/*
 * PowerPC CPU socket abstraction
 *
 * Copyright (c) 2015 SUSE Linux GmbH
 * Copyright (C) 2015 Bharata B Rao <bharata@linux.vnet.ibm.com>
 */
#ifndef HW_PPC_CPU_SOCKET_H
#define HW_PPC_CPU_SOCKET_H

#include "hw/cpu/socket.h"
#include "cpu-core.h"

#ifdef TARGET_PPC64
#define TYPE_POWERPC_CPU_SOCKET "powerpc64-cpu-socket"
#elif defined(TARGET_PPCEMB)
#define TYPE_POWERPC_CPU_SOCKET "embedded-powerpc-cpu-socket"
#else
#define TYPE_POWERPC_CPU_SOCKET "powerpc-cpu-socket"
#endif

#define POWERPC_CPU_SOCKET(obj) \
    OBJECT_CHECK(PowerPCCPUSocket, (obj), TYPE_POWERPC_CPU_SOCKET)

typedef struct PowerPCCPUSocket {
    /*< private >*/
    DeviceState parent_obj;
    /*< public >*/

    PowerPCCPUCore core[0];
} PowerPCCPUSocket;

#endif
