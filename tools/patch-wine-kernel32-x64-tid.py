#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Modified 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""madeira-m5: x64 fast paths for kernel32's GetCurrentThreadId & GetCurrentProcessId.

Factorio calls kernel32!GetCurrentThreadId 67.8M times (~25.8% of all x64->EC exits).
Reading TEB->ClientId.UniqueThread (%gs:0x48) and UniqueProcess (%gs:0x40) directly in
x64 takes 2 instructions with zero emulator exit. Built on top of kernel32-usd's
KUSER_SHARED_DATA patch into kernel32-x64tid.dll.

Usage:
  patch-wine-kernel32-x64-tid.py WINE_SRC
  patch-wine-kernel32-x64-tid.py --verify DLL [STOCK]
"""
import os
import struct
import sys

SOURCE = "tid_x64.c"
EXPORTS = ("GetCurrentThreadId", "GetCurrentProcessId")

TID_X64_C = r'''/*
 * madeira-m5: x64 bodies for kernel32's GetCurrentThreadId and GetCurrentProcessId
 * (tools/patch-wine-kernel32-x64-tid.py; shipped as kernel32-x64tid.dll).
 */

#if 0
#pragma makedep arm64ec_x64
#endif

#ifdef __arm64ec_x64__

#include "wine/asm.h"

__ASM_GLOBAL_FUNC( "EXP+#KERNEL32_GetCurrentThreadId",
                   "movl %gs:0x48,%eax\n\t"
                   "ret" )

__ASM_GLOBAL_FUNC( "EXP+#KERNEL32_GetCurrentProcessId",
                   "movl %gs:0x40,%eax\n\t"
                   "ret" )

#endif  /* __arm64ec_x64__ */
'''


def patch(wine):
    k32 = os.path.join(wine, "dlls", "kernel32")
    mk = os.path.join(k32, "Makefile.in")
    src = os.path.join(k32, SOURCE)
    if not os.path.isfile(mk):
        sys.exit("patch-wine-kernel32-x64-tid: missing " + mk)
    with open(src, "w", encoding="utf-8") as f:
        f.write(TID_X64_C)
    text = open(mk, "r", encoding="utf-8").read()
    if f"\t{SOURCE} \\\n" in text or f"\t{SOURCE}\n" in text:
        print("patch-wine-kernel32-x64-tid: already patched")
        return 0
    lines = text.split("\n")
    try:
        start = lines.index("SOURCES = \\")
    except ValueError:
        sys.exit("patch-wine-kernel32-x64-tid: SOURCES anchor not found in " + mk)
    end = start + 1
    while end < len(lines) and lines[end].endswith("\\"):
        end += 1
    if end >= len(lines) or not lines[end].startswith("\t"):
        sys.exit("patch-wine-kernel32-x64-tid: SOURCES list not understood in " + mk)
    lines[end] = lines[end] + " \\"
    lines.insert(end + 1, "\t" + SOURCE)
    open(mk, "w", encoding="utf-8").write("\n".join(lines))
    print("patch-wine-kernel32-x64-tid: patched " + mk + " (+" + SOURCE + ")")
    return 0


def verify(path, stock=None):
    # Reuse verifier helpers from patch-wine-kernelbase-x64-tls.py
    import importlib.util
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch-wine-kernelbase-x64-tls.py")
    spec = importlib.util.spec_from_file_location("kbtls", helper)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    d, machine, secs, r2o, exps, ranges, redirs = mod.parse_pe(path)
    bad = []
    if machine != 0x8664 or not any(k == 1 for _, _, k in ranges):
        bad.append("not an ARM64EC image")
    expected = {
        "GetCurrentThreadId": bytes.fromhex("658b042548000000c3"),
        "GetCurrentProcessId": bytes.fromhex("658b042540000000c3"),
    }
    for name, want in expected.items():
        rva = exps.get(name)
        if rva is None:
            bad.append(f"{name}: not exported")
            continue
        kind = [k for s, l, k in ranges if s <= rva < s + l]
        if kind != [2]:
            bad.append(f"{name}: rva {rva:#x} not in X64 code range ({kind})")
        if rva not in redirs:
            bad.append(f"{name}: missing CHPE RedirectionMetadata entry for {rva:#x}")
        got = d[r2o(rva):r2o(rva) + len(want)]
        if got != want:
            bad.append(f"{name}: body {got.hex()} != {want.hex()}")
        for off in range(0, 16, 4):
            w = struct.unpack_from("<I", d, r2o(rva + off))[0]
            if mod.x18_role(w):
                bad.append(f"{name}+0x{off:x}: word {w:08x} triggers ARM64 x18 patcher")
    if stock:
        _, _, _, _, ref, _, _ = mod.parse_pe(stock)
        missing = sorted(set(ref) - set(exps))
        extra = sorted(set(exps) - set(ref))
        if missing or extra:
            bad.append(f"exports differ from {stock}: missing={missing[:8]} extra={extra[:8]}")
    if bad:
        sys.exit("verify %s:\n  %s" % (path, "\n  ".join(bad)))
    print(f"verify {path}: GetCurrentThreadId & GetCurrentProcessId are x64 bodies with CHPE redirects and no x18 collisions")
    return 0


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--verify":
        sys.exit(verify(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None))
    elif len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        sys.exit(patch(sys.argv[1]))
    else:
        sys.exit(__doc__)
