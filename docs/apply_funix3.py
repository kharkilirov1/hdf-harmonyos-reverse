#!/usr/bin/env python3
"""FUNIX3: трассировка unix sendmsg от foundation (точные сигнатуры 4.14)."""
import re

AF = "/home/kharki/k414/src/net/unix/af_unix.c"
s = open(AF).read()
if "FUNIX" in s:
    print("FUNIX already")
    raise SystemExit(0)

TEMPLATE = (
    "\tif (current->comm[0] == 'f' && current->comm[1] == 'o' &&\n"
    "\t    current->comm[2] == 'u') {\n"
    "\t\tstruct sock *__sk = sock->sk;\n"
    "\t\tpr_info(\"FUNIX __FN__ pid=%d(%s) len=%zu sock=%p\\n\",\n"
    "\t\t\tcurrent->pid, current->comm, len, __sk);\n"
    "\t}\n"
)

patterns = {
    "unix_dgram_sendmsg": r"static int unix_dgram_sendmsg\(struct socket \*sock, struct msghdr \*msg,\n\s*size_t len\)\n\{\n",
    "unix_stream_sendmsg": r"static int unix_stream_sendmsg\(struct socket \*sock, struct msghdr \*msg,\n\s*size_t len\)\n\{\n",
    "unix_seqpacket_sendmsg": r"static int unix_seqpacket_sendmsg\(struct socket \*sock, struct msghdr \*msg,\n\s*size_t len\)\n\{\n",
}

added = 0
for fn, pat in patterns.items():
    m = re.search(pat, s)
    if not m:
        print("anchor missing for", fn)
        continue
    ins = m.group(0) + TEMPLATE.replace("__FN__", fn)
    s = s.replace(m.group(0), ins, 1)
    added += 1
if added:
    open(AF, "w").write(s)
print("FUNIX added:", added)
