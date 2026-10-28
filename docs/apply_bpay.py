#!/usr/bin/env python3
"""BPAY: печать первых 32 байт payload (после копирования в buffer)."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()
if "BPAY to=" in s:
    print("already instrumented")
    raise SystemExit(0)
anchor = "\tif (copy_from_user(offp, (const void __user *)(uintptr_t)\n"
assert anchor in s
ins = """	if (!reply && target_proc->tsk && t->buffer) {
		const char *__tc = target_proc->tsk->comm;
		u32 *__d = (u32 *)(void *)t->buffer->data;
		if ((__tc[0] == 's' && __tc[1] == 'a' && __tc[2] == 'm') ||
		    (__tc[0] == 'h' && __tc[1] == 'd') ||
		    (__tc[0] == 'i' && __tc[1] == 'n') ||
		    (__tc[0] == 'p' && __tc[1] == 'a')) {
			pr_info("BPAY to=%s code=%u flags=%x sz=%zu d=%08x %08x %08x %08x %08x %08x %08x %08x\\n",
				__tc, t->code, t->flags, (size_t)tr->data_size,
				__d[0], __d[1], __d[2], __d[3],
				__d[4], __d[5], __d[6], __d[7]);
		}
	}
""" + anchor
s = s.replace(anchor, ins, 1)
open(p, "w").write(s)
print("BPAY instrumented v2")
