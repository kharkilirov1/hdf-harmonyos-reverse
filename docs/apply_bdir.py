#!/usr/bin/env python3
"""BTGT-v2: печать направленных транзакций (запросы code<=5 и все ответы)
с comm цели; по каждой паре (from,to,code) не чаще 1 раза в 5 секунд."""
p = "/home/kharki/k414/src/drivers/android/binder.c"
s = open(p).read()

# удалить старую BINIT-вставку, если есть
start = s.find("\tif (!reply && target_proc->tsk) {")
if start != -1:
    end = s.find("\t}\n", s.find("__last_tgt_print", start))
    # найти конец блока: ищем "\t}\n\t}\n" после
    tail = s.find("\t\t}\n\t}\n", start)
    if tail != -1:
        s = s[:start] + s[tail + len("\t\t}\n\t}\n"):]
        print("old BINIT block removed")

if "BDIR reply" in s:
    print("already instrumented v2")
    raise SystemExit(0)

anchor = "\tt->priority = task_nice(current);\n"
if anchor not in s:
    raise SystemExit("anchor not found")

block = r'''	{
		static u32 __bd[16][3];
		static unsigned long __bdj[16];
		u32 k0 = (u32)proc->pid;
		u32 k1 = (u32)target_proc->pid;
		u32 k2 = t->code | ((u32)t->flags << 16);
		int i, slot = -1;
		for (i = 0; i < 16; i++) {
			if (__bd[i][0] == k0 && __bd[i][1] == k1 && __bd[i][2] == k2) {
				slot = i;
				break;
			}
			if (slot < 0 && __bd[i][0] == 0)
				slot = i;
		}
		if (slot < 0)
			slot = (int)((k0 ^ k1 ^ k2) & 15);
		if (__bd[slot][0] != k0 || __bd[slot][1] != k1 ||
		    __bd[slot][2] != k2 || time_after(jiffies, __bdj[slot] + 5 * HZ)) {
			__bd[slot][0] = k0;
			__bd[slot][1] = k1;
			__bd[slot][2] = k2;
			__bdj[slot] = jiffies;
			if ((!reply && t->code <= 5) || reply)
				pr_info("BDIR r=%d from=%d to=%d(%s) code=%u flags=%x\n",
					reply ? 1 : 0, proc->pid, target_proc->pid,
					(target_proc->tsk ? target_proc->tsk->comm : "?"),
					t->code, t->flags);
		}
	}
'''
s = s.replace(anchor, anchor + block, 1)
open(p, "w").write(s)
print("BDIR v2 instrumented")
