/*
 * QEMU PowerPC pSeries Logical Partition (aka sPAPR) hardware System Emulator
 *
 * RTAS Real Time Clock
 *
 * Copyright (c) 2010-2011 David Gibson, IBM Corporation.
 * Copyright 2014 David Gibson, Red Hat.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 */
#include "cpu.h"
#include "sysemu/sysemu.h"
#include "hw/ppc/spapr.h"
#include "sysemu/sysemu.h"

#define NSEC_PER_SEC    1000000000LL

void spapr_rtc_read(sPAPREnvironment *spapr, struct tm *tm, uint32_t *ns)
{
    int64_t host_ns = qemu_clock_get_ns(rtc_clock);
    time_t guest_s;

    guest_s = host_ns / NSEC_PER_SEC + spapr->rtc_offset;

    if (tm) {
        gmtime_r(&guest_s, tm);
    }
    if (ns) {
        *ns = host_ns % NSEC_PER_SEC;
    }
}

static void rtas_get_time_of_day(PowerPCCPU *cpu, sPAPREnvironment *spapr,
                                 uint32_t token, uint32_t nargs,
                                 target_ulong args,
                                 uint32_t nret, target_ulong rets)
{
    struct tm tm;
    uint32_t ns;

    if ((nargs != 0) || (nret != 8)) {
        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);
        return;
    }

    spapr_rtc_read(spapr, &tm, &ns);

    rtas_st(rets, 0, RTAS_OUT_SUCCESS);
    rtas_st(rets, 1, tm.tm_year + 1900);
    rtas_st(rets, 2, tm.tm_mon + 1);
    rtas_st(rets, 3, tm.tm_mday);
    rtas_st(rets, 4, tm.tm_hour);
    rtas_st(rets, 5, tm.tm_min);
    rtas_st(rets, 6, tm.tm_sec);
    rtas_st(rets, 7, ns);
}

static void rtas_set_time_of_day(PowerPCCPU *cpu, sPAPREnvironment *spapr,
                                 uint32_t token, uint32_t nargs,
                                 target_ulong args,
                                 uint32_t nret, target_ulong rets)
{
    struct tm tm;
    time_t new_s;
    int64_t host_ns;

    if ((nargs != 7) || (nret != 1)) {
        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);
        return;
    }

    tm.tm_year = rtas_ld(args, 0) - 1900;
    tm.tm_mon = rtas_ld(args, 1) - 1;
    tm.tm_mday = rtas_ld(args, 2);
    tm.tm_hour = rtas_ld(args, 3);
    tm.tm_min = rtas_ld(args, 4);
    tm.tm_sec = rtas_ld(args, 5);

    new_s = mktimegm(&tm);
    if (new_s == -1) {
        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);
        return;
    }

    /* Generate a monitor event for the change */
    rtc_change_mon_event(&tm);

    host_ns = qemu_clock_get_ns(rtc_clock);

    spapr->rtc_offset = new_s - host_ns / NSEC_PER_SEC;

    rtas_st(rets, 0, RTAS_OUT_SUCCESS);
}

void spapr_rtc_init(void)
{
    struct tm tm;
    time_t host_s;
    int64_t rtc_ns;

    /* Initialize the RTAS RTC from host time */

    qemu_get_timedate(&tm, 0);
    host_s = mktimegm(&tm);
    rtc_ns = qemu_clock_get_ns(rtc_clock);
    spapr->rtc_offset = host_s - rtc_ns / NSEC_PER_SEC;

    spapr_rtas_register(RTAS_GET_TIME_OF_DAY, "get-time-of-day",
                        rtas_get_time_of_day);
    spapr_rtas_register(RTAS_SET_TIME_OF_DAY, "set-time-of-day",
                        rtas_set_time_of_day);
}
