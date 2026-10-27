#!/usr/bin/env python3
"""patch_hapverify.py - обход проверки подписи HAP.

libhapverify.z.so, символ OHOS::Security::Verify::HapVerify
(экспорт по адресу 0x4a094 — это b <реальная реализация 0x36148>).
Патчим вход реальной реализации: b <cave>, cave: mov w0,#0; ret
(0 = успех). HapVerifyResult (out-параметр) остаётся по умолчанию.
"""
import struct
import shutil

SRC = "/home/kharki/hp6/sys6/system/lib64/libhapverify.z.so"
DST = "/home/kharki/hsroot2/system/lib64/libhapverify.z.so"
BAK = DST + ".orig"

ENTRY_VA = 0x36148


def load_segments(d):
    phoff = struct.unpack_from("<Q", d, 0x20)[0]
    phes = struct.unpack_from("<H", d, 0x36)[0]
    phn = struct.unpack_from("<H", d, 0x38)[0]
    segs = []
    for i in range(phn):
        o = phoff + i * phes
        if struct.unpack_from("<I", d, o)[0] != 1:
            continue
        off = struct.unpack_from("<Q", d, o + 8)[0]
        va = struct.unpack_from("<Q", d, o + 0x10)[0]
        sz = struct.unpack_from("<Q", d, o + 0x20)[0]
        fl = struct.unpack_from("<I", d, o + 4)[0]
        segs.append((off, va, sz, fl))
    return segs


def va2off(segs, va):
    for off, va0, sz, fl in segs:
        if va0 <= va < va0 + sz:
            return off + (va - va0)
    raise SystemExit("va not mapped %#x" % va)


def off2va(segs, off):
    for o, va0, sz, fl in segs:
        if o <= off < o + sz:
            return va0 + (off - o)
    raise SystemExit("off not mapped %#x" % off)


def find_cave(d, segs, need):
    for off, va0, sz, fl in segs:
        if not (fl & 1):
            continue
        start = None
        for i in range(off, off + sz, 4):
            if d[i:i + 4] == b"\x00\x00\x00\x00":
                if start is None:
                    start = i
            else:
                if start is not None and i - start >= need:
                    return start
                start = None
        if start is not None and off + sz - start >= need:
            return start
    raise SystemExit("no cave")


def main():
    shutil.copyfile(DST, BAK)
    print("backup:", BAK)
    d = bytearray(open(SRC, "rb").read())
    segs = load_segments(d)
    off = va2off(segs, ENTRY_VA)
    print("entry VA=%#x off=%#x old=%s" % (ENTRY_VA, off, bytes(d[off:off + 4]).hex()))
    cave_off = find_cave(d, segs, 32)
    cave_va = off2va(segs, cave_off)
    cave = struct.pack("<II", 0x52800000, 0xD65F03C0)  # mov w0,#0 ; ret
    b = 0x14000000 | (((cave_va - ENTRY_VA) >> 2) & 0x3FFFFFF)
    print("cave off=%#x va=%#x" % (cave_off, cave_va))
    d[cave_off:cave_off + len(cave)] = cave
    d[off:off + 4] = struct.pack("<I", b)
    open(DST, "wb").write(bytes(d))
    print("written:", DST, "patch=b %#x" % cave_va)


if __name__ == "__main__":
    main()
