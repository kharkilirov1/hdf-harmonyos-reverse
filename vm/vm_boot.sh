#!/bin/bash
cd /home/kharki || exit 1
pkill -f qemu-system-x86_64 2>/dev/null
sleep 1
setsid /usr/bin/qemu-system-x86_64 -m 4096 -smp 4 -enable-kvm \
  -drive file=/home/kharki/noble.img,if=virtio,format=qcow2 \
  -drive file=/home/kharki/seed.img,if=virtio,format=raw \
  -netdev user,id=n1,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=n1 \
  -nographic -serial file:/home/kharki/hdfvm4.log -monitor none \
  </dev/null >/dev/null 2>&1 &
echo "qemu launcher pid=$!"
exit 0
