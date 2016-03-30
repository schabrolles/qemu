/*
 * ppc CPU core abstraction
 *
 * Copyright (c) 2015 SUSE Linux GmbH
 * Copyright (C) 2015 Bharata B Rao <bharata@linux.vnet.ibm.com>
 */

#include "qemu/osdep.h"
#include "hw/qdev.h"
#include "hw/ppc/cpu-core.h"
#include "hw/boards.h"
#include <sysemu/cpus.h>
#include <sysemu/sysemu.h>
#include "qemu/error-report.h"
#include "qapi/error.h"

static int ppc_cpu_core_realize_child(Object *child, void *opaque)
{
    Error **errp = opaque;

    object_property_set_bool(child, true, "realized", errp);
    if (*errp) {
        return 1;
    }

    return 0;
}

static void ppc_cpu_core_realize(DeviceState *dev, Error **errp)
{
    object_child_foreach(OBJECT(dev), ppc_cpu_core_realize_child, errp);
}

static void ppc_cpu_core_class_init(ObjectClass *oc, void *data)
{
    DeviceClass *dc = DEVICE_CLASS(oc);

    dc->realize = ppc_cpu_core_realize;
}

static void ppc_cpu_core_instance_init(Object *obj)
{
    int i;
    PowerPCCPU *cpu = NULL;
    MachineState *machine = MACHINE(qdev_get_machine());
    int threads_per_core;

    /*
     * Support topologies like -smp 15,cores=4,threads=4 where one core
     * will have less than the specified SMT threads. The last core will
     * always have the deficit even when -device options are used to
     * cold-plug the cores.
     */
    if ((smp_remaining_cpus > 0) && (smp_remaining_cpus < smp_threads)) {
        threads_per_core = smp_remaining_cpus;
    } else {
        threads_per_core = smp_threads;
    }
    smp_remaining_cpus -= threads_per_core;

    for (i = 0; i < threads_per_core; i++) {
        cpu = POWERPC_CPU(cpu_ppc_create(TYPE_POWERPC_CPU, machine->cpu_model));
        if (!cpu) {
            error_report("Unable to find PowerPC CPU definition: %s\n",
                          machine->cpu_model);
            exit(EXIT_FAILURE);
        }
        object_property_add_child(obj, "thread[*]", OBJECT(cpu), &error_abort);
        object_unref(OBJECT(cpu));
    }
}

static const TypeInfo ppc_cpu_core_type_info = {
    .name = TYPE_POWERPC_CPU_CORE,
    .parent = TYPE_DEVICE,
    .class_init = ppc_cpu_core_class_init,
    .instance_init = ppc_cpu_core_instance_init,
    .instance_size = sizeof(PowerPCCPUCore),
};

static void ppc_cpu_core_register_types(void)
{
    type_register_static(&ppc_cpu_core_type_info);
}

type_init(ppc_cpu_core_register_types)
