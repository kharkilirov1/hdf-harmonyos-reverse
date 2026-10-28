#!/usr/bin/env python3
"""BPAYR2: расширенный дамп ответов installd (32 слова) для поиска кодов 0x82xxxx."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()
if "BPAYR2" in s:
    print("already instrumented")
    raise SystemExit(0)

old = (
    '\t\t\tpr_info("BPAYR req=%d to=%s from=%d code=%u sz=%zu d=%08x %08x %08x %08x %08x %08x\\n",\n'
    "\t\t\t\t(thread->transaction_stack ? thread->transaction_stack->debug_id : 0),\n"
    "\t\t\t\t__tc, proc->pid, t->code, (size_t)tr->data_size,\n"
    "\t\t\t\t__d[0], __d[1], __d[2], __d[3], __d[4], __d[5]);"
)
new = (
    old
    + '\n\t\t\tif (proc->tsk && proc->tsk->comm[0] == \'i\' &&\n'
    + '\t\t\t    proc->tsk->comm[1] == \'n\') {\n'
    + '\t\t\t\tpr_info("BPAYR2 %08x %08x %08x %08x %08x %08x %08x %08x\\n",\n'
    + "\t\t\t\t\t__d[6], __d[7], __d[8], __d[9],\n"
    + "\t\t\t\t\t__d[10], __d[11], __d[12], __d[13]);\n"
    + '\t\t\t\tpr_info("BPAYR3 %08x %08x %08x %08x %08x %08x %08x %08x\\n",\n'
    + "\t\t\t\t\t__d[14], __d[15], __d[16], __d[17],\n"
    + "\t\t\t\t\t__d[18], __d[19], __d[20], __d[21]);\n"
    + "\t\t\t}"
)
if old not in s:
    raise SystemExit("anchor not found")
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("BPAYR2/3 instrumented")
