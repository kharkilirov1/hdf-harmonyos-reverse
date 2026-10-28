#!/system/bin/sh
# dumpstack11.sh - карты памяти foundation + стеки в первые секунды жизни процесса
n=0
while [ $n -lt 4 ]; do
  n=$((n+1))
  for d in /proc/[0-9]*; do
    comm=$(cat "$d/comm" 2>/dev/null)
    [ "$comm" = "foundation" ] || continue
    p=${d#/proc/}
    cat /proc/$p/maps > /data/diag/maps_${p}_${n}.txt 2>/dev/null
    {
      echo "=== iter $n pid $p ==="
      for t in /proc/$p/task/*; do
        echo "--- ${t##*/} $(cat "$t/comm" 2>/dev/null)"
        cat "$t/stack" 2>/dev/null
      done
    } > /data/diag/fst_${p}_${n}.txt 2>/dev/null
  done
  sleep 4
done
echo "=== done ==="
