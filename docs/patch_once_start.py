#!/usr/bin/env python3
"""patch_libsafwk.py - code-cave инъекция публикации SA 401 в libsafwk.

Цель: libsystem_ability_fwk.z.so (C++ SAFWK).
BMS (SA 401) вызывает SystemAbility::AddSystemAbilityListener(int) во время
OnStart. В хвосте этой функции (VA 0x1f15c..0x1f200) подменяем инструкцию
0x1f1e0 (`ldr w2,[x20,#8]`) на `b cave`.

Пещера (cave) в свободном padding .text:
  if ([x20+8] == 401) {
      x0 = x20;  x0 = GetAbilityRemoteObject(x20);   // 0x213c0
      Publish(x20, &sptr_on_stack);                  // 0x1f324
  }
  ldr w2,[x20,#8]; mov w1,w19; b 0x1f1e8   // оригинальный хвост 0x1f1e8

Регистры: x20 = SystemAbility* (self), w19 = listener id.
Смещения Publish/GetAbilityRemoteObject — те же .so, прямые bl.
"""
import struct
import subprocess

SRC = "/home/kharki/hp6/sys6/system/lib64/platformsdk/libsystem_ability_fwk.z.so"
DST = "/home/kharki/hsroot2/system/lib64/platformsdk/libsystem_ability_fwk.z.so"

PATCH_VA = 0x1F1E0
RET_VA = 0x1F1E8
GETTER_VA = 0x213C0
PUBLISH_VA = 0x1F324
START_VA = 0x1FF38
ASM = "/mnt/c/Users/Kharki/Desktop/hdf_contract/cave_start.s"
OBJ = "/tmp/cave_safwk.o"
BIN = "/tmp/cave_safwk.bin"


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
    raise SystemExit("no code cave found")


def build_cave(cave_va):
    subprocess.run(["aarch64-linux-gnu-as", "-o", OBJ, ASM], check=True)
    subprocess.run(["aarch64-linux-gnu-objcopy", "-O", "binary", OBJ, BIN], check=True)
    code = open(BIN, "rb").read()
    words = list(struct.unpack("<%dI" % (len(code) // 4), code))
    bl_idx = [i for i, w in enumerate(words) if w == 0x94000000]
    b_idx = [i for i, w in enumerate(words) if w == 0x14000000]
    assert len(bl_idx) in (1, 2, 3), "bl placeholders: %d" % len(bl_idx)
    assert len(b_idx) == 1, "expect 1 b placeholder, got %d" % len(b_idx)

    def enc(insn_va, target_va):
        return (0x94000000 if insn_va != cave_va else 0)  # unused

    def enc_bl(insn_va, target_va):
        return 0x94000000 | (((target_va - insn_va) >> 2) & 0x3FFFFFF)

    def enc_b(insn_va, target_va):
        return 0x14000000 | (((target_va - insn_va) >> 2) & 0x3FFFFFF)

    if len(bl_idx) == 3:
        words[bl_idx[0]] = enc_bl(cave_va + bl_idx[0] * 4, START_VA)
        words[bl_idx[1]] = enc_bl(cave_va + bl_idx[1] * 4, PUBLISH_VA)
        words[bl_idx[2]] = enc_bl(cave_va + bl_idx[2] * 4, PUBLISH_VA)
    elif len(bl_idx) == 2:
        words[bl_idx[0]] = enc_bl(cave_va + bl_idx[0] * 4, START_VA)
        words[bl_idx[1]] = enc_bl(cave_va + bl_idx[1] * 4, PUBLISH_VA)
    else:
        words[bl_idx[0]] = enc_bl(cave_va + bl_idx[0] * 4, PUBLISH_VA)
    words[b_idx[0]] = enc_b(cave_va + b_idx[0] * 4, RET_VA)
    return struct.pack("<%dI" % len(words), *words)


def main():
    d = bytearray(open(SRC, "rb").read())
    segs = load_segments(d)
    patch_off = va2off(segs, PATCH_VA)
    old = bytes(d[patch_off:patch_off + 4])
    print("file:", DST)
    print("patch VA=%#x -> off=%#x old bytes=%s" % (PATCH_VA, patch_off, old.hex()))
    cave_off = find_cave(d, segs, 96)
    cave_va = off2va(segs, cave_off)
    print("cave off=%#x va=%#x" % (cave_off, cave_va))
    cave = build_cave(cave_va)
    print("cave bytes (%d): %s" % (len(cave), cave.hex()))
    if any(b != 0 for b in d[cave_off:cave_off + len(cave)]):
        raise SystemExit("cave area not free")
    b_insn = 0x14000000 | (((cave_va - PATCH_VA) >> 2) & 0x3FFFFFF)
    print("patch: %s -> b %#x (%s)" % (old.hex(), cave_va, struct.pack("<I", b_insn).hex()))
    d[cave_off:cave_off + len(cave)] = cave
    d[patch_off:patch_off + 4] = struct.pack("<I", b_insn)
    open(DST, "wb").write(bytes(d))
    print("written:", DST)


if __name__ == "__main__":
    main()
