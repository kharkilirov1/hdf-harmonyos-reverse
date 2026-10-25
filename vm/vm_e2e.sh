#!/bin/bash
# End-to-end: real phone libhdf_platform (x86_64 musl) -> real kernel module in VM.
set -u
export SSHPASS=ubuntu
SSH="sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -p 2222 ubuntu@127.0.0.1"
SCP="sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222"
PAY=/home/kharki/hdfpay

for i in $(seq 1 12); do
  cd /home/kharki
  tar cf hdfpay.tar hdfpay
  $SCP hdfpay.tar ubuntu@127.0.0.1:/home/ubuntu/ >/dev/null 2>&1
  OUT=$($SSH "cd /home/ubuntu && rm -rf hdfpay && tar xf hdfpay.tar && cd hdfpay && chmod +x harness_i2c.exe libc.so && sudo dmesg -C >/dev/null && LD_LIBRARY_PATH=. ./libc.so ./harness_i2c.exe ./libhdf_platform.z.so 2>&1 | grep -v HiLogBase | head -8" 2>&1)
  MISS=$(echo "$OUT" | grep -o "Error loading shared library [A-Za-z0-9._+-]*" | head -1 | awk '{print $NF}')
  echo "=== iter $i: missing='$MISS' ==="
  if [ -z "$MISS" ]; then
      echo "--- harness output ---"; echo "$OUT"
      echo "--- kernel side ---"
      $SSH "sudo dmesg | grep -i hdfstub" 2>&1
      echo "E2E_DONE"
      break
  fi
  SRC=$(find /mnt/emu -name "$MISS" 2>/dev/null | head -1)
  if [ -z "$SRC" ]; then echo "NOT FOUND in image: $MISS"; break; fi
  cp -L "$SRC" "$PAY/$MISS"
  echo "copied $MISS from $SRC"
done
