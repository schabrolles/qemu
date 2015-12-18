/*
 * QEMU sPAPR PCI host for VFIO
 *
 * Copyright (c) 2011-2014 Alexey Kardashevskiy, IBM Corporation.
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License,
 *  or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, see <http://www.gnu.org/licenses/>.
 */

#include "hw/ppc/spapr.h"
#include "hw/pci-host/spapr.h"
#include "linux/vfio.h"
#include "hw/misc/vfio.h"

static Property spapr_phb_vfio_properties[] = {
    DEFINE_PROP_INT32("iommu", sPAPRPHBVFIOState, iommugroupid, -1),
    DEFINE_PROP_END_OF_LIST(),
};

static void spapr_phb_vfio_finish_realize(sPAPRPHBState *sphb, Error **errp)
{
    sPAPRPHBVFIOState *svphb = SPAPR_PCI_VFIO_HOST_BRIDGE(sphb);
    struct vfio_iommu_spapr_tce_info info = { .argsz = sizeof(info) };
    int ret;
    sPAPRTCETable *tcet;
    uint32_t liobn = svphb->phb.dma_liobn;

    if (svphb->iommugroupid == -1) {
        error_setg(errp, "Wrong IOMMU group ID %d", svphb->iommugroupid);
        return;
    }

    ret = vfio_container_ioctl(&svphb->phb.iommu_as, svphb->iommugroupid,
                               VFIO_IOMMU_SPAPR_TCE_GET_INFO, &info);
    if (ret) {
        error_setg_errno(errp, -ret,
                         "spapr-vfio: get info from container failed");
        return;
    }

    tcet = spapr_tce_new_table(DEVICE(sphb), liobn, info.dma32_window_start,
                               SPAPR_TCE_PAGE_SHIFT,
                               info.dma32_window_size >> SPAPR_TCE_PAGE_SHIFT,
                               true);
    if (!tcet) {
        error_setg(errp, "spapr-vfio: failed to create VFIO TCE table");
        return;
    }

    /* Register default 32bit DMA window */
    memory_region_add_subregion(&sphb->iommu_root, tcet->bus_offset,
                                spapr_tce_get_iommu(tcet));

    object_unref(OBJECT(tcet));

    if (sphb->ddw_enabled) {
        sphb->ddw_enabled = !!(info.flags & VFIO_IOMMU_SPAPR_INFO_DDW);
    }
}

static int spapr_phb_vfio_eeh_handler(sPAPRPHBState *sphb, int req, int opt)
{
    sPAPRPHBVFIOState *svphb = SPAPR_PCI_VFIO_HOST_BRIDGE(sphb);
    struct vfio_eeh_pe_op op = { .argsz = sizeof(op) };
    int cmd;

    switch (req) {
    case RTAS_EEH_REQ_SET_OPTION:
        switch (opt) {
        case RTAS_EEH_DISABLE:
            cmd = VFIO_EEH_PE_DISABLE;
            break;
        case RTAS_EEH_ENABLE:
            cmd = VFIO_EEH_PE_ENABLE;
            break;
        case RTAS_EEH_THAW_IO:
            cmd = VFIO_EEH_PE_UNFREEZE_IO;
            break;
        case RTAS_EEH_THAW_DMA:
            cmd = VFIO_EEH_PE_UNFREEZE_DMA;
            break;
        default:
            return -EINVAL;
        }
        break;
    case RTAS_EEH_REQ_GET_STATE:
        cmd = VFIO_EEH_PE_GET_STATE;
        break;
    case RTAS_EEH_REQ_RESET:
        switch (opt) {
        case RTAS_SLOT_RESET_DEACTIVATE:
            cmd = VFIO_EEH_PE_RESET_DEACTIVATE;
            break;
        case RTAS_SLOT_RESET_HOT:
            cmd = VFIO_EEH_PE_RESET_HOT;
            break;
        case RTAS_SLOT_RESET_FUNDAMENTAL:
            cmd = VFIO_EEH_PE_RESET_FUNDAMENTAL;
            break;
        default:
            return -EINVAL;
        }
        break;
    case RTAS_EEH_REQ_CONFIGURE:
        cmd = VFIO_EEH_PE_CONFIGURE;
        break;
    default:
         return -EINVAL;
    }

    op.op = cmd;
    return vfio_container_ioctl(&svphb->phb.iommu_as, svphb->iommugroupid,
                                VFIO_EEH_PE_OP, &op);
}

static int spapr_pci_vfio_ddw_query(sPAPRPHBState *sphb,
                                    uint32_t *windows_supported,
                                    uint32_t *page_size_mask)
{
    sPAPRPHBVFIOState *svphb = SPAPR_PCI_VFIO_HOST_BRIDGE(sphb);
    struct vfio_iommu_spapr_tce_info info = { .argsz = sizeof(info) };
    int ret;

    ret = vfio_container_ioctl(&svphb->phb.iommu_as, svphb->iommugroupid,
                               VFIO_IOMMU_SPAPR_TCE_GET_INFO, &info);
    if (ret) {
        return ret;
    }

    *windows_supported = info.ddw.max_dynamic_windows_supported;
    *page_size_mask = info.ddw.pgsizes;

    return ret;
}

static int spapr_pci_vfio_ddw_create(sPAPRPHBState *sphb, uint32_t page_shift,
                                     uint32_t window_shift, uint32_t liobn,
                                     sPAPRTCETable **ptcet)
{
    sPAPRPHBVFIOState *svphb = SPAPR_PCI_VFIO_HOST_BRIDGE(sphb);
    struct vfio_iommu_spapr_tce_create create = {
        .argsz = sizeof(create),
        .page_shift = page_shift,
        .window_size = 1ULL << window_shift,
        .levels = 1,
        .start_addr = 0
    };
    int ret;

    ret = vfio_container_ioctl(&sphb->iommu_as, svphb->iommugroupid,
                               VFIO_IOMMU_SPAPR_TCE_CREATE, &create);
    if (ret) {
        return ret;
    }

    *ptcet = spapr_tce_new_table(DEVICE(sphb), liobn,
                                 create.start_addr, page_shift,
                                 1ULL << (window_shift - page_shift),
                                 true);
    memory_region_add_subregion(&sphb->iommu_root, (*ptcet)->bus_offset,
                                spapr_tce_get_iommu(*ptcet));

    return ret;
}

static int spapr_pci_vfio_ddw_remove(sPAPRPHBState *sphb, sPAPRTCETable *tcet)
{
    sPAPRPHBVFIOState *svphb = SPAPR_PCI_VFIO_HOST_BRIDGE(sphb);
    struct vfio_iommu_spapr_tce_remove remove = {
        .argsz = sizeof(remove),
        .start_addr = tcet->bus_offset
    };
    int ret;

    spapr_pci_ddw_remove(sphb, tcet);
    ret = vfio_container_ioctl(&sphb->iommu_as, svphb->iommugroupid,
                               VFIO_IOMMU_SPAPR_TCE_REMOVE, &remove);

    return ret;
}

static void spapr_phb_vfio_class_init(ObjectClass *klass, void *data)
{
    DeviceClass *dc = DEVICE_CLASS(klass);
    sPAPRPHBClass *spc = SPAPR_PCI_HOST_BRIDGE_CLASS(klass);

    dc->props = spapr_phb_vfio_properties;
    spc->finish_realize = spapr_phb_vfio_finish_realize;
    spc->eeh_handler = spapr_phb_vfio_eeh_handler;
    spc->ddw_query = spapr_pci_vfio_ddw_query;
    spc->ddw_create = spapr_pci_vfio_ddw_create;
    spc->ddw_remove = spapr_pci_vfio_ddw_remove;
}

static const TypeInfo spapr_phb_vfio_info = {
    .name          = TYPE_SPAPR_PCI_VFIO_HOST_BRIDGE,
    .parent        = TYPE_SPAPR_PCI_HOST_BRIDGE,
    .instance_size = sizeof(sPAPRPHBVFIOState),
    .class_init    = spapr_phb_vfio_class_init,
    .class_size    = sizeof(sPAPRPHBClass),
};

static void spapr_pci_vfio_register_types(void)
{
    type_register_static(&spapr_phb_vfio_info);
}

type_init(spapr_pci_vfio_register_types)
