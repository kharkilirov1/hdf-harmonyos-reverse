/* access_token_id_stub.c — минимальный драйвер /dev/access_token_id для HarmonyOS userland.
 *
 * Зачем: HarmonyOS libipc_common/GetSelfTokenID открывает /dev/access_token_id
 * и делает ioctl:
 *   0x80084101  _IOR('A', 1, u64)  — GetSelfTokenID
 *   0x80084103  _IOR('A', 3, u64)  — GetSelfFirstCallerTokenID
 * (в бинарях прошивки 6.0.0.108, libipc_common.z.so, disasm ede8/ef8c)
 * Обычно этот узел создаёт вендорский драйвер CONFIG_ACCESS_TOKENID, которого
 * нет в mainline. Заглушка хранит tokenId по pid и позволяет сервисам
 * access_token инициализироваться.
 */
#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/pid.h>
#include <linux/sched.h>

#define AT_GET_SELF   _IOR('A', 1, u64)
#define AT_SET_SELF   _IOW('A', 2, u64)
#define AT_GET_CALLER _IOR('A', 3, u64)

struct at_entry {
	struct list_head list;
	pid_t pid;
	u64 token;
};

static LIST_HEAD(at_list);
static DEFINE_SPINLOCK(at_lock);
static u64 default_token;

static u64 at_get(pid_t pid)
{
	struct at_entry *e;
	u64 v = 0;
	spin_lock(&at_lock);
	list_for_each_entry(e, &at_list, list) {
		if (e->pid == pid) {
			v = e->token;
			break;
		}
	}
	spin_unlock(&at_lock);
	return v;
}

static void at_set(pid_t pid, u64 token)
{
	struct at_entry *e, *n;
	spin_lock(&at_lock);
	list_for_each_entry(e, &at_list, list) {
		if (e->pid == pid) {
			e->token = token;
			spin_unlock(&at_lock);
			return;
		}
	}
	n = kmalloc(sizeof(*n), GFP_ATOMIC);
	if (n) {
		n->pid = pid;
		n->token = token;
		list_add(&n->list, &at_list);
	}
	spin_unlock(&at_lock);
}

static long at_ioctl(struct file *f, unsigned int cmd, unsigned long arg)
{
	u64 val = 0;
	pid_t pid = task_tgid_nr(current);

	switch (cmd) {
	case AT_GET_SELF:
		val = at_get(pid);
		if (!val)
			val = default_token;
		if (copy_to_user((void __user *)arg, &val, sizeof(val)))
			return -EFAULT;
		return 0;
	case AT_SET_SELF:
		if (copy_from_user(&val, (void __user *)arg, sizeof(val)))
			return -EFAULT;
		if (!val)
			val = default_token;
		at_set(pid, val);
		return 0;
	case AT_GET_CALLER:
		val = at_get(pid);
		if (!val)
			val = default_token;
		if (copy_to_user((void __user *)arg, &val, sizeof(val)))
			return -EFAULT;
		return 0;
	default:
		pr_info("access_token_id: unknown ioctl 0x%08x\n", cmd);
		return -ENOTTY;
	}
}

static int at_open(struct inode *inode, struct file *f) { return 0; }
static int at_release(struct inode *inode, struct file *f) { return 0; }

static const struct file_operations at_fops = {
	.owner = THIS_MODULE,
	.open = at_open,
	.release = at_release,
	.unlocked_ioctl = at_ioctl,
	.compat_ioctl = at_ioctl,
};

static struct miscdevice at_dev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "access_token_id",
	.fops = &at_fops,
	.mode = 0666,
};

static int __init at_init(void)
{
	int r = misc_register(&at_dev);
	if (r)
		pr_err("access_token_id: misc_register failed %d\n", r);
	else
		pr_info("access_token_id: stub device registered\n");
	return r;
}

static void __exit at_exit(void)
{
	struct at_entry *e, *n;
	spin_lock(&at_lock);
	list_for_each_entry_safe(e, n, &at_list, list) {
		list_del(&e->list);
		kfree(e);
	}
	spin_unlock(&at_lock);
	misc_deregister(&at_dev);
}

module_init(at_init);
module_exit(at_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("access_token_id stub for HarmonyOS userland experiments");
