#!/system/bin/sh
# dumpstack4.sh - стеки потоков подозреваемых процессов
for d in /proc/[0-9]*; do
  comm=$(cat "$d/comm" 2>/dev/null)
  case "$comm" in
    foundation|sa_main|bms*|hdf_devmgr|msdp_sa|param_watcher|installs) ;;
    *) continue ;;
  esac
  p=${d#/proc/}
  echo "=== PID $p comm=$comm ==="
  for t in /proc/$p/task/*; do
    tid=${t##*/}
    tc=$(cat "$t/comm" 2>/dev/null)
    stack=$(cat "$t/stack" 2>/dev/null)
    case "$stack" in
      *binder_ioctl*|*futex*|*ppoll*|*poll*|*read*) ;;
      *) continue ;;
    esac
    echo "--- tid=$tid comm=$tc"
    echo "$stack"
  done
done
echo "=== done ==="
