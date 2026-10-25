import gzip, zlib, lzma, bz2, struct, sys

d = open("/home/kharki/mi9/out/kernel_raw", "rb").read()
print("payload:", len(d), "magic:", d[:16])

# ARM64 Image начинается с 0x14 у этого вендор-контейнера
img = d[0x14:]
t_off, img_size, flags = struct.unpack_from("<QQQ", img, 8)
print(f"Image: file={len(img)} text_offset=0x{t_off:x} image_size=0x{img_size:x} flags=0x{flags:x}")
print("ARMd magic:", img[0x38:0x3c])
open("/home/kharki/mi9/out/Image.arm64", "wb").write(img)
print("written Image.arm64")

# ---- extract-ikconfig ----
def try_decompress(buf, off):
    for name, fn in (("gzip", lambda b: gzip.decompress(b)),
                     ("zlib", lambda b: zlib.decompress(b, 15)),
                     ("xz", lambda b: lzma.decompress(b)),
                     ("bzip2", lambda b: bz2.decompress(b))):
        try:
            return name, fn(buf[off:])
        except Exception:
            continue
    return None, None

found = False
for marker in (b"IKCFG_ST",):
    start = 0
    while True:
        j = d.find(marker, start)
        if j < 0:
            break
        for off in range(8, 96):
            name, cfg = try_decompress(d[j:], off)
            if cfg and len(cfg) > 2000 and b"CONFIG_" in cfg:
                print(f"IKCONFIG: {name} at IKCFG_ST+{off}, {len(cfg.splitlines())} строк")
                open("/home/kharki/mi9/out/kernel.config", "wb").write(cfg)
                found = True
                break
        if found:
            break
        start = j + 1
    if found:
        break

if not found:
    print("IKCONFIG: не найден ни gzip/zlib/xz/bzip2 после IKCFG_ST")

# ---- баннер ----
i = d.find(b"Linux version")
if i >= 0:
    print("banner:", d[i:i + 220].split(b"\x00")[0].decode("latin1"))
