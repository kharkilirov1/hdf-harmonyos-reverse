#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kallsyms_parse.py -- recover the kallsyms symbol table from a stripped Linux
vmlinux (ELF64) that has no .symtab / .BTF, only the compressed kallsyms
arrays in .rodata.

Target: vmlinux-7.0.0-B1  (Linux 5.10.210, x86_64, Huawei clang 15)
  CONFIG_KALLSYMS=y
  CONFIG_KALLSYMS_ALL=y
  CONFIG_KALLSYMS_BASE_RELATIVE=y
  CONFIG_KALLSYMS_ABSOLUTE_PERCPU=y

Layout that is searched for (may differ slightly per build, so every step is
signature-verified and there are fallbacks):

    kallsyms_offsets        u32[N]      (N = number of symbols)
    kallsyms_relative_base  u64         (link-time base address, e.g. _text)
    kallsyms_num_syms       u32         (== N)
    kallsyms_names          byte[N]     (length-prefixed token sequences)
    kallsyms_markers        u32[M]      (M = ceil(N/256), names offset / 256)
    kallsyms_token_table    256 x NUL-terminated ASCII strings
    kallsyms_token_index    u16[256]    (offsets of the strings in the table)

Decoding of an address (kernel/kallsyms.c, BASE_RELATIVE + ABSOLUTE_PERCPU):

    off = (s32)offsets[i]
    if off >= 0:  addr = off                       # absolute (percpu) symbol
    else:         addr = relative_base - 1 - off   # normal kernel symbol

Standard library only (Python 3.8+).
"""

import os
import re
import struct
import sys

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

DEFAULT_TARGET = "vmlinux-7.0.0-B1"

CONTROL_NAMES = [
    "start_kernel",
    "kallsyms_lookup_name",
    "do_exit",
    "schedule",
    "__x64_sys_read",
    "init_task",
    "panic",
]

VENDOR_RE = re.compile(r"huawei|hisi|kirin|hkip|ohos|hdf|hmos", re.I)

# symbol type letters that kallsyms stores as the first character of a name
KSYM_TYPES = set("TtWwDdBbRrAaVvNnUuIiMmZz?")

MAX_SYMBOLS = 2_000_000
MIN_SYMBOLS = 20_000

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def u16(d, o):
    return d[o] | (d[o + 1] << 8)


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def u64(d, o):
    return struct.unpack_from("<Q", d, o)[0]


def s32(v):
    return v - (1 << 32) if v >= (1 << 31) else v


def parse_elf_sections(data):
    """Minimal ELF64 little-endian section parser (no external deps)."""
    if data[:4] != b"\x7fELF":
        raise SystemExit("not an ELF file")
    if data[4] != 2:
        raise SystemExit("only ELF64 is supported")

    e_shoff = u64(data, 0x28)
    e_shentsize = u16(data, 0x3A)
    e_shnum = u16(data, 0x3C)
    e_shstrndx = u16(data, 0x3E)
    if e_shoff == 0 or e_shnum == 0:
        raise SystemExit("no section headers")
    if e_shentsize < 64:
        raise SystemExit("unexpected section header size")

    sections = []
    for i in range(e_shnum):
        b = e_shoff + i * e_shentsize
        if b + 64 > len(data):
            break
        (sh_name, sh_type, sh_flags, sh_addr,
         sh_offset, sh_size) = struct.unpack_from("<IIQQQQ", data, b)
        sections.append({
            "index": i,
            "name_off": sh_name,
            "type": sh_type,
            "flags": sh_flags,
            "addr": sh_addr,
            "off": sh_offset,
            "size": sh_size,
            "name": "",
        })

    if 0 <= e_shstrndx < len(sections):
        st = sections[e_shstrndx]
        base, end = st["off"], min(st["off"] + st["size"], len(data))
        for s in sections:
            n = base + s["name_off"]
            if n >= end:
                continue
            e = data.find(b"\x00", n, end)
            if e < 0:
                e = end
            s["name"] = data[n:e].decode("latin1", "replace")
    return sections


# --------------------------------------------------------------------------
# step 1: find kallsyms_token_table / kallsyms_token_index
# --------------------------------------------------------------------------


def _validate_token_table(data, p, idx):
    """Given a candidate token_index offset p, try to locate the token table
    start t.  Returns (t, tokens, table_len) or None."""
    base = idx[255]
    if base < 200 or base > 0x2000:          # 256 tokens, total size sanity
        return None

    # token 0 starts at t, so its terminating NUL sits at t + idx[1] - 1.
    # Therefore t = z + 1 - idx[1] for a NUL byte z right before p.
    lo = max(0, p - base - 512)
    zeros = []
    z = data.rfind(b"\x00", lo, p)
    while z >= 0 and len(zeros) < 400:
        zeros.append(z)
        z = data.rfind(b"\x00", lo, z)

    for z in zeros:
        t = z + 1 - idx[1]
        if t < 0:
            continue
        ok = True
        for i in range(255):
            s = t + idx[i]
            ln = idx[i + 1] - idx[i] - 1
            if ln <= 0 or s + ln >= p:
                ok = False
                break
            chunk = data[s:s + ln]
            if 0 in chunk or any(b < 0x20 or b > 0x7E for b in chunk):
                ok = False
                break
            if data[s + ln] != 0:
                ok = False
                break
        if not ok:
            continue
        # last token: printable run terminated by NUL, then zero padding to p
        s = t + idx[255]
        e = data.find(b"\x00", s, p)
        if e < 0 or e == s:
            continue
        tail = data[s:e]
        if any(b < 0x20 or b > 0x7E for b in tail):
            continue
        if data[e + 1:p].count(0) != len(data[e + 1:p]):
            continue
        tokens = []
        for i in range(256):
            s = t + idx[i]
            L = (idx[i + 1] - idx[i] - 1) if i < 255 else (e - s)
            tokens.append(data[s:s + L])
        return t, tokens, p - t
    return None


def find_token_table(data, regions):
    """Search for the (token_table, token_index) pair.

    Signature: 256 NUL-terminated printable strings immediately followed by
    256 u16 offsets, where idx[0] == 0 and idx[i+1]-idx[i] == len(token[i])+1.
    """
    pat = re.compile(rb"\x00\x00[\x01-\x7f]\x00[\x01-\x7f]\x00")
    for (lo, hi) in regions:
        hi = min(hi, len(data))
        if hi - lo < 1024:
            continue
        for m in pat.finditer(data, lo, hi):
            p = m.start()
            if p & 1:
                continue
            idx = struct.unpack_from("<256H", data, p)
            if idx[0] != 0:
                continue
            bad = False
            for i in range(255):
                d = idx[i + 1] - idx[i]
                if d < 1 or d > 64:
                    bad = True
                    break
            if bad:
                continue
            got = _validate_token_table(data, p, idx)
            if got:
                t, tokens, table_len = got
                return {
                    "token_table": t,
                    "token_index": p,
                    "tokens": tokens,
                    "table_len": table_len,
                    "index_len": 512,
                }
    return None


# --------------------------------------------------------------------------
# step 2: markers (u32 array right before the token table)
# --------------------------------------------------------------------------


def find_markers(data, table_off):
    vals = []
    q = table_off
    while q - 4 >= 0 and len(vals) < 8192:
        v = u32(data, q - 4)
        if v > 0x10000000:
            break
        if vals and v >= vals[-1]:
            break
        vals.append(v)
        q -= 4
        if v == 0 and len(vals) > 2:
            break
    vals.reverse()
    if len(vals) < 3 or vals[0] != 0:
        return None
    if any(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)):
        return None
    return {"markers": q, "count": len(vals), "values": vals}


# --------------------------------------------------------------------------
# step 3: names blob (walk the length-prefixed token stream)
# --------------------------------------------------------------------------


def walk_names(data, start, end, limit=MAX_SYMBOLS):
    """Walk records; return record count if the walk ends exactly at `end`."""
    pos = start
    n = 0
    while pos < end:
        if n > limit:
            return None
        b0 = data[pos]
        if b0 & 0x80:                       # 6.1+ extended length encoding
            if pos + 1 >= end:
                return None
            ln = (b0 & 0x7F) | (data[pos + 1] << 7)
            pos += 2
        else:
            ln = b0
            pos += 1
        if ln == 0:
            return None
        pos += ln
        n += 1
    return n if pos == end else None


def find_names(data, names_end, search_span=8 << 20):
    """Locate kallsyms_names + num_syms + relative_base.

    Anchor: the u64 at names_start-16 is the link-time base address and the
    u32 at names_start-8 is the symbol count (verified by walking the blob).
    """
    lo = max(0, names_end - search_span)
    lo = (lo + 7) & ~7
    for S in range(lo, names_end - 8, 8):
        rb = u64(data, S - 16)
        if not (0xFFFF_FFFF_8000_0000 <= rb <= 0xFFFF_FFFF_9000_0000):
            continue
        n = u32(data, S - 8)
        if not (MIN_SYMBOLS <= n <= MAX_SYMBOLS):
            continue
        cnt = walk_names(data, S, names_end)
        if cnt != n:
            continue
        return {"names": S, "num_syms": n, "relative_base": rb,
                "num_syms_off": S - 8, "relative_base_off": S - 16}
    # fallback: relax the relative_base test to "any plausible kernel pointer"
    for S in range(lo, names_end - 8, 8):
        rb = u64(data, S - 16)
        if not (0xFFFF_8000_0000_0000 <= rb <= 0xFFFF_FFFF_FFFF_FFFF):
            continue
        n = u32(data, S - 8)
        if not (MIN_SYMBOLS <= n <= MAX_SYMBOLS):
            continue
        if walk_names(data, S, names_end) == n:
            return {"names": S, "num_syms": n, "relative_base": rb,
                    "num_syms_off": S - 8, "relative_base_off": S - 16,
                    "relative_base_guess": True}
    return None


# --------------------------------------------------------------------------
# step 4: addresses
# --------------------------------------------------------------------------


def decode_addresses(offsets, relative_base):
    """Try all plausible interpretations, keep the one that validates."""
    mask = (1 << 64) - 1
    n = len(offsets)
    variants = {}

    variants["base_relative_percpu"] = [
        (v if s32(v) >= 0 else (relative_base - 1 - s32(v)) & mask)
        for v in offsets
    ]
    variants["base_relative"] = [(relative_base + v) & mask for v in offsets]
    variants["absolute_u32"] = [v for v in offsets]
    variants["absolute_s32"] = [s32(v) & mask for v in offsets]

    best = None
    for name, addrs in variants.items():
        mono = sum(1 for i in range(n - 1) if addrs[i + 1] >= addrs[i])
        sane = sum(1 for a in addrs
                   if 0xFFFF_FFFF_8000_0000 <= a <= 0xFFFF_FFFF_9000_0000
                   or a < 0x0100_0000)
        score = (mono / max(1, n - 1)) + (sane / max(1, n))
        if best is None or score > best[0]:
            best = (score, name, addrs, mono, sane)
    return {"scheme": best[1], "addrs": best[2], "mono": best[3],
            "sane": best[4]}


# --------------------------------------------------------------------------
# step 5: main recovery
# --------------------------------------------------------------------------


def recover(data):
    sections = parse_elf_sections(data)
    regions = []
    ro = [s for s in sections if s["name"] == ".rodata" and s["size"] > 0]
    for s in ro:
        regions.append((s["off"], s["off"] + s["size"]))
    # always allow a full-file fallback
    regions.append((0, len(data)))

    info = {"sections": sections}
    tt = find_token_table(data, regions)
    if not tt:
        raise SystemExit("kallsyms_token_table signature not found")
    info.update(tt)

    mk = find_markers(data, tt["token_table"])
    if not mk:
        raise SystemExit("kallsyms_markers not found before token table")
    info.update(mk)

    # names end right before the markers array, modulo 8-byte label padding
    names_end = mk["markers"]
    pad = 0
    while pad < 8 and names_end - 1 > 0 and data[names_end - 1] == 0:
        names_end -= 1
        pad += 1
    info["names_end"] = mk["markers"] - pad
    info["names_pad"] = pad

    nm = find_names(data, info["names_end"])
    if not nm:
        raise SystemExit("kallsyms_names / num_syms / relative_base not found")
    info.update(nm)

    n = nm["num_syms"]
    off_start = nm["relative_base_off"] - 4 * n
    if off_start < 0:
        raise SystemExit("kallsyms_offsets would start before the file")
    info["offsets"] = off_start
    info["offsets_end"] = nm["relative_base_off"]

    offsets = list(struct.unpack_from("<%dI" % n, data, off_start))
    dec = decode_addresses(offsets, nm["relative_base"])
    info.update(dec)

    # ---- decode names -----------------------------------------------------
    tokens = tt["tokens"]
    names = []
    pos = nm["names"]
    for _ in range(n):
        b0 = data[pos]
        if b0 & 0x80:
            ln = (b0 & 0x7F) | (data[pos + 1] << 7)
            pos += 2
        else:
            ln = b0
            pos += 1
        raw = data[pos:pos + ln]
        pos += ln
        names.append(b"".join(tokens[b] for b in raw))
    info["names_consumed"] = pos
    return info, names


def split_type(raw_name):
    """kallsyms stores the symbol type as the first character of the name."""
    if raw_name and chr(raw_name[0]) in KSYM_TYPES and len(raw_name) > 1:
        return chr(raw_name[0]), raw_name[1:].decode("latin1")
    return "?", raw_name.decode("latin1")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, DEFAULT_TARGET)
    if not os.path.isfile(target):
        raise SystemExit("input file not found: %s" % target)

    data = open(target, "rb").read()
    print("input      : %s (%d bytes)" % (target, len(data)))

    info, names = recover(data)
    n = len(names)
    addrs = info["addrs"]

    print("token_table: file offset 0x%x (%d bytes, 256 tokens)"
          % (info["token_table"], info["table_len"]))
    print("token_index: file offset 0x%x" % info["token_index"])
    print("markers    : file offset 0x%x (%d entries)"
          % (info["markers"], info["count"]))
    print("names      : file offset 0x%x .. 0x%x"
          % (info["names"], info["names_end"]))
    print("num_syms   : %d (u32 at 0x%x)" % (n, info["num_syms_off"]))
    print("rel. base  : 0x%016x (u64 at 0x%x)"
          % (info["relative_base"], info["relative_base_off"]))
    print("offsets    : file offset 0x%x .. 0x%x (u32[%d])"
          % (info["offsets"], info["offsets_end"], n))
    print("addr scheme: %s (monotone %d/%d, in-range %d/%d)"
          % (info["scheme"], info["mono"], n - 1, info["sane"], n))

    # ---- build name -> address lookup -------------------------------------
    by_name = {}
    for raw, a in zip(names, addrs):
        typ, nm = split_type(raw)
        by_name.setdefault(nm, a)

    # ---- validation -------------------------------------------------------
    print("\n--- validation ---")
    ok = True
    if n > 50_000:
        print("[ok]   symbol count %d > 50000" % n)
    else:
        print("[FAIL] symbol count %d <= 50000" % n)
        ok = False

    found = 0
    for want in CONTROL_NAMES:
        if want in by_name:
            a = by_name[want]
            good = (0xFFFF_FFFF_8100_0000 <= a <= 0xFFFF_FFFF_8400_0000
                    or a < 0x0100_0000)
            print("[%s] %-22s = 0x%016x" % ("ok" if good else "warn", want, a))
            found += 1
        else:
            print("[FAIL] control symbol missing: %s" % want)
            ok = False if want in ("start_kernel", "kallsyms_lookup_name") else ok

    code = [a for raw, a in zip(names, addrs)
            if 0xFFFF_FFFF_8100_0000 <= a <= 0xFFFF_FFFF_8300_0000]
    print("[ok]   %d symbols (%.1f%%) inside 0xffffffff81000000..0xffffffff83000000"
          % (len(code), 100.0 * len(code) / max(1, n)))
    if info["mono"] != n - 1:
        print("[warn] address array is not fully sorted (%d/%d)"
              % (info["mono"], n - 1))

    # ---- write outputs ----------------------------------------------------
    tsv_path = os.path.join(here, "symbols.tsv")
    txt_path = os.path.join(here, "symbols.txt")
    with open(tsv_path, "w", encoding="utf-8", newline="\n") as f:
        for raw, a in zip(names, addrs):
            typ, nm = split_type(raw)
            f.write("0x%016x\t%s\t%s\n" % (a, typ, nm))
    with open(txt_path, "w", encoding="utf-8", newline="\n") as f:
        for raw in names:
            f.write(split_type(raw)[1] + "\n")
    print("\nwrote %s (%d lines)" % (tsv_path, n))
    print("wrote %s (%d lines)" % (txt_path, n))

    # ---- statistics -------------------------------------------------------
    plain = [split_type(r)[1] for r in names]
    uniq = set(plain)
    vendors = sorted({nm for nm in plain if VENDOR_RE.search(nm)})
    print("\n--- statistics ---")
    print("total symbols    : %d" % n)
    print("unique names     : %d" % len(uniq))
    print("vendor-ish names : %d (huawei|hisi|kirin|hkip|ohos|hdf|hmos)"
          % len(vendors))
    for v in vendors:
        print("    %-45s 0x%016x" % (v, by_name.get(v, 0)))

    print("\nRESULT: %s (%d symbols, %d/%d control names)"
          % ("OK" if ok else "CHECK FAILED", n, found, len(CONTROL_NAMES)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
