#!/bin/bash
set -u
SRC=/home/kharki/hp6
M=/mnt
sudo mkdir -p $M/sys16 $M/ven16 $M/spr16 $M/hs2
for p in sys16:system.img ven16:vendor.img spr16:sys_prod.img; do
  d=${p%%:*}; img=${p##*:}
  sudo umount $M/$d 2>/dev/null
  sudo mount -o loop,ro $SRC/$img $M/$d || { echo "MOUNT_FAIL $img"; exit 1; }
  echo "mounted $img -> $M/$d"
done

rm -f /home/kharki/hsroot3.img
truncate -s 14G /home/kharki/hsroot3.img
sudo mkfs.ext4 -q -F -O ^metadata_csum_seed,^64bit /home/kharki/hsroot3.img
sudo umount $M/hs2 2>/dev/null
sudo mount -o loop /home/kharki/hsroot3.img $M/hs2 || { echo MOUNT_DST_FAIL; exit 1; }

echo "=== copy system (with xattrs) ==="
sudo cp -a --preserve=all $M/sys16/. $M/hs2/
echo "=== copy vendor ==="
sudo mkdir -p $M/hs2/vendor
sudo cp -a --preserve=all $M/ven16/. $M/hs2/vendor/
echo "=== copy sys_prod ==="
sudo mkdir -p $M/hs2/sys_prod
sudo cp -a --preserve=all $M/spr16/. $M/hs2/sys_prod/

echo "=== xattr check ==="
getfattr -d -m - $M/hs2/system/bin/init 2>/dev/null | tail -1
getfattr -d -m - $M/hs2/vendor/lib64/libhdf_platform.z.so 2>/dev/null | tail -1

sudo sync
sudo umount $M/hs2
sudo umount $M/sys16 $M/ven16 $M/spr16 2>/dev/null
ls -lh /home/kharki/hsroot3.img
echo DONE
