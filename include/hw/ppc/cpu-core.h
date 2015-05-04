/*
 * PowerPC CPU core abstraction
 *
 * Copyright (c) 2015 SUSE Linux GmbH
 * Copyright (C) 2015 Bharata B Rao <bharata@linux.vnet.ibm.com>
 */
#ifndef HW_PPC_CPU_CORE_H
#define HW_PPC_CPU_CORE_H

#include "hw/qdev.h"
#include "cpu.h"

#ifdef TARGET_PPC64
#define TYPE_POWERPC_CPU_CORE "powerpc64-cpu-core"
#elif defined(TARGET_PPCEMB)
#define TYPE_POWERPC_CPU_CORE "embedded-powerpc-cpu-core"
#else
#define TYPE_POWERPC_CPU_CORE "powerpc-cpu-core"
#endif

#define POWERPC_CPU_CORE(obj) \
    OBJECT_CHECK(PowerPCCPUCore, (obj), TYPE_POWERPC_CPU_CORE)

typedef struct PowerPCCPUCore {
    /*< private >*/
    DeviceState parent_obj;
    /*< public >*/

    PowerPCCPU thread[0];
} PowerPCCPUCore;

#endif
