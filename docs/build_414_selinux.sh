#!/bin/bash
set -u
cd /home/kharki/k414/src || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
B=/home/kharki/k414/build2
export KBUILD_CFLAGS="-Wno-error"
rm -rf "$B"; mkdir -p "$B"
make O="$B" defconfig > /tmp/k414_3_def.log 2>&1 || { echo DEFCONFIG_FAIL; exit 1; }
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
$SC --enable SECURITY_NETWORK
$SC --enable SECURITY_SELINUX
$SC --enable SECURITY_SELINUX_BOOTPARAM
$SC --enable SECURITY_SELINUX_DEVELOP
$SC --enable DEFAULT_SECURITY_SELINUX
$SC --enable NETWORK_SECMARK
$SC --enable BLK_DEV_INITRD
$SC --enable DEVTMPFS
$SC --enable DEVTMPFS_MOUNT
make O="$B" olddefconfig > /tmp/k414_3_olddef.log 2>&1 || { echo OLDDEF_FAIL; tail -5 /tmp/k414_3_olddef.log; exit 1; }
echo "--- config check ---"
grep -E "CONFIG_SECURITY_SELINUX=|CONFIG_SECURITY_NETWORK=|CONFIG_VIRTIO_BLK=|CONFIG_SERIAL_AMBA_PL011_CONSOLE=|CONFIG_ANDROID_BINDER_IPC=" "$B/.config"
echo "--- build ---"
make O="$B" -j"$(nproc)" Image > /tmp/k414_3_build.log 2>&1
echo "BUILD_RC=$?"
tail -6 /tmp/k414_3_build.log
ls -lh "$B/arch/arm64/boot/Image" 2>/dev/null
