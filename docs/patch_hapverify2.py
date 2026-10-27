#!/usr/bin/env python3
"""patch_hapverify2.py - точечный обход проверки подписи HAP.

В libhapverify.z.so, HapVerify (реализация 0x36148):
   36188: tbnz ...            ; проверка глобального флага
   3618c: bl 35aec            ; CheckXxx -> w0
   36190: tbz w0, #0, 3624c   ; если w0==0 -> fail (-14)
Патч: 0x36190 -> nop, т.е. продолжаем при любом результате этой
ранней проверки. Остальная цепочка (CheckFilePath, RandomAccessFile,
ParseAndVerify) остаётся рабочей, поэтому HapVerifyResult должен
заполняться нормально.
"""
import struct
import shutil

SRC = "/home/kharki/hp6/sys6/system/lib64/libhapverify.z.so"
DST = "/home/kharki/hsroot2/system/lib64/libhapverify.z.so"
BAK = DST + ".orig"

VA = 0x36190
OLD = bytes.fromhex("e0050036")   # tbz w0,#0,0x3624c
NEW = bytes.fromhex("1f2003d5")   # nop


def main():
    shutil.copyfile(DST, BAK)
    print("backup:", BAK)
    d = bytearray(open(SRC, "rb").read())
    off = VA - 0x1000  # .text: file offset = VA - 0x1000
    cur = bytes(d[off:off + 4])
    print("VA=%#x off=%#x old=%s" % (VA, off, cur.hex()))
    assert cur == OLD, "unexpected bytes: %s" % cur.hex()
    d[off:off + 4] = NEW
    open(DST, "wb").write(bytes(d))
    print("written:", DST, "new=", NEW.hex())


if __name__ == "__main__":
    main()
