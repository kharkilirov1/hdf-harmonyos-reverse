#!/usr/bin/env python3
"""BPAYR: печать payload ОТВЕТОВ (reply), приходящих в foundation — там коды
ошибок установки (0x82xxxx) от installd/BMS."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()
if "BPAYR to=" in s:
    print("already instrumented")
    raise SystemExit(0)
anchor = "\tif (copy_from_user(offp, (const void __user *)(uintptr_t)\n"
assert anchor in s
ins = """	if (reply && target_proc->tsk && t->buffer) {
		const char *__tc = target_proc->tsk->comm;
		u32 *__d = (u32 *)(void *)t->buffer->data;
		if (__tc[0] == 'f' && __tc[1] == 'o' && __tc[2] == 'u') {
			pr_info("BPAYR to=%s from=%d code=%u sz=%zu d=%08x %08x %08x %08x %08x %08x\\n",
				__tc, proc->pid, t->code, (size_t)tr->data_size,
				__d[0], __d[1], __d[2], __d[3], __d[4], __d[5]);
		}
	}
""" + anchor
s = s.replace(anchor, ins, 1)
open(p, "w").write(s)
print("BPAYR instrumented")
