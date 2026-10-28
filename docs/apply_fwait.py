#!/usr/bin/env python3
"""FWAIT: печать futex-ожиданий интересующих процессов (owner tid из слова futex)."""
p = "/home/kharki/k414/src/kernel/futex.c"
s = open(p).read()
if "FWAIT pid=" in s:
    print("already instrumented")
    raise SystemExit(0)
anchor = """static int futex_wait(u32 __user *uaddr, unsigned int flags, u32 val,
		      ktime_t *abs_time, u32 bitset)
{
"""
assert anchor in s
ins = anchor + """	{
		static unsigned long __fw_last;
		const char *__cm = current->comm;
		if (__cm[0] == 'f' || __cm[0] == 'h' || __cm[0] == 's' ||
		    __cm[0] == 'm' || __cm[0] == 'p' || __cm[0] == 'b') {
			if (time_after(jiffies, __fw_last + HZ / 4)) {
				__fw_last = jiffies;
				pr_info("FWAIT pid=%d tid=%d(%s) addr=%p val=%08x bitset=%08x\\n",
					current->tgid, current->pid, current->comm,
					uaddr, val, bitset);
			}
		}
	}
"""
s = s.replace(anchor, ins, 1)
open(p, "w").write(s)
print("FWAIT instrumented")
