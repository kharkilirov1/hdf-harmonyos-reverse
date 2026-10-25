#!/bin/bash
# Сборка harness'ов под OHOS musl (x86_64). Правьте SDK_PATH под свою установку.
set -e
SDK_PATH="${SDK_PATH:-/c/Program Files/Huawei/DevEco Studio/sdk/default/openharmony/native}"
CLANG="$SDK_PATH/llvm/bin/clang.exe"
SYSROOT="$SDK_PATH/sysroot"
for src in harness_i2c harness_ark harness_ark2 harness_ark3 harness_dlopen harness_ipc; do
  [ -f "$src.c" ] || continue
  "$CLANG" --target=x86_64-linux-ohos --sysroot="$SYSROOT" -O0 -o "$src.exe" "$src.c" -ldl
  echo "built $src.exe"
done
"$CLANG" --target=x86_64-linux-ohos --sysroot="$SYSROOT" -O1 -fPIC -shared \
  -o shim_ioctl.so shim_ioctl.c -ldl
"$CLANG" --target=x86_64-linux-ohos --sysroot="$SYSROOT" -O1 -fPIC -shared \
  -o libhilog_stub.so stub_hilog.c
echo "built shim_ioctl.so, libhilog_stub.so"