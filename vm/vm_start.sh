#!/bin/bash
set -x
cd ~
rm -f seed.img hdfvm.log
# resize root fs to 12G
qemu-img resize noble.img 12G

cat > user-data.yaml <<'EOF'
#cloud-config
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG1vY2tLZXlGb3JIREZUZXN0MTIzNDU2Nzg5MDEyMzQ1Njc4OTAgbW9jaw== hdf-test
ssh_pwauth: true
chpasswd:
  list: |
    ubuntu:ubuntu
  expire: false
package_update: false
package_upgrade: false
EOF

cat > meta-data.yaml <<'EOF'
instance-id: hdfvm
local-hostname: hdfvm
EOF

cloud-localds seed.img user-data.yaml meta-data.yaml

nohup qemu-system-x86_64 -m 4096 -smp 4 -enable-kvm \
  -drive file=noble.img,if=virtio,format=qcow2 \
  -drive file=seed.img,if=virtio,format=raw \
  -netdev user,id=n1,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=n1 \
  -nographic -serial file:hdfvm.log -monitor none \
  > /dev/null 2>&1 &

echo "qemu pid $!"
sleep 30
tail -5 hdfvm.log 2>/dev/null
