/*
 * QEMU PowerPC pSeries Logical Partition (aka sPAPR) hardware System Emulator
 *
 * Trivial in-partition RTAS implementation, based on a hypercall
 *
 * Copyright (c) 2010,2011 David Gibson, IBM Corporation.
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

#define KVMPPC_HCALL_BASE       0xf000
#define KVMPPC_H_RTAS           (KVMPPC_HCALL_BASE + 0x0)

.globl	_start
_start:
	mr	4,3
	lis	3,KVMPPC_H_RTAS@h
	ori	3,3,KVMPPC_H_RTAS@l
	sc	1
	blr
   . = 0x200
   /*
    * Trampoline saves r3 in sprg2 and issues private hcall
    * to request qemu to build error log. QEMU builds the
    * error log, copies to rtas-blob and returns the address.
    * The initial 16 bytes in return adress consist of saved
    * srr0 and srr1 which we restore and pass on the actual error
    * log address to OS handled mcachine check notification
    * routine
    *
    * All the below instructions are copied to interrupt vector
    * 0x200 at the time of handling ibm,nmi-register rtas call.
    */
   mtsprg  2,3
   li      3,0
   /*
    * ori r3,r3,KVMPPC_H_REPORT_MC_ERR. The KVMPPC_H_REPORT_MC_ERR
    * value is patched below
    */
1:  ori     3,3,0
   sc      1               /* Issue H_CALL */
   cmpdi   cr0,3,0
   beq     cr0,1b          /* retry KVMPPC_H_REPORT_MC_ERR */
   mtsprg  2,4
   ld      4,0(3)
   mtsrr0  4               /* Restore srr0 */
   ld      4,8(3)
   mtsrr1  4               /* Restore srr1 */
   ld      4,16(3)
   mtcrf   0,4             /* Restore cr */
   addi    3,3,24
   mfsprg  4,2
   /*
    * Branch to address registered by OS. The branch address is
    * patched in the ibm,nmi-register rtas call.
    */
   ba      0x0
   b       .
