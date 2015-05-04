#include "qom/object.h"
#include "qapi/qmp/qerror.h"
#include "qemu/typedefs.h"
#include "qmp-commands.h"

sPAPRCPUSocketList *qmp_query_spapr_cpu_sockets(Error **errp)
{
    error_set(errp, QERR_UNSUPPORTED);
    return 0;
}
