#!/usr/bin/env python3
"""patch_libbms_markers.py - маркеры в /dev/kmsg на входе функций libbms.

Для каждой цели: в padding .text кладём пещеру:
  save x0..x8 -> openat("/dev/kmsg") -> write(marker) -> close
  -> restore -> (исходные первые N инструкций) -> b func+N*4
На входе функции ставим b cave.
"""
import struct
import subprocess

SRC = "/home/kharki/hsroot2/system/lib64/libbms.z.so"
DST = "/home/kharki/hsroot2/system/lib64/libbms.z.so"
ASM = "/tmp/bms_cave.s"
OBJ = "/tmp/bms_cave.o"
BIN = "/tmp/bms_cave.bin"

# (VA функции, сколько инструкций вытесняем, текст маркера)
TARGETS = [
    (0x2A920C, 3, "BMK OnStart\\n"),        # BundleMgrService::OnStart
    (0x2AC040, 3, "BMK Init\\n"),           # BundleMgrService::Init
    (0x2B4464, 3, "BMK OnBmsStarting\\n"),  # BMSEventHandler::OnBmsStarting
]


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


def build(cave_va, func_va, nmove, marker, orig_words):
    asm = ".text\n"
    asm += "cave_%x:\n" % func_va
    asm += "\tstp x0, x1, [sp, #-16]!\n"
    asm += "\tstp x2, x3, [sp, #-16]!\n"
    asm += "\tstp x4, x5, [sp, #-16]!\n"
    asm += "\tstp x6, x7, [sp, #-16]!\n"
    asm += "\tsub sp, sp, #16\n\tstr x8, [sp]\n"
    asm += "\tmov x0, #-100\n"
    asm += "\tadr x1, path_%x\n" % func_va
    asm += "\tmov x2, #1\n\tmov x3, #0\n\tmov x8, #56\n\tsvc #0\n"
    asm += "\tmov x9, x0\n"
    asm += "\tmov x0, x9\n"
    asm += "\tadr x1, msg_%x\n" % func_va
    asm += "\tmov x2, #%d\n" % len(marker)
    asm += "\tmov x8, #64\n\tsvc #0\n"
    asm += "\tmov x0, x9\n\tmov x8, #57\n\tsvc #0\n"
    asm += "\tldr x8, [sp]\n\tadd sp, sp, #16\n"
    asm += "\tldp x6, x7, [sp], #16\n"
    asm += "\tldp x4, x5, [sp], #16\n"
    asm += "\tldp x2, x3, [sp], #16\n"
    asm += "\tldp x0, x1, [sp], #16\n"
    for w in orig_words:
        asm += "\t.inst 0x%08x\n" % w
    asm += "\t.inst 0x14000000\n"   # placeholder b (fix later)
    asm += "path_%x: .asciz \"/dev/kmsg\"\n" % func_va
    asm += "msg_%x: .ascii \"%s\"\n" % (func_va, marker)
    asm += ".align 2\n"
    open(ASM, "w").write(asm)
    subprocess.run(["aarch64-linux-gnu-as", "-o", OBJ, ASM], check=True)
    subprocess.run(["aarch64-linux-gnu-objcopy", "-O", "binary", OBJ, BIN], check=True)
    blob = bytearray(open(BIN, "rb").read())
    # найти placeholder b (0x14000000) и заменить на b func+nmove*4
    off = blob.find(b"\x00\x00\x00\x14")
    if off < 0:
        raise SystemExit("placeholder b not found")
    insn_va = cave_va + off
    target = func_va + nmove * 4
    insn = 0x14000000 | (((target - insn_va) >> 2) & 0x3FFFFFF)
    blob[off:off + 4] = struct.pack("<I", insn)
    return bytes(blob)


def main():
    d = bytearray(open(SRC, "rb").read())
    segs = load_segments(d)
    cave_off = find_cave(d, segs, 1024)
    cave_va = off2va(segs, cave_off)
    print("cave va=%#x" % cave_va)
    cur = cave_off
    cur_va = cave_va
    for func_va, nmove, marker in TARGETS:
        foff = va2off(segs, func_va)
        orig_words = list(struct.unpack("<%dI" % nmove, bytes(d[foff:foff + nmove * 4])))
        blob = build(cur_va, func_va, nmove, marker, orig_words)
        print("func %#x: cave %#x len %d" % (func_va, cur_va, len(blob)))
        if any(b != 0 for b in d[cur:cur + len(blob)]):
            raise SystemExit("cave not free at %#x" % cur_va)
        d[cur:cur + len(blob)] = blob
        b_insn = 0x14000000 | (((cur_va - func_va) >> 2) & 0x3FFFFFF)
        d[foff:foff + 4] = struct.pack("<I", b_insn)
        cur += (len(blob) + 15) & ~15
        cur_va = off2va(segs, cur)
    open(DST, "wb").write(bytes(d))
    print("written", DST)


if __name__ == "__main__":
    main()
