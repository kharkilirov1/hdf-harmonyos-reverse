#!/bin/bash
set -u
cd /home/kharki/k414/src || exit 1
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
export KBUILD_CFLAGS="-fcommon -Wno-error"
export KCFLAGS="-fcommon"

cp /mnt/c/Users/Kharki/Desktop/hdf_contract/09_mi9_kernel.config .config

SC=scripts/config
# QEMU virt
$SC --enable SERIAL_AMBA
$SC --enable SERIAL_AMBA_PL011
$SC --enable SERIAL_AMBA_PL011_CONSOLE
$SC --enable ARM_AMBA
$SC --enable PCI
$SC --enable PCI_HOST_GENERIC
$SC --enable VIRTIO
$SC --enable VIRTIO_PCI
$SC --enable VIRTIO_MMIO
$SC --enable VIRTIO_BLK
$SC --enable VIRTIO_NET
$SC --enable BLK_DEV_INITRD
$SC --enable DEVTMPFS
$SC --enable DEVTMPFS_MOUNT
# выключаем Qualcomm-специфику, которой нет в QEMU (необязательно)
$SC --disable QCOM_RNDIS 2>/dev/null
$SC --disable MSM_GENI_SERIAL 2>/dev/null

echo "=== olddefconfig $(date) ==="
make olddefconfig > /tmp/k414_olddef.log 2>&1
echo "rc=$? (warnings: $(grep -c 'unknown option' /tmp/k414_olddef.log 2>/dev/null))"
grep -E "CONFIG_VIRTIO_BLK=|CONFIG_VIRTIO_PCI=|CONFIG_SERIAL_AMBA_PL011_CONSOLE=|CONFIG_ANDROID_BINDER_IPC=|CONFIG_EXT4_FS=|CONFIG_SECURITY_SELINUX=" .config

echo "=== build start $(date) ==="
make -j"$(nproc)" Image > /tmp/k414_build.log 2>&1
echo "BUILD_RC=$? $(date)"
tail -40 /tmp/k414_build.log
ls -lh arch/arm64/boot/Image 2>/dev/null
