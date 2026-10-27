#!/usr/bin/env python3
"""patch_installd_verify.py — принудительный успех VerifyCodeSignature.

Ошибка установки (чистый лог): 
  BMSInstalld: VerifyCode failed due to -769
  BMSInstalld: verify code signature failed: 8522362
  BMS: Install systemHsp ... result 8522362
Патчим серверные обработчики в libinstalls.z.so (.text: file = VA - 0x1000):
  InstalldHostImpl::VerifyCodeSignature        @0x91f14
  InstalldHostImpl::VerifyCodeSignatureForHap  @0x92ad8
на входе: mov w0,#0 (ERR_OK); ret.
"""
import shutil
import struct

LIB = "/home/kharki/hsroot2/system/lib64/libinstalls.z.so"
BAK = LIB + ".orig.verify"
ENTRIES = [0x91F14, 0x92AD8]
MOV0 = struct.pack("<I", 0x52800000)
RET = struct.pack("<I", 0xD65F03C0)


def main():
    shutil.copyfile(LIB, BAK)
    print("backup:", BAK)
    d = bytearray(open(LIB, "rb").read())
    for va in ENTRIES:
        off = va - 0x1000
        print("VA=%#x off=%#x old=%s" % (va, off, bytes(d[off:off + 8]).hex()))
        d[off:off + 8] = MOV0 + RET
    open(LIB, "wb").write(bytes(d))
    print("written:", LIB)


if __name__ == "__main__":
    main()
