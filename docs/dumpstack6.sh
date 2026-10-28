#!/system/bin/sh
# dumpstack6.sh - TIDMAP: карта tid -> comm (и tgid) для корреляции с FWAIT
for d in /proc/[0-9]*; do
  p=${d#/proc/}
  for t in /proc/$p/task/*; do
    tid=${t##*/}
    echo "T $tid $p $(cat "$t/comm" 2>/dev/null)"
  done
done
echo "=== done ==="
