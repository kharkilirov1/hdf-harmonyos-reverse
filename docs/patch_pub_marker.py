#!/usr/bin/env python3
"""patch_pub_marker.py - расширяем пещеру libsafwk: после Publish(401)
пишем байт в /data/diag/pub401 (детерминированный маркер для триггера bm)."""
import struct
import subprocess

SRC = "/home/kharki/hp6/sys6/system/lib64/platformsdk/libsystem_ability_fwk.z.so"
DST = "/home/kharki/hsroot2/system/lib64/platformsdk/libsystem_ability_fwk.z.so"

PATCH_VA = 0x1F1E0     # ldr w2,[x20,#8] (в хвосте AddSystemAbilityListener)
PUBLISH_VA = 0x1F324
ASM = "/tmp/pub_cave.s"
OBJ = "/tmp/pub_cave.o"
BIN = "/tmp/pub_cave.bin"


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
    raise SystemExit("va %#x" % va)


def off2va(segs, off):
    for o, va0, sz, fl in segs:
        if o <= off < o + sz:
            return va0 + (off - o)
    raise SystemExit("off %#x" % off)


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


ASM_TMPL = """.text
.global cave
cave:
    stp x0, x1, [sp, #-16]!
    stp x2, x3, [sp, #-16]!
    stp x4, x5, [sp, #-16]!
    stp x6, x7, [sp, #-16]!
    sub sp, sp, #16
    str x8, [sp]
    ldr w10, [x20, #8]
    mov w11, #401
    cmp w10, w11
    b.ne skipm
    mov w11, #8250
    cmp w19, w11
    b.ne skipm
    ldr x9, [x20, #0x178]
    cbz x9, skipm
    sub sp, sp, #16
    str x9, [sp]
    mov x1, sp
    mov x0, x20
    bl publish
    add sp, sp, #16
    /* debug: openat(-100,"/dev/console",O_WRONLY,0) + write("CAVEPUB") */
    mov x0, #-100
    adr x1, cpath
    mov x2, #1
    mov x3, #0
    mov x8, #56
    svc #0
    mov x10, x0
    cmp x10, #0
    b.lt nomark
    mov x0, x10
    adr x1, cmsg
    mov x2, #8
    mov x8, #64
    svc #0
    mov x0, x10
    mov x8, #57
    svc #0
nomark:
    /* маркер: openat(-100,"/data/diag/pub401",0x441,0644) */
    mov x0, #-100
    adr x1, mpath
    mov x2, #0x441
    mov x3, #0x1a4
    mov x8, #56
    svc #0
    mov x9, x0
    cmp x9, #0
    b.lt skipw
    mov x0, x9
    adr x1, mchar
    mov x2, #1
    mov x8, #64
    svc #0
    mov x0, x9
    mov x8, #57
    svc #0
skipw:
skipm:
    ldr x8, [sp]
    add sp, sp, #16
    ldp x6, x7, [sp], #16
    ldp x4, x5, [sp], #16
    ldp x2, x3, [sp], #16
    ldp x0, x1, [sp], #16
    .inst 0x{FRST:08x}
    .inst 0x14000000
mpath: .asciz "/data/diag/pub401"
cpath: .asciz "/dev/console"
cmsg: .ascii "CAVEPUB0"
mchar: .ascii "x"
.align 2
"""


def main():
    d = bytearray(open(SRC, "rb").read())
    segs = load_segments(d)
    poff = va2off(segs, PATCH_VA)
    first = struct.unpack_from("<I", d, poff)[0]
    cave_off = find_cave(d, segs, 512)
    cave_va = off2va(segs, cave_off)
    print("cave va=%#x first=%08x" % (cave_va, first))
    asm = ASM_TMPL.replace("{FRST:08x}", "%08x" % first)
    open(ASM, "w").write(asm)
    subprocess.run(["aarch64-linux-gnu-as", "-o", OBJ, ASM], check=True)
    subprocess.run(["aarch64-linux-gnu-objcopy", "-O", "binary", OBJ, BIN], check=True)
    blob = bytearray(open(BIN, "rb").read())
    # найти плейсхолдер b (нулевой) — он последний .inst 0x14000000 перед строками
    idx = blob.find(b"\x00\x00\x00\x14")
    if idx < 0:
        raise SystemExit("no placeholder")
    insn_va = cave_va + idx
    target = PATCH_VA + 4
    blob[idx:idx + 4] = struct.pack("<I", 0x14000000 | (((target - insn_va) >> 2) & 0x3FFFFFF))
    # поправить bl publish (ассемблер не знает внешний символ)
    bidx = blob.find(b"\x00\x00\x00\x94")
    if bidx < 0:
        raise SystemExit("no bl publish placeholder")
    bl_va = cave_va + bidx
    blob[bidx:bidx + 4] = struct.pack("<I", 0x94000000 | (((PUBLISH_VA - bl_va) >> 2) & 0x3FFFFFF))
    if any(b != 0 for b in d[cave_off:cave_off + len(blob)]):
        raise SystemExit("cave busy")
    d[cave_off:cave_off + len(blob)] = blob
    d[poff:poff + 4] = struct.pack("<I", 0x14000000 | (((cave_va - PATCH_VA) >> 2) & 0x3FFFFFF))
    open(DST, "wb").write(bytes(d))
    print("written", DST)


if __name__ == "__main__":
    main()
