#!/usr/bin/env python3
"""FEXIT: printk при завершении foundation/sa_main и при SIGKILL им.

1) kernel/exit.c do_exit(): если comm начинается на 'foundation' или 'sa_main' —
   печатаем pid/tgid/exit_code/comm.
2) kernel/signal.c: при отправке SIGKILL цели с comm foundation/sa_main —
   печатаем, кто послал (pid/comm отправителя).
"""
import re

EXIT = "/home/kharki/k414/src/kernel/exit.c"
SIG = "/home/kharki/k414/src/kernel/signal.c"

s = open(EXIT).read()
if "FEXIT pid=" not in s:
    anchor = "void __noreturn do_exit(long code)\n{\n"
    if anchor not in s:
        raise SystemExit("do_exit anchor not found")
    ins = anchor + (
        "\t{\n"
        "\t\tconst char *__c = current->comm;\n"
        "\t\tif ((__c[0] == 'f' && __c[1] == 'o' && __c[2] == 'u') ||\n"
        "\t\t    (__c[0] == 's' && __c[1] == 'a' && __c[2] == '_'))\n"
        "\t\t\tpr_info(\"FEXIT pid=%d tgid=%d code=%ld(%s)\\n\",\n"
        "\t\t\t\tcurrent->pid, current->tgid, code, __c);\n"
        "\t}\n"
    )
    s = s.replace(anchor, ins, 1)
    open(EXIT, "w").write(s)
    print("exit.c instrumented")
else:
    print("exit.c already")

s2 = open(SIG).read()
if "FSIGK pid=" not in s2:
    anchor2 = "static void complete_signal(int sig, struct task_struct *p, enum pid_type type)\n{\n"
    if anchor2 not in s2:
        raise SystemExit("complete_signal anchor not found")
    ins2 = anchor2 + (
        "\tif (sig == SIGKILL) {\n"
        "\t\tconst char *__tc = p->comm;\n"
        "\t\tif (((__tc[0] == 'f' && __tc[1] == 'o' && __tc[2] == 'u') ||\n"
        "\t\t     (__tc[0] == 's' && __tc[1] == 'a' && __tc[2] == '_')) &&\n"
        "\t\t    p->pid != current->pid)\n"
        "\t\t\tpr_info(\"FSIGK target=%d(%s) sender=%d(%s)\\n\",\n"
        "\t\t\t\tp->pid, __tc, current->pid, current->comm);\n"
        "\t}\n"
    )
    s2 = s2.replace(anchor2, ins2, 1)
    open(SIG, "w").write(s2)
    print("signal.c instrumented")
else:
    print("signal.c already")
