#!/bin/bash
cd /home/kharki/k414/build2 || exit 1
rm -f /tmp/mi9_414_xattr.log
exec timeout 900 /usr/bin/qemu-system-aarch64 -M virt -cpu cortex-a72 -m 4096 -smp 4 \
  -kernel arch/arm64/boot/Image \
  -append "console=ttyAMA0 root=/dev/vda rw init=/system/bin/init security=selinux selinux=1" \
  -drive file=/home/kharki/hsroot3.img,format=raw,if=virtio \
  -nographic -no-reboot > /tmp/mi9_414_xattr.log 2>&1
