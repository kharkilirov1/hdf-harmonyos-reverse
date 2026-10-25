#!/bin/bash
set -u
cd /home/kharki/k414/src || exit 1
B=/home/kharki/k414/build2
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
rm -rf "$B"; mkdir -p "$B"
make O="$B" defconfig > /tmp/k414_2_defconfig.log 2>&1
echo "defconfig rc=$?"
SC="scripts/config --file $B/.config"
$SC --enable VIRTIO
$SC --enable VIRTIO_PCI
$SC --enable VIRTIO_MMIO
$SC --enable VIRTIO_BLK
$SC --enable VIRTIO_NET
$SC --enable SERIAL_AMBA_PL011
$SC --enable SERIAL_AMBA_PL011_CONSOLE
$SC --enable ARM_AMBA
$SC --enable PCI
$SC --enable PCI_HOST_GENERIC
$SC --enable ANDROID_BINDER_IPC
$SC --enable ASHMEM
$SC --enable SECURITY_SELINUX
$SC --enable BLK_DEV_INITRD
$SC --enable DEVTMPFS
$SC --enable DEVTMPFS_MOUNT
make O="$B" olddefconfig > /tmp/k414_2_olddef.log 2>&1
grep -E "CONFIG_VIRTIO_BLK=|CONFIG_SERIAL_AMBA_PL011_CONSOLE=|CONFIG_ANDROID_BINDER_IPC=|CONFIG_SECURITY_SELINUX=" "$B/.config"
echo "=== build start $(date) ==="
make O="$B" -j"$(nproc)" Image > /tmp/k414_2_build.log 2>&1
echo "BUILD_RC=$? $(date)"
tail -8 /tmp/k414_2_build.log
ls -lh "$B/arch/arm64/boot/Image" 2>/dev/null
