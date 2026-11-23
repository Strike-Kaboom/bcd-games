#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Modified 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""madeira-m5: x64 fast paths in Wine's ARM64EC kernelbase.dll (kernelbase-x64tls.dll).

Dark Souls III calls kernelbase!TlsGetValue ~316,000 times/second during active
gameplay (13.4% of all x64->EC emulator exits), and many 64-bit games hammer
TlsGetValue / TlsSetValue / GetLastError / GetCurrentThreadId / GetCurrentProcessId.
Each call is a few TEB loads/stores, yet crossing the ARM64EC boundary costs dozens
of instructions and a pipeline barrier.

Using the same `#pragma makedep arm64ec_x64` / `EXP+#<export>` pattern as BCD's
ucrtbase-x64math.dll and ntdll-sync.dll, this patch provides pure-x64 bodies for:
  - TlsGetValue          (slots 0..63 & expansion slots 64..1087; out-of-range -> #TlsGetValue)
  - TlsSetValue          (slots 0..63; expansion slots -> #TlsSetValue)
  - GetLastError         (%gs:0x68)
  - GetCurrentThreadId   (%gs:0x48)
  - GetCurrentProcessId  (%gs:0x40)

ARM64EC callers are redirected to the native ARM64EC bodies via CHPE RedirectionMetadata
(with our forwarded-export redirect fix in ntdll-sync.dll).

Usage:
  patch-wine-kernelbase-x64-tls.py WINE_SRC          patch dlls/kernelbase (idempotent)
  patch-wine-kernelbase-x64-tls.py --verify DLL [STOCK]
"""
import os
import struct
import sys

SOURCE = "tls_x64.c"
EC_SOURCE = "tls_ec.c"
EXPORTS = (
    "TlsGetValue",
    "TlsSetValue",
    "GetLastError",
    "GetCurrentThreadId",
    "GetCurrentProcessId",
)

TLS_EC_C = r'''/*
 * madeira-m5: ARM64EC counterpart symbols for kernelbase's GetLastError,
 * GetCurrentThreadId, and GetCurrentProcessId so lld-link emits CHPE
 * RedirectionMetadata pairing EXP+#<Name> -> #<Name>.
 */
#ifdef __arm64ec__
extern unsigned int __cdecl kernelbase_GetLastError(void);
extern unsigned int __cdecl kernelbase_GetCurrentThreadId(void);
extern unsigned int __cdecl kernelbase_GetCurrentProcessId(void);
unsigned int __cdecl GetLastError(void);
unsigned int __cdecl GetCurrentThreadId(void);
unsigned int __cdecl GetCurrentProcessId(void);
unsigned int __cdecl GetLastError(void) { return kernelbase_GetLastError(); }
unsigned int __cdecl GetCurrentThreadId(void) { return kernelbase_GetCurrentThreadId(); }
unsigned int __cdecl GetCurrentProcessId(void) { return kernelbase_GetCurrentProcessId(); }
#endif
'''

TLS_X64_C = r'''/*
 * madeira-m5: x64 bodies for kernelbase's TlsGetValue, TlsSetValue,
 * GetLastError, GetCurrentThreadId, and GetCurrentProcessId
 * (tools/patch-wine-kernelbase-x64-tls.py; shipped as kernelbase-x64tls.dll).
 *
 * TEB64 offsets (verified against Wine arm64ec kernelbase.dll):
 *   %gs:0x40   ClientId.UniqueProcess (DWORD)
 *   %gs:0x48   ClientId.UniqueThread  (DWORD)
 *   %gs:0x68   LastErrorValue         (DWORD)
 *   %gs:0x1480 TlsSlots[64]           (void *)
 *   %gs:0x1780 TlsExpansionSlots      (void **)
 */

#if 0
#pragma makedep arm64ec_x64
#endif

#ifdef __arm64ec_x64__

#include "wine/asm.h"

__ASM_GLOBAL_FUNC( "EXP+#TlsGetValue",
                   "movl %ecx,%ecx\n\t"
                   "movl $0,%gs:0x68\n\t"
                   "cmpl $64,%ecx\n\t"
                   "jae 1f\n\t"
                   "movq %gs:0x1480(,%rcx,8),%rax\n\t"
                   "ret\n"
                   "1:\tcmpl $1088,%ecx\n\t"
                   "jae 9f\n\t"
                   "movq %gs:0x1780,%rax\n\t"
                   "testq %rax,%rax\n\t"
                   "jz 2f\n\t"
                   "movq -512(%rax,%rcx,8),%rax\n"
                   "2:\tret\n"
                   "9:\tjmp \"#TlsGetValue\"" )

__ASM_GLOBAL_FUNC( "EXP+#TlsSetValue",
                   "movl %ecx,%ecx\n\t"
                   "cmpl $64,%ecx\n\t"
                   "jae 9f\n\t"
                   "movq %rdx,%gs:0x1480(,%rcx,8)\n\t"
                   "movl $1,%eax\n\t"
                   "ret\n"
                   "9:\tjmp \"#TlsSetValue\"" )

__ASM_GLOBAL_FUNC( "EXP+#GetLastError",
                   "movl %gs:0x68,%eax\n\t"
                   "ret" )

__ASM_GLOBAL_FUNC( "EXP+#GetCurrentThreadId",
                   "movl %gs:0x48,%eax\n\t"
                   "ret" )

__ASM_GLOBAL_FUNC( "EXP+#GetCurrentProcessId",
                   "movl %gs:0x40,%eax\n\t"
                   "ret" )

#endif  /* __arm64ec_x64__ */
'''


def patch(wine):
    kb = os.path.join(wine, "dlls", "kernelbase")
    mk = os.path.join(kb, "Makefile.in")
    src = os.path.join(kb, SOURCE)
    ec_src = os.path.join(kb, EC_SOURCE)
    if not os.path.isfile(mk):
        sys.exit("patch-wine-kernelbase-x64-tls: missing " + mk)
    with open(src, "w", encoding="utf-8") as f:
        f.write(TLS_X64_C)
    with open(ec_src, "w", encoding="utf-8") as f:
        f.write(TLS_EC_C)
    text = open(mk, "r", encoding="utf-8").read()
    added = []
    for sname in (SOURCE, EC_SOURCE):
        if f"\t{sname} \\\n" in text or f"\t{sname}\n" in text:
            continue
        lines = text.split("\n")
        try:
            start = lines.index("SOURCES = \\")
        except ValueError:
            sys.exit("patch-wine-kernelbase-x64-tls: SOURCES anchor not found in " + mk)
        end = start + 1
        while end < len(lines) and lines[end].endswith("\\"):
            end += 1
        if end >= len(lines) or not lines[end].startswith("\t"):
            sys.exit("patch-wine-kernelbase-x64-tls: SOURCES list not understood in " + mk)
        lines[end] = lines[end] + " \\"
        lines.insert(end + 1, "\t" + sname)
        text = "\n".join(lines)
        added.append(sname)
    if not added:
        print("patch-wine-kernelbase-x64-tls: already patched")
        return 0
    open(mk, "w", encoding="utf-8").write(text)
    print("patch-wine-kernelbase-x64-tls: patched " + mk + " (+" + ",+".join(added) + ")")
    return 0


def x18_role(insn):
    rn, rm, rt2 = (insn >> 5) & 0x1f, (insn >> 16) & 0x1f, (insn >> 10) & 0x1f
    if 18 not in (rn, rm, rt2):
        return 0
    top8, top11 = insn >> 24, insn >> 21
    if (top8 & 0x3F) in (0x39, 0x3D) and rn == 18:
        return 1
    if (top11 & 0x1F9) == 0x1C1 and ((insn >> 10) & 3) == 2:
        if rn == 18:
            return 1
        if rm == 18:
            return 2
    if (top11 & 0x3E7) == 0x1C0 and rn == 18:
        return 1
    if (top8 & 0x3E) in (0x28, 0x2C):
        if rn == 18:
            return 1
        if rt2 == 18:
            return 3
    if (top11 & 0x7FF) in (0x150, 0x550) and rm == 18:
        return 2
    if (top8 & 0x1F) == 0x11 and rn == 18:
        return 1
    if (top8 & 0x1F) == 0x0B:
        if rn == 18:
            return 1
        if rm == 18:
            return 2
    return 0


def parse_pe(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    machine, nsec = struct.unpack_from("<HH", d, pe + 4)
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    image_base = struct.unpack_from("<Q", d, opt + 24)[0]
    ddir = opt + 112
    exp_rva = struct.unpack_from("<I", d, ddir)[0]
    cfg_rva, cfg_size = struct.unpack_from("<II", d, ddir + 10 * 8)
    secs = []
    for i in range(nsec):
        s = opt + optsz + 40 * i
        vsz, va, rsz, raw = struct.unpack_from("<IIII", d, s + 8)
        ch = struct.unpack_from("<I", d, s + 36)[0]
        secs.append((va, max(vsz, rsz), raw, vsz, ch))

    def r2o(rva):
        for va, sz, raw, _, _ in secs:
            if va <= rva < va + sz:
                return rva - va + raw
        raise ValueError(f"rva {rva:#x} outside sections")

    e = r2o(exp_rva)
    nfun, nnames, afun, anames, aords = struct.unpack_from("<IIIII", d, e + 20)
    exps = {}
    for i in range(nnames):
        no = r2o(struct.unpack_from("<I", d, r2o(anames) + 4 * i)[0])
        name = d[no:d.index(b"\0", no)].decode("latin-1")
        o = struct.unpack_from("<H", d, r2o(aords) + 2 * i)[0]
        exps[name] = struct.unpack_from("<I", d, r2o(afun) + 4 * o)[0]

    chpe = struct.unpack_from("<Q", d, r2o(cfg_rva) + 0xC8)[0] - image_base
    m = r2o(chpe)
    cm_rva, cm_n = struct.unpack_from("<II", d, m + 4)
    rm_rva, rm_n = struct.unpack_from("<II", d, m + 16), struct.unpack_from("<I", d, m + 52)[0]
    rm_rva = struct.unpack_from("<I", d, m + 16)[0]
    ranges = []
    for i in range(cm_n):
        start, length = struct.unpack_from("<II", d, r2o(cm_rva) + 8 * i)
        ranges.append((start & ~3, length, start & 3))
    redirs = {}
    for i in range(rm_n):
        src_rva, dst_rva = struct.unpack_from("<II", d, r2o(rm_rva) + 8 * i)
        redirs[src_rva] = dst_rva
    return d, machine, secs, r2o, exps, ranges, redirs


def verify(path, stock=None):
    d, machine, secs, r2o, exps, ranges, redirs = parse_pe(path)
    bad = []
    if machine != 0x8664 or not any(k == 1 for _, _, k in ranges):
        bad.append("not an ARM64EC image")
    ffs = bytes.fromhex("488bc448895820555de9")
    for name in EXPORTS:
        rva = exps.get(name)
        if rva is None:
            bad.append(f"{name}: not exported")
            continue
        kind = [k for s, l, k in ranges if s <= rva < s + l]
        if kind != [2]:
            bad.append(f"{name}: rva {rva:#x} not in X64 code range ({kind})")
        if rva not in redirs:
            bad.append(f"{name}: missing CHPE RedirectionMetadata entry for {rva:#x}")
        raw = d[r2o(rva):r2o(rva) + 64]
        if raw[:10] == ffs:
            bad.append(f"{name}: still a fast-forward sequence")
        # Scan up to next 16-byte padded boundary after ret/jmp
        scan_len = 80 if name == "TlsGetValue" else (32 if name == "TlsSetValue" else 16)
        for off in range(0, scan_len, 4):
            w = struct.unpack_from("<I", d, r2o(rva + off))[0]
            if x18_role(w):
                bad.append(f"{name}+0x{off:x}: word {w:08x} triggers ARM64 x18 patcher")
    if stock:
        _, _, _, _, ref, _, _ = parse_pe(stock)
        missing = sorted(set(ref) - set(exps))
        extra = sorted(set(exps) - set(ref))
        if missing or extra:
            bad.append(f"exports differ from {stock}: missing={missing[:8]} extra={extra[:8]}")
    if bad:
        sys.exit("verify %s:\n  %s" % (path, "\n  ".join(bad)))
    print(f"verify {path}: {', '.join(EXPORTS)} are x64 bodies in X64 ranges with CHPE redirects and no x18 collisions")
    return 0


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--verify":
        sys.exit(verify(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None))
    elif len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        sys.exit(patch(sys.argv[1]))
    else:
        sys.exit(__doc__)
