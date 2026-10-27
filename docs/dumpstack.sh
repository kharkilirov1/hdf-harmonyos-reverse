#!/system/bin/sh
# dumpstack.sh - снять состояние потоков foundation (ищущих BMS OnStart)
for p in $(pidof foundation) $(pidof sa_main); do
  echo "=== PID $p ==="
  for t in /proc/$p/task/*; do
    tid=$(basename "$t")
    st=$(cat "$t/stat" 2>/dev/null | awk '{print $3}')
    wc=$(cat "$t/wchan" 2>/dev/null)
    sc=$(cat "$t/syscall" 2>/dev/null)
    echo "--- tid=$tid state=$st wchan=$wc syscall=$sc"
    cat "$t/stack" 2>/dev/null
  done
done
echo "=== done ==="
