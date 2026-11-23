#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
# Modified 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
#
# Build M5 x64 fast-path ARM64EC Wine DLLs using the existing wine/build-arm64ec tree:
#   1. kernelbase-x64tls.dll  (TlsGetValue, TlsSetValue, GetLastError, GetCurrentThreadId/ProcessId in x64)
#   2. kernel32-x64tid.dll    (KUSER_SHARED_DATA direct GetTickCount + GetCurrentThreadId/ProcessId in x64)
# Runs after tools/build-wine-extra-dlls.sh and leaves the wine submodule clean.
set -eu
R="$(pwd)"
MINGW="${MINGW:-$R/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin}"
export PATH="$MINGW:$PATH"
B="$R/wine/build-arm64ec"
SHIP="$R/app/Madeira/arm64ec-windows"
JOBS="$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

if [ ! -f "$B/Makefile" ]; then
    echo "::warning::build-wine-m5-dlls: $B/Makefile missing; skipping kernelbase-x64tls & kernel32-x64tid"
    exit 0
fi

pad_pe() {
    python3 - "$1" <<'PY'
import struct, sys
p = sys.argv[1]; d = open(p, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
target = struct.unpack_from('<I', d, pe + 24 + 56)[0] + 0x10000
if len(d) < target:
    open(p, 'ab').write(b'\0' * (target - len(d)))
PY
}

# 1. kernelbase-x64tls.dll
if [ -f "$R/wine/dlls/kernelbase/Makefile.in" ] && [ -f "$SHIP/kernelbase.dll" ]; then
    kb="$B/dlls/kernelbase/arm64ec-windows/kernelbase.dll"
    if python3 "$R/tools/patch-wine-kernelbase-x64-tls.py" "$R/wine"; then
        rm -f "$kb" "$B"/dlls/kernelbase/arm64ec-windows/*.o
        make -C "$B" -j"$JOBS" dlls/kernelbase/arm64ec-windows/kernelbase.dll > "$B.kernelbase-x64tls.log" 2>&1 || true
        if [ -f "$kb" ] && cp "$kb" "$SHIP/kernelbase-x64tls.dll.tmp" &&
           "$MINGW/arm64ec-w64-mingw32-strip" --strip-debug "$SHIP/kernelbase-x64tls.dll.tmp" &&
           pad_pe "$SHIP/kernelbase-x64tls.dll.tmp" &&
           python3 "$R/tools/patch-wine-kernelbase-x64-tls.py" --verify "$SHIP/kernelbase-x64tls.dll.tmp" "$SHIP/kernelbase.dll"; then
            mv "$SHIP/kernelbase-x64tls.dll.tmp" "$SHIP/kernelbase-x64tls.dll"
            echo "::notice::kernelbase-x64tls.dll built and verified"
        else
            rm -f "$SHIP/kernelbase-x64tls.dll.tmp"
            echo "::warning::kernelbase-x64tls.dll failed to build or verify"
            tail -n 30 "$B.kernelbase-x64tls.log" || true
        fi
    fi
    git -C "$R/wine" checkout -- dlls/kernelbase/Makefile.in
    touch "$R/wine/dlls/kernelbase/Makefile.in"
    rm -f "$R/wine/dlls/kernelbase/tls_x64.c" "$R/wine/dlls/kernelbase/tls_ec.c" "$kb" "$B"/dlls/kernelbase/arm64ec-windows/*.o
fi

# 2. kernel32-x64tid.dll (usd-direct + GetCurrentThreadId/ProcessId in x64)
if [ -f "$R/wine/dlls/kernel32/Makefile.in" ] && [ -f "$SHIP/kernel32.dll" ]; then
    k32="$B/dlls/kernel32/arm64ec-windows/kernel32.dll"
    if python3 "$R/tools/patch-wine-kernel32-usd-direct.py" "$R/wine/dlls/kernel32/sync.c" &&
       python3 "$R/tools/patch-wine-kernel32-x64-tid.py" "$R/wine"; then
        rm -f "$k32" "$B"/dlls/kernel32/arm64ec-windows/*.o
        make -C "$B" -j"$JOBS" dlls/kernel32/arm64ec-windows/kernel32.dll > "$B.kernel32-x64tid.log" 2>&1 || true
        if [ -f "$k32" ] && cp "$k32" "$SHIP/kernel32-x64tid.dll.tmp" &&
           "$MINGW/arm64ec-w64-mingw32-strip" --strip-debug "$SHIP/kernel32-x64tid.dll.tmp" &&
           pad_pe "$SHIP/kernel32-x64tid.dll.tmp" &&
           python3 "$R/tools/patch-wine-kernel32-x64-tid.py" --verify "$SHIP/kernel32-x64tid.dll.tmp" "$SHIP/kernel32.dll"; then
            mv "$SHIP/kernel32-x64tid.dll.tmp" "$SHIP/kernel32-x64tid.dll"
            echo "::notice::kernel32-x64tid.dll built and verified"
        else
            rm -f "$SHIP/kernel32-x64tid.dll.tmp"
            echo "::warning::kernel32-x64tid.dll failed to build or verify"
            tail -n 30 "$B.kernel32-x64tid.log" || true
        fi
    fi
    git -C "$R/wine" checkout -- dlls/kernel32/sync.c dlls/kernel32/Makefile.in
    touch "$R/wine/dlls/kernel32/Makefile.in"
    rm -f "$R/wine/dlls/kernel32/tid_x64.c" "$R/wine/dlls/kernel32/tid_ec.c" "$k32" "$B"/dlls/kernel32/arm64ec-windows/*.o
fi
