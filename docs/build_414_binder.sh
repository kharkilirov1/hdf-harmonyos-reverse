#!/bin/bash
set -u
cd /home/kharki/k414/src || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
B=/home/kharki/k414/build2
export KBUILD_CFLAGS="-Wno-error"
SC="scripts/config --file $B/.config"
# Android-подсистемы (binder/ashmem) — нужны samgr/IPC
$SC --enable STAGING
$SC --enable ANDROID
$SC --enable ANDROID_BINDER_IPC
$SC --enable ANDROID_BINDERFS
$SC --enable ANDROID_BINDER_DEVICES "binder,hwbinder,vndbinder"
$SC --enable ASHMEM
$SC --enable STAGING_ANDROID 2>/dev/null || true
make O="$B" olddefconfig > /tmp/k414_4_olddef.log 2>&1 || { echo OLDDEF_FAIL; tail -5 /tmp/k414_4_olddef.log; exit 1; }
echo "--- config ---"
grep -E "CONFIG_ANDROID=|CONFIG_ANDROID_BINDER_IPC=|CONFIG_ANDROID_BINDERFS=|CONFIG_ASHMEM=|CONFIG_SECURITY_SELINUX=" "$B/.config"
echo "--- build ---"
make O="$B" -j"$(nproc)" Image > /tmp/k414_4_build.log 2>&1
echo "BUILD_RC=$?"
tail -4 /tmp/k414_4_build.log
ls -lh "$B/arch/arm64/boot/Image" 2>/dev/null
