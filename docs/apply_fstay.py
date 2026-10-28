#!/usr/bin/env python3
"""FSTAY: не даём foundation/sa_main завершиться: sys_exit_group для них
превращается в бесконечное ожидание (процесс остаётся жив, SA 401 не умирает)."""
p = "/home/kharki/k414/src/kernel/exit.c"
s = open(p).read()
if "FSTAY STAY" in s:
    print("already")
    raise SystemExit(0)

old = """SYSCALL_DEFINE1(exit_group, int, error_code)
{
	do_group_exit((error_code & 0xff) << 8);
	/* NOTREACHED */
	return 0;
}"""
new = """SYSCALL_DEFINE1(exit_group, int, error_code)
{
	{
		const char *__c = current->comm;
		if ((__c[0] == 'f' && __c[1] == 'o' && __c[2] == 'u') ||
		    (__c[0] == 's' && __c[1] == 'a' && __c[2] == '_')) {
			pr_info("FSTAY STAY pid=%d tgid=%d comm=%s code=%d\\n",
				current->pid, current->tgid, __c, error_code);
			for (;;) {
				set_current_state(TASK_UNINTERRUPTIBLE);
				schedule_timeout(HZ);
			}
		}
	}
	do_group_exit((error_code & 0xff) << 8);
	/* NOTREACHED */
	return 0;
}"""
if old not in s:
    raise SystemExit("exit_group anchor not found")
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("FSTAY added")
