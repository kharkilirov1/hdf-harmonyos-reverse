#!/bin/bash
cd /home/kharki/k414/build2 || exit 1
rm -f /tmp/mi9_bootevents.log
exec timeout 600 /usr/bin/qemu-system-aarch64 -M virt -cpu cortex-a72 -m 4096 -smp 4 \
  -kernel arch/arm64/boot/Image \
  -append "console=ttyAMA0 root=/dev/vda rw init=/system/bin/init security=selinux selinux=1 enforcing=0 bootevent.samgr.ready=true bootevent.appfwk.ready=true bootevent.launcher.ready=true bootevent.wms.ready=true bootevent.renderservice.ready=true bootevent.lockscreen.ready=true bootevent.param_watcher.started=true bootevent.hdf_devmgr.ready=true" \
  -drive file=/home/kharki/hsroot2.img,format=raw,if=virtio \
  -nographic -no-reboot > /tmp/mi9_bootevents.log 2>&1
