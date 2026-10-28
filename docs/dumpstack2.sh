#!/system/bin/sh
# dumpstack2.sh - снять kernel-стеки потоков foundation/sa_main (нужен CONFIG_STACKTRACE)
PIDS=""
for c in foundation sa_main bms installd; do
  for r in $(pidof $c 2>/dev/null); do PIDS="$PIDS $r"; done
done
for d in /proc/[0-9]*; do
  cm=$(cat "$d/comm" 2>/dev/null)
  case "$cm" in
    foundation*|sa_main*|bms*) PIDS="$PIDS ${d#/proc/}" ;;
  esac
done
echo "PIDS:$PIDS"
for p in $PIDS; do
  echo "=== PID $p comm=$(cat /proc/$p/comm 2>/dev/null) ==="
  for t in /proc/$p/task/*; do
    tid=$(basename "$t")
    st=$(awk '{print $3}' "$t/stat" 2>/dev/null)
    sc=$(cat "$t/syscall" 2>/dev/null)
    echo "--- tid=$tid state=$st syscall=$sc"
    cat "$t/stack" 2>/dev/null
  done
done
echo "=== done ==="
