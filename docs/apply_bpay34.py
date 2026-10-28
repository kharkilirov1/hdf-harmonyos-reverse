#!/usr/bin/env python3
"""BPAY3/4: расширенный дамп payload (128 байт) для транзакций к installs."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()
if "BPAY3" in s:
    print("already instrumented")
    raise SystemExit(0)

old = (
    '\t\t\tpr_info("BPAY2 %08x %08x %08x %08x %08x %08x %08x %08x\\n",\n'
    "\t\t\t\t__d[8], __d[9], __d[10], __d[11],\n"
    "\t\t\t\t__d[12], __d[13], __d[14], __d[15]);"
)
new = (
    old
    + '\n\t\t\tif (__tc[0] == \'i\' && __tc[1] == \'n\') {\n'
    + '\t\t\t\tpr_info("BPAY3 %08x %08x %08x %08x %08x %08x %08x %08x\\n",\n'
    + "\t\t\t\t\t__d[16], __d[17], __d[18], __d[19],\n"
    + "\t\t\t\t\t__d[20], __d[21], __d[22], __d[23]);\n"
    + '\t\t\t\tpr_info("BPAY4 %08x %08x %08x %08x %08x %08x %08x %08x\\n",\n'
    + "\t\t\t\t\t__d[24], __d[25], __d[26], __d[27],\n"
    + "\t\t\t\t\t__d[28], __d[29], __d[30], __d[31]);\n"
    + "\t\t\t}"
)
if old not in s:
    raise SystemExit("anchor not found")
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("BPAY3/4 added for installs")
