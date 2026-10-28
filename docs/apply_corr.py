#!/usr/bin/env python3
"""CORR: добавляет debug_id запроса в BPAY и req=debug_id в BPAYR — точная
корреляция запрос->ответ."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()

old_req = 'pr_info("BPAY to=%s code=%u flags=%x sz=%zu d=%08x %08x %08x %08x %08x %08x %08x %08x\\n",'
new_req = 'pr_info("BPAY id=%d to=%s code=%u flags=%x sz=%zu d=%08x %08x %08x %08x %08x %08x %08x %08x\\n",\n\t\t\t\tt->debug_id,'
assert old_req in s, "BPAY anchor missing"
s = s.replace(old_req, new_req, 1)

old_rep = 'pr_info("BPAYR to=%s from=%d code=%u sz=%zu d=%08x %08x %08x %08x %08x %08x\\n",\n\t\t\t\t__tc, proc->pid, t->code, (size_t)tr->data_size,'
new_rep = 'pr_info("BPAYR req=%d to=%s from=%d code=%u sz=%zu d=%08x %08x %08x %08x %08x %08x\\n",\n\t\t\t\t(thread->transaction_stack ? thread->transaction_stack->debug_id : 0),\n\t\t\t\t__tc, proc->pid, t->code, (size_t)tr->data_size,'
assert old_rep in s, "BPAYR anchor missing"
s = s.replace(old_rep, new_rep, 1)
open(p, "w").write(s)
print("CORR instrumented")
