#!/bin/bash
set -u
cd ~
pkill -f qemu-system-x86_64 2>/dev/null; sleep 2

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
    bwr.read_consumed = 0;
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

cat > Makefile <<'MKEOF'
obj-m += module_hdfstub.o
all:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
MKEOF

cat > test_ioctl.c <<'TEOF'
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/ioctl.h>

struct hdf_write_read_buf {
    uint32_t write_size; uint32_t write_consumed; uint64_t write_buffer;
    uint32_t read_size;  uint32_t read_consumed;  uint64_t read_buffer;
    int32_t  cmd_code;
};

static int call(int fd, const char *name, int cmd, unsigned char *wbuf, uint32_t wlen)
{
    unsigned char rbuf[128];
    struct hdf_write_read_buf b;
    memset(&b, 0, sizeof(b));
    b.write_size = wlen;
    b.write_buffer = (uint64_t)(uintptr_t)wbuf;
    b.read_size = sizeof(rbuf);
    b.read_buffer = (uint64_t)(uintptr_t)rbuf;
    b.cmd_code = cmd;
    errno = 0;
    int r = ioctl(fd, 0x6201, &b);
    printf("[test] %s: ioctl(0x6201) cmdId=%d -> r=%d errno=%d (%s)\n",
           name, cmd, r, errno, strerror(errno));
    return r;
}

int main(void)
{
    const char *node = "/dev/HDF_PLATFORM_I2C_MANAGER";
    int fd = open(node, O_RDWR);
    if (fd < 0) { printf("[test] open(%s) FAILED errno=%d\n", node, errno); return 1; }
    printf("[test] open(%s) OK fd=%d\n", node, fd);

    unsigned char bus = 0;
    unsigned char msg[28] = {0};
    unsigned char close_payload[4] = {0};

    call(fd, "I2C_IO_OPEN",     1, &bus, 4);
    call(fd, "I2C_IO_TRANSFER", 0, msg, sizeof(msg));
    call(fd, "I2C_IO_CLOSE",    2, close_payload, 4);

    close(fd);
    printf("[test] done\n");
    return 0;
}
TEOF

cat > user-data.yaml <<'UDEOF'
#cloud-config
instance-id: hdfvm2
local-hostname: hdfvm2
write_files:
  - path: /root/module_hdfstub.c
    permissions: '0644'
    content: |
UDEOF
sed -e 's/^/      /' module_hdfstub.c >> user-data.yaml
cat >> user-data.yaml <<'UDEOF'
  - path: /root/Makefile
    permissions: '0644'
    content: |
UDEOF
sed -e 's/^/      /' Makefile >> user-data.yaml
cat >> user-data.yaml <<'UDEOF'
  - path: /root/test_ioctl.c
    permissions: '0644'
    content: |
UDEOF
sed -e 's/^/      /' test_ioctl.c >> user-data.yaml
cat >> user-data.yaml <<'UDEOF'
runcmd:
  - [ bash, -lc, "exec > /dev/ttyS0 2>&1; echo HDFSTUB_TEST_START; export DEBIAN_FRONTEND=noninteractive; apt-get update -qq; apt-get install -y -qq gcc make linux-headers-$(uname -r); cd /root; make 2>&1 | tail -5; insmod module_hdfstub.ko; ls -l /dev/HDF_PLATFORM_I2C_MANAGER; gcc -O0 -o test_ioctl test_ioctl.c; ./test_ioctl; echo '--- dmesg ---'; dmesg | grep -i hdfstub; echo HDFSTUB_TEST_END; poweroff -f" ]
UDEOF

cat > meta-data.yaml <<'MDEOF'
instance-id: hdfvm2
local-hostname: hdfvm2
MDEOF

rm -f seed.img hdfvm2.log
cloud-localds seed.img user-data.yaml meta-data.yaml

nohup qemu-system-x86_64 -m 4096 -smp 4 -enable-kvm \
  -drive file=noble.img,if=virtio,format=qcow2 \
  -drive file=seed.img,if=virtio,format=raw \
  -netdev user,id=n1 \
  -device virtio-net-pci,netdev=n1 \
  -nographic -serial file:hdfvm2.log -monitor none \
  > /dev/null 2>&1 &
echo "qemu started pid $!"
