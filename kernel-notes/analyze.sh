#!/bin/bash
K="/mnt/c/Users/Kharki/Desktop/harmony_kernel_re/vmlinux-7.0.0-B1"
echo "=== sections (sorted by size) ==="
readelf -S "$K" | sed -n '5,120p' | awk '{printf "%-22s %-12s %-10s %-16s %s\n", $2, $3, $4, $6, $7}' | sort -k4 -nr | head -40
echo
echo "=== symbol tables ==="
readelf -S "$K" | grep -E 'symtab|strtab|BTF|kallsyms' || echo "no symtab/BTF sections found"
echo
echo "=== nm symbol count ==="
nm "$K" 2>&1 | head -3
nm "$K" 2>/dev/null | wc -l
echo
echo "=== interesting strings ==="
for pat in hkip HKIP huawei verity dm-verity ohos OHOS hdf HDF secureboot "secure boot" tee TEE iommu; do
  c=$(strings -a "$K" | grep -c -F "$pat")
  echo "$pat : $c"
done
echo
echo "=== sample huawei/ohos strings ==="
strings -a "$K" | grep -E 'hkip|hisi|kirin|huawei|ohos' | sort -u | head -40
