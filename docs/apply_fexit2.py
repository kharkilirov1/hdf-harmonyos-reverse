#!/usr/bin/env python3
"""FEXIT2: при выходе foundation/sa_main печатаем user pc/sp и 6 слов стека,
чтобы увидеть, откуда вызван exit()."""
import re

EXIT = "/home/kharki/k414/src/kernel/exit.c"
s = open(EXIT).read()
if "FEXIT2 pc=" in s:
    print("already")
    raise SystemExit(0)

anchor = "\t{\n\t\tconst char *__c = current->comm;\n"
idx = s.find(anchor)
if idx < 0:
    raise SystemExit("FEXIT block not found")
end = s.find("\t}\n", idx) + len("\t}\n")
ins = (
    "\t{\n"
    "\t\tconst char *__c = current->comm;\n"
    "\t\tif (__c[0] == 'f' && __c[1] == 'o' && __c[2] == 'u') {\n"
    "\t\t\tstruct pt_regs *__r = current_pt_regs();\n"
    "\t\t\tu64 __w[6] = {0};\n"
    "\t\t\tif (__r && !user_mode(__r) && __r->sp &&\n"
    "\t\t\t    !copy_from_user(__w, (void __user *)__r->sp, sizeof(__w)))\n"
    "\t\t\t\tpr_info(\"FEXIT2 pc=%llx lr=%llx sp=%llx w=%llx %llx %llx %llx %llx %llx\\n\",\n"
    "\t\t\t\t\t(u64)__r->pc, (u64)__r->regs[30], (u64)__r->sp,\n"
    "\t\t\t\t\t__w[0], __w[1], __w[2], __w[3], __w[4], __w[5]);\n"
    "\t\t}\n"
    "\t}\n"
)
s = s[:end] + ins + s[end:]
open(EXIT, "w").write(s)
print("FEXIT2 added")
