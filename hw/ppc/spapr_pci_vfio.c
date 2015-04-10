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
#include "hw/vfio/vfio.h"

static Property spapr_phb_vfio_properties[] = {
    DEFINE_PROP_INT32("iommu", sPAPRPHBState, iommugroupid, -1),
    DEFINE_PROP_END_OF_LIST(),
};

int spapr_phb_vfio_dma_capabilities_update(sPAPRPHBState *sphb)
{
    struct vfio_iommu_spapr_tce_info info = { .argsz = sizeof(info) };
    int ret;

    ret = vfio_container_ioctl(&sphb->iommu_as,
                               VFIO_IOMMU_SPAPR_TCE_GET_INFO, &info);
    if (ret) {
        return ret;
    }

    sphb->dma32_window_start = info.dma32_window_start;
    sphb->dma32_window_size = info.dma32_window_size;

    return ret;
}

int spapr_phb_vfio_eeh_set_option(sPAPRPHBState *sphb,
                                         unsigned int addr, int option)
{
    struct vfio_eeh_pe_op op = { .argsz = sizeof(op) };
    int ret;

    switch (option) {
    case RTAS_EEH_DISABLE:
        op.op = VFIO_EEH_PE_DISABLE;
        break;
    case RTAS_EEH_ENABLE: {
        PCIHostState *phb;
        PCIDevice *pdev;

        /*
         * The EEH functionality is enabled on basis of PCI device,
         * instead of PE. We need check the validity of the PCI
         * device address.
         */
        phb = PCI_HOST_BRIDGE(sphb);
        pdev = pci_find_device(phb->bus,
                               (addr >> 16) & 0xFF, (addr >> 8) & 0xFF);
        if (!pdev) {
            return RTAS_OUT_PARAM_ERROR;
        }

        op.op = VFIO_EEH_PE_ENABLE;
        break;
    }
    case RTAS_EEH_THAW_IO:
        op.op = VFIO_EEH_PE_UNFREEZE_IO;
        break;
    case RTAS_EEH_THAW_DMA:
        op.op = VFIO_EEH_PE_UNFREEZE_DMA;
        break;
    default:
        return RTAS_OUT_PARAM_ERROR;
    }

    ret = vfio_container_ioctl(&sphb->iommu_as,
                               VFIO_EEH_PE_OP, &op);
    if (ret < 0) {
        return RTAS_OUT_HW_ERROR;
    }

    return RTAS_OUT_SUCCESS;
}

int spapr_phb_vfio_eeh_get_state(sPAPRPHBState *sphb, int *state)
{
    struct vfio_eeh_pe_op op = { .argsz = sizeof(op) };
    int ret;

    op.op = VFIO_EEH_PE_GET_STATE;
    ret = vfio_container_ioctl(&sphb->iommu_as,
                               VFIO_EEH_PE_OP, &op);
    if (ret < 0) {
        return RTAS_OUT_PARAM_ERROR;
    }

    *state = ret;
    return RTAS_OUT_SUCCESS;
}

int spapr_phb_vfio_eeh_reset(sPAPRPHBState *sphb, int option)
{
    struct vfio_eeh_pe_op op = { .argsz = sizeof(op) };
    int ret;

    switch (option) {
    case RTAS_SLOT_RESET_DEACTIVATE:
        op.op = VFIO_EEH_PE_RESET_DEACTIVATE;
        break;
    case RTAS_SLOT_RESET_HOT:
        op.op = VFIO_EEH_PE_RESET_HOT;
        break;
    case RTAS_SLOT_RESET_FUNDAMENTAL:
        op.op = VFIO_EEH_PE_RESET_FUNDAMENTAL;
        break;
    default:
        return RTAS_OUT_PARAM_ERROR;
    }

    ret = vfio_container_ioctl(&sphb->iommu_as,
                               VFIO_EEH_PE_OP, &op);
    if (ret < 0) {
        return RTAS_OUT_HW_ERROR;
    }

    return RTAS_OUT_SUCCESS;
}

int spapr_phb_vfio_eeh_configure(sPAPRPHBState *sphb)
{
    struct vfio_eeh_pe_op op = { .argsz = sizeof(op) };
    int ret;

    op.op = VFIO_EEH_PE_CONFIGURE;
    ret = vfio_container_ioctl(&sphb->iommu_as,
                               VFIO_EEH_PE_OP, &op);
    if (ret < 0) {
        return RTAS_OUT_PARAM_ERROR;
    }

    return RTAS_OUT_SUCCESS;
}

static void spapr_phb_vfio_class_init(ObjectClass *klass, void *data)
{
    DeviceClass *dc = DEVICE_CLASS(klass);

    dc->props = spapr_phb_vfio_properties;
}

static const TypeInfo spapr_phb_vfio_info = {
    .name          = TYPE_SPAPR_PCI_VFIO_HOST_BRIDGE,
    .parent        = TYPE_SPAPR_PCI_HOST_BRIDGE,
    .instance_size = sizeof(sPAPRPHBState),
    .class_init    = spapr_phb_vfio_class_init,
    .class_size    = sizeof(sPAPRPHBClass),
};

static void spapr_pci_vfio_register_types(void)
{
    type_register_static(&spapr_phb_vfio_info);
}

type_init(spapr_pci_vfio_register_types)
