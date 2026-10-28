#!/usr/bin/env python3
"""FNAME2/FPIPE: трассировка PR_SET_NAME (bms_event) и pipe_write от foundation."""
import re

SYSC = "/home/kharki/k414/src/kernel/sys.c"
s = open(SYSC).read()
if "FNAME2 set" not in s:
    m = re.search(r"\tcase PR_SET_NAME:\n(?:.*\n){0,8}?\t\tset_task_comm\(me, comm\);\n", s)
    if not m:
        raise SystemExit("PR_SET_NAME block not found")
    block = m.group(0)
    ins = block + (
        "\t\t{\n"
        "\t\t\tchar __nb[16] = {0};\n"
        "\t\t\tif (!copy_from_user(__nb, arg2, sizeof(__nb) - 1) &&\n"
        "\t\t\t    __nb[0] == 'b' && __nb[1] == 'm' && __nb[2] == 's')\n"
        "\t\t\t\tpr_info(\"FNAME2 set pid=%d(%s) new=%s ppid=%d\\n\",\n"
        "\t\t\t\t\tcurrent->pid, current->comm, __nb,\n"
        "\t\t\t\t\tcurrent->real_parent ? current->real_parent->pid : -1);\n"
        "\t\t}\n"
    )
    s = s.replace(block, ins, 1)
    open(SYSC, "w").write(s)
    print("FNAME2 added")
else:
    print("FNAME2 already")

PIPE = "/home/kharki/k414/src/fs/pipe.c"
s2 = open(PIPE).read()
if "FPIPE" not in s2:
    m2 = re.search(r"pipe_write\(struct kiocb \*iocb, struct iov_iter \*from\)\n\{\n", s2)
    if not m2:
        raise SystemExit("pipe_write not found")
    ins2 = m2.group(0) + (
        "\tif (current->comm[0] == 'f' && current->comm[1] == 'o' &&\n"
        "\t    current->comm[2] == 'u' && current->comm[3] == 'n') {\n"
        "\t\tpr_info(\"FPIPE pid=%d(%s) count=%zu\\n\", current->pid,\n"
        "\t\t\tcurrent->comm, iov_iter_count(from));\n"
        "\t}\n"
    )
    s2 = s2.replace(m2.group(0), ins2, 1)
    open(PIPE, "w").write(s2)
    print("FPIPE added")
else:
    print("FPIPE already")
