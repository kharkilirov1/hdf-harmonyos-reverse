#!/usr/bin/env python3
"""Добавляет BINIT-трейс: кто и с каким code шлёт транзакцию процессу init."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()
if "BINIT from=" in s:
    print("already instrumented")
    raise SystemExit(0)
anchor = "\tt->priority = task_nice(current);\n"
if anchor not in s:
    raise SystemExit("anchor not found")
ins = (
    anchor
    + "\tif (!reply && target_proc->tsk) {\n"
    + "\t\tstatic unsigned long __last_tgt_print;\n"
    + "\t\tconst char *__tc = target_proc->tsk->comm;\n"
    + "\t\tif (__tc[0] == 'i' && __tc[1] == 'n' && __tc[2] == 'i' &&\n"
    + "\t\t    __tc[3] == 't' && __tc[4] == 0) {\n"
    + "\t\t\tif (time_after(jiffies, __last_tgt_print + HZ / 2)) {\n"
    + "\t\t\t\t__last_tgt_print = jiffies;\n"
    + "\t\t\t\tpr_info(\"BINIT from=%d code=%u flags=%x\\n\",\n"
    + "\t\t\t\t\tproc->pid, t->code, t->flags);\n"
    + "\t\t\t}\n"
    + "\t\t}\n"
    + "\t}\n"
)
s = s.replace(anchor, ins, 1)
open(p, "w").write(s)
print("instrumented init-target")
