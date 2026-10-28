#!/system/bin/sh
# dumpstack5.sh - futex-диагностика: адрес futex, слово, владелец (tid) и его состояние
for d in /proc/[0-9]*; do
  comm=$(cat "$d/comm" 2>/dev/null)
  case "$comm" in
    foundation|sa_main|bms*|hdf_devmgr|msdp_sa|param_watcher|installs|samgr) ;;
    *) continue ;;
  esac
  p=${d#/proc/}
  echo "=== PID $p comm=$comm ==="
  for t in /proc/$p/task/*; do
    tid=${t##*/}
    tc=$(cat "$t/comm" 2>/dev/null)
    sc=$(cat "$t/syscall" 2>/dev/null)
    set -- $sc
    echo "--- tid=$tid comm=$tc syscall=$sc"
    if [ "$1" = "98" ] && [ -n "$2" ]; then
      addr=$2
      w=$(dd if="/proc/$p/mem" bs=1 "skip=$((addr))" count=4 2>/dev/null | od -An -tx4 2>/dev/null | tr -d ' ')
      echo "    futex_addr=$addr word=$w"
      if [ -n "$w" ]; then
        owner=$((0x$w & 0x3fffffff))
        echo "    owner_tid=$owner"
        oc=$(cat /proc/$p/task/$owner/comm 2>/dev/null)
        osc=$(cat /proc/$p/task/$owner/syscall 2>/dev/null)
        echo "    owner_comm=$oc owner_syscall=$osc"
        cat /proc/$p/task/$owner/stack 2>/dev/null
      fi
    fi
    cat "$t/stack" 2>/dev/null
  done
done
echo "=== done ==="
