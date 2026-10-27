#!/usr/bin/env python3
"""patch_sa_main.py - не даём «foundation» завершиться.

sa_main после LocalAbilityManager::DoStartSAProcess вызывает
ReportSaMainExit и завершается (exit 0); init перезапускает сервис,
и процесс, в котором жили SA (включая BMS/SA 401), умирает.
Патч: bl ReportSaMainExit -> b . (бесконечный цикл), процесс остаётся
жить, SA-объекты и их binder-узлы сохраняются.

Смещения: 0x2898 и 0x2eb8 (VA). Для этого ELF offset == VA
(проверяется assert'ом по байтам).
"""
import struct

SRC = "/home/kharki/hp6/sys6/system/bin/sa_main"
DST = "/home/kharki/hsroot2/system/bin/sa_main"

# bl ReportSaMainExit = 0x94000a22 (VA 0x2898), 0x9400089a (VA 0x2eb8)
PATCHES = [
    (0x2898, bytes.fromhex("220a0094"), bytes.fromhex("00000014")),  # b .
    (0x2EB8, bytes.fromhex("9a080094"), bytes.fromhex("00000014")),  # b .
]


def main():
    d = bytearray(open(SRC, "rb").read())
    for va, old, new in PATCHES:
        off = va
        cur = bytes(d[off:off + 4])
        print("VA=%#x off=%#x cur=%s expect=%s" % (va, off, cur.hex(), old.hex()))
        if cur == new:
            print("  already patched")
            continue
        assert cur == old, "unexpected bytes at %#x" % va
        d[off:off + 4] = new
    open(DST, "wb").write(bytes(d))
    print("written:", DST)


if __name__ == "__main__":
    main()
