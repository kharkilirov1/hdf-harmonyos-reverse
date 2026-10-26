#include <linux/module.h>
#include <linux/fs.h>
#include <linux/miscdevice.h>
#include <linux/uaccess.h>

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

static const struct file_operations bbox_fops = {
	.owner = THIS_MODULE,
	.write = bbox_write,
	.read = bbox_read,
};

static struct miscdevice bbox_dev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "bbox",
	.fops = &bbox_fops,
	.mode = 0660,
};

static int __init bbox_init(void)
{
	int r = misc_register(&bbox_dev);
	pr_info("bbox_stub: register %d\n", r);
	return r;
}
device_initcall(bbox_init);
