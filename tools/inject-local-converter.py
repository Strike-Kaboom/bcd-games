#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Created 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""Inject Apple's local libmetalirconverter.dylib from an official BCD.ipa into our custom unsigned IPA.

Because Apple's Metal Shader Converter iOS dylib (libmetalirconverter.dylib) is never
committed to public git or uploaded in public GitHub Actions artifacts, our CI compiles
madeira-d3d12 against the Apache-2.0 vendored headers and ships a clean open-source IPA.
Before sideloading with Sideloadly, run this script locally on Windows/macOS/Linux to copy
Payload/Madeira.app/d3d12/libmetalirconverter.dylib from your own downloaded official BCD.ipa
into the custom unsigned IPA (Sideloadly re-signs all dylibs and app extensions on install).

Usage:
  python3 tools/inject-local-converter.py --ipa custom-unsigned.ipa --source official-BCD.ipa --out custom-ready.ipa
"""
import argparse
import struct
import sys
import zipfile

DYLIB_PATH = "Payload/Madeira.app/d3d12/libmetalirconverter.dylib"
REQUIRED_PLUGINS = (
    "Payload/Madeira.app/PlugIns/MadeiraJITHelper.appex/",
    "Payload/Madeira.app/PlugIns/MadeiraMemoryHost.appex/",
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ipa", required=True, help="Path to custom unsigned IPA downloaded from GitHub Actions")
    ap.add_argument("--source", required=True, help="Path to local official BCD.ipa containing libmetalirconverter.dylib")
    ap.add_argument("--out", required=True, help="Output path for Sideloadly-ready unsigned IPA")
    args = ap.parse_args()

    with zipfile.ZipFile(args.source, "r") as src:
        if DYLIB_PATH not in src.namelist():
            sys.exit(f"ERROR: {DYLIB_PATH} not found in source IPA {args.source}")
        dylib_bytes = src.read(DYLIB_PATH)

    if len(dylib_bytes) < 4096:
        sys.exit(f"ERROR: {DYLIB_PATH} looks truncated ({len(dylib_bytes)} bytes)")
    magic = struct.unpack_from("<I", dylib_bytes, 0)[0]
    if magic not in (0xFEEDFACF, 0xCAFEBABE, 0xBEBAFECA):
        sys.exit(f"ERROR: {DYLIB_PATH} is not a Mach-O binary (magic={magic:#x})")

    with zipfile.ZipFile(args.ipa, "r") as zin:
        names = zin.namelist()
        for plug in REQUIRED_PLUGINS:
            if not any(n.startswith(plug) for n in names):
                sys.exit(f"ERROR: custom IPA is missing required app extension {plug}")
        with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            for item in zin.infolist():
                if item.filename == DYLIB_PATH:
                    continue
                zout.writestr(item, zin.read(item.filename))
            info = zipfile.ZipInfo(DYLIB_PATH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100755 << 16
            zout.writestr(info, dylib_bytes)

    print(f"OK: wrote {args.out}")
    print(f"  + injected {DYLIB_PATH} ({len(dylib_bytes):,} bytes) from {args.source}")
    print("  + verified MadeiraJITHelper.appex and MadeiraMemoryHost.appex are intact")
    print("  -> Ready to install via Sideloadly over your existing BCD install (keep same bundle ID).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
