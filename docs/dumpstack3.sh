#!/system/bin/sh
# dumpstack3.sh - компактно: только потоки с интересными именами/стеками
for d in /proc/[0-9]*; do
  comm=$(cat "$d/comm" 2>/dev/null)
  case "$comm" in
    foundation|sa_main|bms*) ;;
    *) continue ;;
  esac
  p=${d#/proc/}
  echo "=== PID $p comm=$comm ==="
  for t in /proc/$p/task/*; do
    tid=${t##*/}
    tc=$(cat "$t/comm" 2>/dev/null)
    sc=$(cat "$t/syscall" 2>/dev/null | awk '{print $1}')
    st=$(awk '{print $3}' "$t/stat" 2>/dev/null)
    stack=$(cat "$t/stack" 2>/dev/null)
    case "$stack" in
      *binder*) ;;
      *) case "$tc" in SaInit*|*BMS*|*Event*|*bms*) ;; *) continue ;; esac ;;
    esac
    echo "--- tid=$tid comm=$tc state=$st syscall=$sc"
    echo "$stack"
  done
done
echo "=== done ==="
