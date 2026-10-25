#!/bin/bash
set -u
export SSHPASS=ubuntu
SSH="sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 ubuntu@127.0.0.1"
SCP="sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222"
cd /home/kharki

cat > module_hdfstub.c <<'MODEOF'
#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>

struct hdf_write_read_buf {
    u32 write_size; u32 write_consumed; u64 write_buffer;
    u32 read_size;  u32 read_consumed;  u64 read_buffer;
    s32 cmd_code;
};

static long hdf_stub_ioctl(struct file *f, unsigned int cmd, unsigned long arg)
{
    struct hdf_write_read_buf bwr;
    if (cmd != _IO('b', 1)) {
        pr_info("hdfstub: unknown cmd %#x\n", cmd);
        return -ENOTTY;
    }
    if (copy_from_user(&bwr, (void __user *)arg, sizeof(bwr)))
        return -EFAULT;

    pr_info("hdfstub: DISPATCH cmdId=%d writeSize=%u readSize=%u\n",
            bwr.cmd_code, bwr.write_size, bwr.read_size);

    if (bwr.write_buffer && bwr.write_size && bwr.write_size < 4096) {
        u8 tmp[64];
        u32 n = bwr.write_size < sizeof(tmp) ? bwr.write_size : sizeof(tmp);
        if (copy_from_user(tmp, (void __user *)(uintptr_t)bwr.write_buffer, n) == 0)
            pr_info("hdfstub: sbuf[0..%u]=%*phN\n", n, n, tmp);
    }

    /* I2C_IO_OPEN == 1: вернуть handle в reply, как это делает драйвер */
    if (bwr.cmd_code == 1) {
        u64 handle = 0x4844465f49324331ULL; /* "HDF_I2C1" */
        if (bwr.read_buffer && bwr.read_size >= 8 &&
            copy_to_user((void __user *)(uintptr_t)bwr.read_buffer, &handle, 8) == 0) {
            bwr.read_consumed = 8;
        }
    }

    if (copy_to_user((void __user *)arg, &bwr, sizeof(bwr)))
        return -EFAULT;
    return 0;
}

static const struct file_operations hdf_stub_fops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = hdf_stub_ioctl,
};

static struct miscdevice hdf_stub_dev = {
    .minor = MISC_DYNAMIC_MINOR,
    .name = "HDF_PLATFORM_I2C_MANAGER",
    .fops = &hdf_stub_fops,
};

static int __init hdf_stub_init(void)
{
    int r = misc_register(&hdf_stub_dev);
    pr_info("hdfstub: misc_register ret=%d node=/dev/HDF_PLATFORM_I2C_MANAGER\n", r);
    return r;
}

static void __exit hdf_stub_exit(void)
{
    misc_deregister(&hdf_stub_dev);
    pr_info("hdfstub: unloaded\n");
}

module_init(hdf_stub_init);
module_exit(hdf_stub_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("HDF_WRITE_READ ioctl stub for ABI validation");
MODEOF

$SCP module_hdfstub.c ubuntu@127.0.0.1:/home/ubuntu/ >/dev/null 2>&1

$SSH "cd /home/ubuntu && make 2>&1 | tail -2 && sudo rmmod module_hdfstub 2>/dev/null; sudo insmod module_hdfstub.ko && sudo chmod 666 /dev/HDF_PLATFORM_I2C_MANAGER && sudo dmesg -C >/dev/null
cd /home/ubuntu/hdfpay && LD_LIBRARY_PATH=. ./libc.so ./harness_i2c.exe ./libhdf_platform.z.so 2>&1 | grep -v HiLogBase | head -10
echo ===KERNEL===
sudo dmesg | grep -i hdfstub" 2>&1 | grep -v "Warning: Permanently"
