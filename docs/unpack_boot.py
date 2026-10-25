#!/usr/bin/env python3
"""Минимальный распаковщик Android boot image (v0/v1/v2) + extract-ikconfig.

Использование:
    python3 unpack_boot.py boot.img outdir
"""
import os, struct, sys, gzip, lzma, zlib, bz2

def parse_header(d):
    magic = d[:8]
    if magic != b"ANDROID!":
        raise SystemExit("не Android boot image: %r" % magic)
    (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr,
     second_size, second_addr, tags_addr, page_size,
     hdr_version, os_version) = struct.unpack_from("<10I", d, 8)
    name = d[48:64].rstrip(b"\x00").decode("latin1")
    cmdline = d[64:64 + 512].rstrip(b"\x00").decode("latin1")
    hdr = {"kernel_size": kernel_size, "ramdisk_size": ramdisk_size,
           "second_size": second_size, "page_size": page_size,
           "hdr_version": hdr_version, "name": name, "cmdline": cmdline,
           "kernel_addr": kernel_addr}
    return hdr

def decompress_kernel(blob):
    for name, fn in (("gzip", lambda b: gzip.decompress(b)),
                     ("xz", lambda b: lzma.decompress(b)),
                     ("bzip2", lambda b: bz2.decompress(b)),
                     ("lz4", None),
                     ("lzma", lambda b: lzma.decompress(b))):
        try:
            if fn is None:
                continue
            return name, fn(blob)
        except Exception:
            continue
    # zImage? попробуем найти gzip-поток
    for magic, name in ((b"\x1f\x8b\x08", "gzip"), (b"\xfd7zXZ", "xz"), (b"BZh", "bzip2")):
        i = blob.find(magic)
        if i >= 0:
            try:
                if name == "gzip":
                    return name, gzip.decompress(blob[i:])
                if name == "xz":
                    return name, lzma.decompress(blob[i:])
                if name == "bzip2":
                    return name, bz2.decompress(blob[i:])
            except Exception:
                pass
    return None, blob

def ikconfig(img):
    i = img.find(b"IKCFG_ST")
    if i < 0:
        return None
    for off in range(8, 64):
        try:
            cfg = gzip.decompress(img[i + off:])
            if b"CONFIG_" in cfg:
                return cfg.decode("utf-8", "replace")
        except Exception:
            continue
    return None

def main():
    boot, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    d = open(boot, "rb").read()
    h = parse_header(d)
    ps = h["page_size"]
    print("header:", h)

    base = ps
    kernel = d[base:base + h["kernel_size"]]
    base += (h["kernel_size"] + ps - 1) // ps * ps
    ramdisk = d[base:base + h["ramdisk_size"]]
    base += (h["ramdisk_size"] + ps - 1) // ps * ps
    second = d[base:base + h["second_size"]] if h["second_size"] else b""

    open(os.path.join(out, "kernel_raw"), "wb").write(kernel)
    open(os.path.join(out, "ramdisk"), "wb").write(ramdisk)
    if second:
        open(os.path.join(out, "second"), "wb").write(second)

    kind, img = decompress_kernel(kernel)
    print("kernel compression:", kind, "-> size", len(img),
          "magic", img[:4].hex())
    open(os.path.join(out, "Image"), "wb").write(img)

    cfg = ikconfig(img)
    if cfg:
        open(os.path.join(out, "kernel.config"), "w").write(cfg)
        print("IKCONFIG: ok,", len(cfg.splitlines()), "строк")
    else:
        print("IKCONFIG: не найден (нет CONFIG_IKCONFIG_PROC или сжатие иное)")

    v = img.find(b"Linux version")
    if v >= 0:
        print("banner:", img[v:v + 180].split(b"\x00")[0].decode("latin1"))

if __name__ == "__main__":
    main()
