#!/usr/bin/env python3
"""patch_bms_syscap.py - обход проверки syscap в libbms.

Функции, логирующие "check syscap failed":
  0x357a40 и 0x3913d4 (libbms.z.so, VA; file offset = VA - 0x1000
  для .text этого файла — проверяется ассертами).
Соглашение: w0 = 0 -> OK (в call site 0x3568a4..0x3568ac: cbz w0 -> успех,
иначе cmp с 0x820022 и b.ne -> ошибка).

Патч: на входе каждой функции
    mov w0, #0        ; 0x52800000
    ret               ; 0xd65f03c0
(перезаписываются pacibsp и первая stp-инструкция; дальше не идём).
"""
import shutil
import struct

SRC = "/home/kharki/hp6/sys6/system/lib64/libbms.z.so"
DST = "/home/kharki/hsroot2/system/lib64/libbms.z.so"
BAK = DST + ".orig.syscap"

ENTRIES = [0x357A40, 0x3913D4]
MOV0 = struct.pack("<I", 0x52800000)
RET = struct.pack("<I", 0xD65F03C0)


def main():
    shutil.copyfile(DST, BAK)
    print("backup:", BAK)
    d = bytearray(open(SRC, "rb").read())
    for va in ENTRIES:
        off = va - 0x1000
        cur = bytes(d[off:off + 8])
        print("VA=%#x off=%#x old=%s" % (va, off, cur.hex()))
        if cur[:8] == (MOV0 + RET):
            print("  already patched")
            continue
        d[off:off + 8] = MOV0 + RET
    open(DST, "wb").write(bytes(d))
    print("written:", DST)


if __name__ == "__main__":
    main()
