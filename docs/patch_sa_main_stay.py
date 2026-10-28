#!/usr/bin/env python3
"""patch_sa_main_stay.py - не даём main() в /system/bin/sa_main вернуться.

Идея: thunk main (0x5074: "b 0x2220") подменяем на ветвь в пещеру:
    cave:
        stp x29, x30, [sp, #-16]!
        bl  0x2220        ; настоящий main(argc, argv)
        b   .             ; бесконечный цикл — процесс никогда не выходит
Это сохраняет все потоки, SA 401 не умирает.
"""
import struct
import sys

SRC = "/home/kharki/hp6/sys6/system/bin/sa_main"
DST = "/home/kharki/hsroot2/system/bin/sa_main"

THUNK_VA = 0x5074   # main -> b 0x2220
BODY_VA = 0x2220    # настоящий main


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
    raise SystemExit("va not mapped: %#x" % va)


def off2va(segs, off):
    for o, va0, sz, fl in segs:
        if o <= off < o + sz:
            return va0 + (off - o)
    raise SystemExit("off not mapped: %#x" % off)


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


def enc_b(va, target):
    return 0x14000000 | (((target - va) >> 2) & 0x3FFFFFF)


def enc_bl(va, target):
    return 0x94000000 | (((target - va) >> 2) & 0x3FFFFFF)


def main():
    d = bytearray(open(SRC, "rb").read())
    segs = load_segments(d)
    toff = va2off(segs, THUNK_VA)
    print("thunk old:", d[toff:toff + 4].hex())
    off = find_cave(d, segs, 24)
    cave_va = off2va(segs, off)
    print("cave va=%#x off=%#x" % (cave_va, off))
    code = [
        0xA9BF7BFD,                      # stp x29, x30, [sp, #-16]!
        enc_bl(cave_va + 4, BODY_VA),    # bl main_body
        0x14000000,                      # b . (заполним ниже)
    ]
    # b . : target == own address
    code[2] = enc_b(cave_va + 8, cave_va + 8)
    blob = struct.pack("<3I", *code)
    if any(b != 0 for b in d[off:off + len(blob)]):
        raise SystemExit("cave not free")
    d[off:off + len(blob)] = blob
    d[toff:toff + 4] = struct.pack("<I", enc_b(THUNK_VA, cave_va))
    open(DST, "wb").write(bytes(d))
    print("written:", DST, "thunk -> ", hex(enc_b(THUNK_VA, cave_va)))


if __name__ == "__main__":
    main()
