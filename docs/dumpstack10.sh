#!/system/bin/sh
# dumpstack10.sh - цикл hilog-снимков: ждём непустого файла до 20 c, затем kill
n=0
while [ $n -lt 8 ]; do
  n=$((n+1))
  f=/data/diag/hc_${n}_$$.log
  : > "$f"
  /system/bin/hilog > "$f" 2>/dev/null &
  hp=$!
  i=0
  while [ $i -lt 20 ]; do
    sleep 1
    [ -s "$f" ] && break
    i=$((i+1))
  done
  kill -9 $hp 2>/dev/null
  sleep 70
done
echo "=== done ==="
