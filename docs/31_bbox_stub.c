#include <linux/module.h>
#include <linux/fs.h>
#include <linux/miscdevice.h>
#include <linux/uaccess.h>
#include <linux/sysctl.h>
#include <linux/proc_fs.h>

static ssize_t bbox_write(struct file *f, const char __user *buf, size_t len, loff_t *off)
{
	char tmp[128];
	size_t n = len < sizeof(tmp)-1 ? len : sizeof(tmp)-1;
	if (copy_from_user(tmp, buf, n)) return -EFAULT;
	tmp[n] = 0;
	pr_info("bbox_stub: write %zu bytes: %.64s\n", len, tmp);
	return len;
}

static ssize_t bbox_read(struct file *f, char __user *buf, size_t len, loff_t *off)
{
	return 0;
}

static long bbox_ioctl(struct file *f, unsigned int cmd, unsigned long arg)
{
	pr_info("bbox_stub: ioctl cmd=0x%x\n", cmd);
	return 0;
}

static const struct file_operations bbox_fops = {
	.owner = THIS_MODULE,
	.write = bbox_write,
	.read = bbox_read,
	.unlocked_ioctl = bbox_ioctl,
};

static struct miscdevice bbox_dev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "bbox",
	.fops = &bbox_fops,
	.mode = 0660,
};

static char hguard_buf[512] = "0:0:0\n";

static struct ctl_table hguard_children[] = {
	{
		.procname = "user_list",
		.data = hguard_buf,
		.maxlen = sizeof(hguard_buf),
		.mode = 0666,
		.proc_handler = proc_dostring,
	},
	{}
};

static struct ctl_table hguard_root[] = {
	{
		.procname = "hguard",
		.mode = 0555,
		.child = hguard_children,
	},
	{}
};

static struct ctl_table_header *hguard_hdr;

static int __init bbox_init(void)
{
	int r = misc_register(&bbox_dev);
	pr_info("bbox_stub: register %d\n", r);
	hguard_hdr = register_sysctl_table(hguard_root);
	pr_info("hguard_stub: register %s\n", hguard_hdr ? "ok" : "fail");
	return r;
}
device_initcall(bbox_init);
