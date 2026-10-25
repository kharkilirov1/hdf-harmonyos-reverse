#!/bin/bash
set -u
cd ~
pkill -f qemu-system-x86_64 2>/dev/null; sleep 2

cat > user-data.yaml <<'UDEOF'
#cloud-config
instance-id: hdfvm3
local-hostname: hdfvm3
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
ssh_pwauth: true
chpasswd:
  list: |
    ubuntu:ubuntu
  expire: false
package_update: false
package_upgrade: false
UDEOF

cat > meta-data.yaml <<'MDEOF'
instance-id: hdfvm3
local-hostname: hdfvm3
MDEOF

rm -f seed.img hdfvm3.log
cloud-localds seed.img user-data.yaml meta-data.yaml

nohup qemu-system-x86_64 -m 4096 -smp 4 -enable-kvm \
  -drive file=noble.img,if=virtio,format=qcow2 \
  -drive file=seed.img,if=virtio,format=raw \
  -netdev user,id=n1,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=n1 \
  -nographic -serial file:hdfvm3.log -monitor none \
  > /dev/null 2>&1 &
echo "qemu started pid $!"
sleep 45
tail -3 hdfvm3.log | sed 's/\x1b\[[0-9;]*m//g'
