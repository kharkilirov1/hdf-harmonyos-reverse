#!/system/bin/sh
# dumpstack7.sh - цикл: снимки hilog + TIDMAP/стеки, один запуск на старт foundation
n=0
while [ $n -lt 5 ]; do
  n=$((n+1))
  /system/bin/hilog > /data/diag/hs_${n}_$$.log 2>/dev/null
  sleep 40
done
for d in /proc/[0-9]*; do
  comm=$(cat "$d/comm" 2>/dev/null)
  case "$comm" in
    foundation|hdf_devmgr|sa_main|bms*) ;;
    *) continue ;;
  esac
  p=${d#/proc/}
  echo "=== PID $p $comm ==="
  for t in /proc/$p/task/*; do
    echo "--- ${t##*/} $(cat "$t/comm" 2>/dev/null) $(cat "$t/syscall" 2>/dev/null)"
    cat "$t/stack" 2>/dev/null
  done
done
echo "=== done ==="
