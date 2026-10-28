#!/usr/bin/env python3
"""patch_defer_start.py - пещера в libsafwk: Publish + ОТЛОЖЕННЫЙ Start в новом
потоке (pthread_create -> tramp: usleep(2s) -> Start(self)).

Идея: если Start вызывать синхронно внутри пути Init/AddSystemAbilityListener,
возникает реентерабельный дедлок (Init ждёт лок, который держит тот же поток).
Откладывание в отдельный поток разрывает эту реентерабельность.
"""
import struct
import subprocess

SRC = "/home/kharki/hp6/sys6/system/lib64/platformsdk/libsystem_ability_fwk.z.so"
DST = "/home/kharki/hsroot2/system/lib64/platformsdk/libsystem_ability_fwk.z.so"

PATCH_VA = 0x1F1E0
RET_VA = 0x1F1E8
PUBLISH_VA = 0x1F324
START_VA = 0x1FF38
ASM = "/mnt/c/Users/Kharki/Desktop/hdf_contract/cave_defer.s"
OBJ = "/tmp/cave_defer.o"
BIN = "/tmp/cave_defer.bin"


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


def plt_va(d, segs, name):
    """Ищем .plt-запись по строке имени в .dynstr через relocation-таблицу."""
    # простой способ: найти в .plt адрес через objdump
    out = subprocess.run(["aarch64-linux-gnu-objdump", "-d", "-j", ".plt", SRC],
                         capture_output=True, text=True).stdout
    import re as _re
    for line in out.splitlines():
        m = _re.match(r"\s*([0-9a-f]+) <" + _re.escape(name) + r"@plt>:", line)
        if m:
            return int(m.group(1), 16)
    raise SystemExit("plt not found: " + name)


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


def build_cave(cave_va, targets):
    subprocess.run(["aarch64-linux-gnu-as", "-o", OBJ, ASM], check=True)
    subprocess.run(["aarch64-linux-gnu-objcopy", "-O", "binary", OBJ, BIN], check=True)
    code = open(BIN, "rb").read()
    words = list(struct.unpack("<%dI" % (len(code) // 4), code))
    bl_idx = [i for i, w in enumerate(words) if w == 0x94000000]
    b_idx = [i for i, w in enumerate(words) if w == 0x14000000]
    if len(bl_idx) != len(targets):
        raise SystemExit("bl placeholders: %d expect %d" % (len(bl_idx), len(targets)))
    if len(b_idx) != 1:
        raise SystemExit("expect exactly 1 b placeholder, got %d" % len(b_idx))

    def enc_bl(insn_va, target_va):
        return 0x94000000 | (((target_va - insn_va) >> 2) & 0x3FFFFFF)

    for idx, tgt in zip(bl_idx, targets):
        words[idx] = enc_bl(cave_va + idx * 4, tgt)
    words[b_idx[0]] = 0x14000000 | (((RET_VA - (cave_va + b_idx[0] * 4)) >> 2) & 0x3FFFFFF)
    return struct.pack("<%dI" % len(words), *words)


def main():
    d = bytearray(open(SRC, "rb").read())
    segs = load_segments(d)
    patch_off = va2off(segs, PATCH_VA)
    print("patch VA=%#x off=%#x old=%s" % (PATCH_VA, patch_off, d[patch_off:patch_off + 4].hex()))
    cave_off = find_cave(d, segs, 160)
    cave_va = off2va(segs, cave_off)
    print("cave off=%#x va=%#x" % (cave_off, cave_va))
    pc_plt = plt_va(d, segs, "pthread_create")
    us_plt = plt_va(d, segs, "usleep")
    print("pthread_create@plt=%#x usleep@plt=%#x" % (pc_plt, us_plt))
    targets = [PUBLISH_VA, pc_plt, us_plt, START_VA]
    cave = build_cave(cave_va, targets)
    print("cave bytes (%d)" % len(cave))
    if any(b != 0 for b in d[cave_off:cave_off + len(cave)]):
        raise SystemExit("cave area not free")
    d[cave_off:cave_off + len(cave)] = cave
    b_insn = 0x14000000 | (((cave_va - PATCH_VA) >> 2) & 0x3FFFFFF)
    d[patch_off:patch_off + 4] = struct.pack("<I", b_insn)
    open(DST, "wb").write(bytes(d))
    print("written:", DST)


if __name__ == "__main__":
    main()
