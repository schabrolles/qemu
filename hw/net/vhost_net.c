/*
 * vhost-net support
 *
 * Copyright Red Hat, Inc. 2010
 *
 * Authors:
 *  Michael S. Tsirkin <mst@redhat.com>
 *
 * This work is licensed under the terms of the GNU GPL, version 2.  See
 * the COPYING file in the top-level directory.
 *
 * Contributions after 2012-01-13 are licensed under the terms of the
 * GNU GPL, version 2 or (at your option) any later version.
 */

#include "net/net.h"
#include "net/tap.h"

#include "hw/virtio/virtio-net.h"
#include "net/vhost_net.h"
#include "qemu/error-report.h"

#include "config.h"

#ifdef CONFIG_VHOST_NET
#include <linux/vhost.h>
#include <sys/socket.h>
#include <linux/kvm.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/virtio_ring.h>
#include <netpacket/packet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <netinet/in.h>

#include <stdio.h>

#include "hw/virtio/virtio_ring.h"
#include "hw/virtio/vhost.h"
#include "hw/virtio/virtio-bus.h"
#include "hw/virtio/virtio-access.h"

struct vhost_net {
    struct vhost_dev dev;
    struct vhost_virtqueue vqs[2];
    int backend;
    NetClientState *nc;
};

unsigned vhost_net_get_features(struct vhost_net *net, unsigned features)
{
    /* Clear features not supported by host kernel. */
    if (!(net->dev.features & (1 << VIRTIO_F_NOTIFY_ON_EMPTY))) {
        features &= ~(1 << VIRTIO_F_NOTIFY_ON_EMPTY);
    }
    if (!(net->dev.features & (1 << VIRTIO_RING_F_INDIRECT_DESC))) {
        features &= ~(1 << VIRTIO_RING_F_INDIRECT_DESC);
    }
    if (!(net->dev.features & (1 << VIRTIO_RING_F_EVENT_IDX))) {
        features &= ~(1 << VIRTIO_RING_F_EVENT_IDX);
    }
    if (!(net->dev.features & (1 << VIRTIO_NET_F_MRG_RXBUF))) {
        features &= ~(1 << VIRTIO_NET_F_MRG_RXBUF);
    }
    return features;
}

void vhost_net_ack_features(struct vhost_net *net, unsigned features)
{
    net->dev.acked_features = net->dev.backend_features;
    if (features & (1 << VIRTIO_F_NOTIFY_ON_EMPTY)) {
        net->dev.acked_features |= (1 << VIRTIO_F_NOTIFY_ON_EMPTY);
    }
    if (features & (1 << VIRTIO_RING_F_INDIRECT_DESC)) {
        net->dev.acked_features |= (1 << VIRTIO_RING_F_INDIRECT_DESC);
    }
    if (features & (1 << VIRTIO_RING_F_EVENT_IDX)) {
        net->dev.acked_features |= (1 << VIRTIO_RING_F_EVENT_IDX);
    }
    if (features & (1 << VIRTIO_NET_F_MRG_RXBUF)) {
        net->dev.acked_features |= (1 << VIRTIO_NET_F_MRG_RXBUF);
    }
}

static int vhost_net_get_fd(NetClientState *backend)
{
    switch (backend->info->type) {
    case NET_CLIENT_OPTIONS_KIND_TAP:
        return tap_get_fd(backend);
    default:
        fprintf(stderr, "vhost-net requires tap backend\n");
        return -EBADFD;
    }
}

struct vhost_net *vhost_net_init(NetClientState *backend, int devfd,
                                 bool force)
{
    int r;
    struct vhost_net *net = g_malloc(sizeof *net);
    if (!backend) {
        fprintf(stderr, "vhost-net requires backend to be setup\n");
        goto fail;
    }
    r = vhost_net_get_fd(backend);
    if (r < 0) {
        goto fail;
    }
    net->nc = backend;
    net->dev.backend_features = qemu_has_vnet_hdr(backend) ? 0 :
        (1 << VHOST_NET_F_VIRTIO_NET_HDR);
    net->backend = r;

    net->dev.nvqs = 2;
    net->dev.vqs = net->vqs;

    r = vhost_dev_init(&net->dev, devfd, "/dev/vhost-net", force);
    if (r < 0) {
        goto fail;
    }
    if (!qemu_has_vnet_hdr_len(backend,
                               sizeof(struct virtio_net_hdr_mrg_rxbuf))) {
        net->dev.features &= ~(1 << VIRTIO_NET_F_MRG_RXBUF);
    }
    if (~net->dev.features & net->dev.backend_features) {
        fprintf(stderr, "vhost lacks feature mask %" PRIu64 " for backend\n",
                (uint64_t)(~net->dev.features & net->dev.backend_features));
        vhost_dev_cleanup(&net->dev);
        goto fail;
    }

    /* Set sane init value. Override when guest acks. */
    vhost_net_ack_features(net, 0);
    return net;
fail:
    g_free(net);
    return NULL;
}

bool vhost_net_query(VHostNetState *net, VirtIODevice *dev)
{
    return vhost_dev_query(&net->dev, dev);
}

static void vhost_net_set_vq_index(struct vhost_net *net, int vq_index)
{
    net->dev.vq_index = vq_index;
}

static int vhost_net_set_vnet_endian(VirtIODevice *dev, NetClientState *peer,
                                     bool set)
{
    int r = 0;

    if (virtio_legacy_is_cross_endian(dev) && !virtio_is_big_endian(dev)) {
        r = qemu_set_vnet_le(peer, set);
        if (r) {
            error_report("backend does not support LE vnet headers");
        }
    } else if (virtio_legacy_is_cross_endian(dev)) {
        r = qemu_set_vnet_be(peer, set);
        if (r) {
            error_report("backend does not support BE vnet headers");
        }
    }

    return r;
}

static int vhost_net_start_one(struct vhost_net *net,
                               VirtIODevice *dev)
{
    struct vhost_vring_file file = { };
    int r;

    if (net->dev.started) {
        return 0;
    }

    net->dev.nvqs = 2;
    net->dev.vqs = net->vqs;

    r = vhost_dev_enable_notifiers(&net->dev, dev);
    if (r < 0) {
        goto fail_notifiers;
    }

    r = vhost_dev_start(&net->dev, dev);
    if (r < 0) {
        goto fail_start;
    }

    net->nc->info->poll(net->nc, false);
    qemu_set_fd_handler(net->backend, NULL, NULL, NULL);
    file.fd = net->backend;
    for (file.index = 0; file.index < net->dev.nvqs; ++file.index) {
        r = ioctl(net->dev.control, VHOST_NET_SET_BACKEND, &file);
        if (r < 0) {
            r = -errno;
            goto fail;
        }
    }
    return 0;
fail:
    file.fd = -1;
    while (file.index-- > 0) {
        int r = ioctl(net->dev.control, VHOST_NET_SET_BACKEND, &file);
        assert(r >= 0);
    }
    net->nc->info->poll(net->nc, true);
    vhost_dev_stop(&net->dev, dev);
fail_start:
    vhost_dev_disable_notifiers(&net->dev, dev);
fail_notifiers:
    return r;
}

static void vhost_net_stop_one(struct vhost_net *net,
                               VirtIODevice *dev)
{
    struct vhost_vring_file file = { .fd = -1 };

    if (!net->dev.started) {
        return;
    }

    for (file.index = 0; file.index < net->dev.nvqs; ++file.index) {
        int r = ioctl(net->dev.control, VHOST_NET_SET_BACKEND, &file);
        assert(r >= 0);
    }
    net->nc->info->poll(net->nc, true);
    vhost_dev_stop(&net->dev, dev);
    vhost_dev_disable_notifiers(&net->dev, dev);
}

int vhost_net_start(VirtIODevice *dev, NetClientState *ncs,
                    int total_queues)
{
    BusState *qbus = BUS(qdev_get_parent_bus(DEVICE(dev)));
    VirtioBusState *vbus = VIRTIO_BUS(qbus);
    VirtioBusClass *k = VIRTIO_BUS_GET_CLASS(vbus);
    int r, e, i, j;

    if (!k->set_guest_notifiers) {
        error_report("binding does not support guest notifiers");
        return -ENOSYS;
    }

    for (j = 0; j < total_queues; j++) {
        r = vhost_net_set_vnet_endian(dev, ncs[j].peer, true);
        if (r < 0) {
            goto err_endian;
        }
        vhost_net_set_vq_index(get_vhost_net(ncs[j].peer), j * 2);
    }

    r = k->set_guest_notifiers(qbus->parent, total_queues * 2, true);
    if (r < 0) {
        error_report("Error binding guest notifier: %d", -r);
        goto err_endian;
    }

    for (i = 0; i < total_queues; i++) {
        r = vhost_net_start_one(get_vhost_net(ncs[i].peer), dev);

        if (r < 0) {
            goto err_start;
        }
    }

    return 0;

err_start:
    while (--i >= 0) {
        vhost_net_stop_one(get_vhost_net(ncs[i].peer), dev);
    }
    e = k->set_guest_notifiers(qbus->parent, total_queues * 2, false);
    if (e < 0) {
        fprintf(stderr, "vhost guest notifier cleanup failed: %d\n", e);
        fflush(stderr);
    }
err_endian:
    while (--j >= 0) {
        vhost_net_set_vnet_endian(dev, ncs[j].peer, false);
    }
    return r;
}

void vhost_net_stop(VirtIODevice *dev, NetClientState *ncs,
                    int total_queues)
{
    BusState *qbus = BUS(qdev_get_parent_bus(DEVICE(dev)));
    VirtioBusState *vbus = VIRTIO_BUS(qbus);
    VirtioBusClass *k = VIRTIO_BUS_GET_CLASS(vbus);
    int i, r;

    for (i = 0; i < total_queues; i++) {
        vhost_net_stop_one(get_vhost_net(ncs[i].peer), dev);
    }

    r = k->set_guest_notifiers(qbus->parent, total_queues * 2, false);
    if (r < 0) {
        fprintf(stderr, "vhost guest notifier cleanup failed: %d\n", r);
        fflush(stderr);
    }
    assert(r >= 0);

    assert(vhost_net_set_vnet_endian(dev, ncs[0].peer, false) >= 0);
}

void vhost_net_cleanup(struct vhost_net *net)
{
    vhost_dev_cleanup(&net->dev);
    g_free(net);
}

bool vhost_net_virtqueue_pending(VHostNetState *net, int idx)
{
    return vhost_virtqueue_pending(&net->dev, idx);
}

void vhost_net_virtqueue_mask(VHostNetState *net, VirtIODevice *dev,
                              int idx, bool mask)
{
    vhost_virtqueue_mask(&net->dev, dev, idx, mask);
}

VHostNetState *get_vhost_net(NetClientState *nc)
{
    VHostNetState *vhost_net = 0;

    if (!nc) {
        return 0;
    }

    switch (nc->info->type) {
    case NET_CLIENT_OPTIONS_KIND_TAP:
        vhost_net = tap_get_vhost_net(nc);
        break;
    default:
        break;
    }

    return vhost_net;
}
#else
struct vhost_net *vhost_net_init(NetClientState *backend, int devfd,
                                 bool force)
{
    error_report("vhost-net support is not compiled in");
    return NULL;
}

bool vhost_net_query(VHostNetState *net, VirtIODevice *dev)
{
    return false;
}

int vhost_net_start(VirtIODevice *dev,
                    NetClientState *ncs,
                    int total_queues)
{
    return -ENOSYS;
}
void vhost_net_stop(VirtIODevice *dev,
                    NetClientState *ncs,
                    int total_queues)
{
}

void vhost_net_cleanup(struct vhost_net *net)
{
}

unsigned vhost_net_get_features(struct vhost_net *net, unsigned features)
{
    return features;
}
void vhost_net_ack_features(struct vhost_net *net, unsigned features)
{
}

bool vhost_net_virtqueue_pending(VHostNetState *net, int idx)
{
    return false;
}

void vhost_net_virtqueue_mask(VHostNetState *net, VirtIODevice *dev,
                              int idx, bool mask)
{
}

VHostNetState *get_vhost_net(NetClientState *nc)
{
    return 0;
}
#endif
