#!/system/bin/sh
# dumpstack12.sh - состояния потоков foundation по секундам (до выхода main)
n=0
while [ $n -lt 14 ]; do
  n=$((n+1))
  for d in /proc/[0-9]*; do
    comm=$(cat "$d/comm" 2>/dev/null)
    [ "$comm" = "foundation" ] || continue
    p=${d#/proc/}
    f=/data/diag/th_${p}_${n}.txt
    {
      echo "=== iter $n pid $p uptime $(cut -d" " -f1 /proc/uptime) ==="
      grep -a "^Threads" /proc/$p/status 2>/dev/null
      for t in /proc/$p/task/*; do
        tid=${t##*/}
        echo "$tid $(cat $t/comm 2>/dev/null) $(cat $t/syscall 2>/dev/null | cut -c1-30)"
      done
    } > "$f" 2>/dev/null
  done
  sleep 2
done
echo "=== done ==="
