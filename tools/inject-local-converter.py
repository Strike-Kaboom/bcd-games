#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Created 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""Prepare a local unsigned BCD-M5 IPA for Sideloadly.

1. Copies Apple's local Metal Shader Converter dylib
   (Payload/Madeira.app/d3d12/libmetalirconverter.dylib) from your own downloaded
   official BCD.ipa into the clean open-source unsigned IPA built by GitHub Actions.
2. Optionally sets a personal Home Screen display name (--display-name) and/or
   Home Screen app icon PNG (--icon) strictly locally without changing the bundle
   identifier (CFBundleIdentifier) or either app extension, so Sideloadly updates
   over an existing install in place without wiping games or settings.

Usage:
  python3 tools/inject-local-converter.py \\
    --ipa custom-unsigned.ipa --source official-BCD.ipa --out custom-ready.ipa \\
    [--display-name "MyName"] [--icon my-icon-1024.png]
"""
import argparse
import io
import plistlib
import struct
import sys
import zipfile

APP_PREFIX = "Payload/Madeira.app/"
INFO_PLIST_PATH = APP_PREFIX + "Info.plist"
DYLIB_PATH = APP_PREFIX + "d3d12/libmetalirconverter.dylib"
REQUIRED_PLUGINS = (
    APP_PREFIX + "PlugIns/MadeiraJITHelper.appex/",
    APP_PREFIX + "PlugIns/MadeiraMemoryHost.appex/",
)
ICON_TARGETS = (
    ("AppIcon60x60@2x.png", 120),
    ("AppIcon60x60@3x.png", 180),
    ("AppIcon76x76@2x~ipad.png", 152),
    ("AppIcon83.5x83.5@2x~ipad.png", 167),
    ("AppIcon1024x1024.png", 1024),
)
ICON_BASES = ["AppIcon60x60", "AppIcon76x76", "AppIcon83.5x83.5", "AppIcon1024x1024"]


def render_icons(icon_path: str) -> dict[str, bytes]:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("ERROR: --icon requires Pillow (pip install pillow)")
    img = Image.open(icon_path)
    if img.mode != "RGB":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
            rgba = img.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[3])
            img = bg
        else:
            img = img.convert("RGB")
    out = {}
    for fname, px in ICON_TARGETS:
        resized = img.resize((px, px), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="PNG", optimize=True)
        out[APP_PREFIX + fname] = buf.getvalue()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ipa", required=True, help="Path to custom unsigned IPA downloaded from GitHub Actions")
    ap.add_argument("--source", required=True, help="Path to local official BCD.ipa containing libmetalirconverter.dylib")
    ap.add_argument("--out", required=True, help="Output path for Sideloadly-ready unsigned IPA")
    ap.add_argument("--display-name", default=None, help="Optional local Home Screen app name (CFBundleDisplayName)")
    ap.add_argument("--icon", default=None, help="Optional local square PNG/ICO for Home Screen app icon")
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

    icon_blobs = render_icons(args.icon) if args.icon else {}
    replaced_paths = {DYLIB_PATH} | set(icon_blobs.keys())
    if args.display_name or args.icon:
        replaced_paths.add(INFO_PLIST_PATH)

    with zipfile.ZipFile(args.ipa, "r") as zin:
        names = zin.namelist()
        for plug in REQUIRED_PLUGINS:
            if not any(n.startswith(plug) for n in names):
                sys.exit(f"ERROR: custom IPA is missing required app extension {plug}")
        if INFO_PLIST_PATH not in names:
            sys.exit(f"ERROR: {INFO_PLIST_PATH} missing from custom IPA")

        plist_bytes = None
        bundle_id = None
        if args.display_name or args.icon:
            info = plistlib.loads(zin.read(INFO_PLIST_PATH))
            bundle_id = info.get("CFBundleIdentifier")
            if args.display_name:
                info["CFBundleDisplayName"] = args.display_name
                info["CFBundleName"] = args.display_name
            if args.icon:
                # Removing CFBundleIconName makes iOS/iPadOS SpringBoard load the bundle PNGs
                # listed in CFBundleIconFiles instead of the compiled AppIcon inside Assets.car,
                # while keeping Assets.car untouched for all other in-app images.
                info["CFBundleIcons"] = {"CFBundlePrimaryIcon": {"CFBundleIconFiles": ICON_BASES}}
                info["CFBundleIcons~ipad"] = {"CFBundlePrimaryIcon": {"CFBundleIconFiles": ICON_BASES}}
            plist_bytes = plistlib.dumps(info, fmt=plistlib.FMT_BINARY, sort_keys=False)

        with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            for item in zin.infolist():
                if item.filename in replaced_paths:
                    continue
                zout.writestr(item, zin.read(item.filename))

            # Write libmetalirconverter.dylib
            zinfo = zipfile.ZipInfo(DYLIB_PATH)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.external_attr = 0o100755 << 16
            zout.writestr(zinfo, dylib_bytes)

            # Write updated Info.plist if customized
            if plist_bytes is not None:
                pinfo = zipfile.ZipInfo(INFO_PLIST_PATH)
                pinfo.compress_type = zipfile.ZIP_DEFLATED
                pinfo.external_attr = 0o100644 << 16
                zout.writestr(pinfo, plist_bytes)

            # Write custom Home Screen PNG icons if requested
            for rel, data in icon_blobs.items():
                iinfo = zipfile.ZipInfo(rel)
                iinfo.compress_type = zipfile.ZIP_DEFLATED
                iinfo.external_attr = 0o100644 << 16
                zout.writestr(iinfo, data)

    print(f"OK: wrote {args.out}")
    print(f"  + injected {DYLIB_PATH} ({len(dylib_bytes):,} bytes) from {args.source}")
    if args.display_name:
        print(f"  + display name set to {args.display_name!r} (CFBundleIdentifier kept as {bundle_id!r})")
    if icon_blobs:
        print(f"  + wrote {len(icon_blobs)} opaque iOS/iPadOS Home Screen PNG icons (CFBundleIconName cleared so SpringBoard uses PNGs)")
    print("  + verified MadeiraJITHelper.appex and MadeiraMemoryHost.appex are intact")
    print("  -> Ready to install via Sideloadly over your existing BCD install (keep same bundle ID).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
