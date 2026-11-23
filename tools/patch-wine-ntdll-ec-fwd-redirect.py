#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Modified 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""Fix ARM64EC forwarded-export CHPE redirection in Wine's ntdll (signal_arm64ec.c).

Root cause of the build-498 ntdll-sync.dll boot crash:
When an ARM64EC DLL (e.g. ucrtbase.dll's _lock during early DllMain before FEX
boots) imports a PE-forwarded symbol such as kernel32!EnterCriticalSection ->
NTDLL.RtlEnterCriticalSection, find_forwarded_export() returns the target address
inside ntdll.dll, and import_dll() then calls:
    arm64ec_redirect_ptr(imp_mod /* kernel32 */, proc /* inside ntdll */, imp_metadata)
Because `proc` lies outside `kernel32`, `rva = proc - kernel32` misses kernel32's
CHPE RedirectionMetadata. Stock ntdll.dll only survived by accident because its
export started with a 10-byte Fast-Forward Sequence (48 8b c4 ... e9), which the
fallback byte decoder followed. With ntdll-sync.dll (or any EXP+# x64 fast-path
export in ntdll/kernelbase/kernel32), the export starts with x64 instructions, so
the fallback missed and stored the un-redirected x64 address in ucrtbase's IAT,
causing check_icall to jump through the still-NULL ExitToX64 dispatcher at boot.

Fix: at the start of arm64ec_redirect_ptr(), if `ptr` lies outside `module`'s
image range, resolve the actual owning module via InLoadOrderModuleList and use
its base address and CHPE RedirectionMetadata.

Usage:
  patch-wine-ntdll-ec-fwd-redirect.py WINE_SRC   (idempotent; fails on moved anchor)
"""
import os
import sys

MARKER = "madeira-m5: forwarded-export CHPE redirect"

OLD = """void *arm64ec_redirect_ptr( HMODULE module, void *ptr, const IMAGE_ARM64EC_METADATA *metadata )
{
    const IMAGE_ARM64EC_REDIRECTION_ENTRY *map = get_rva( module, metadata->RedirectionMetadata );
    int min = 0, max = metadata->RedirectionMetadataCount - 1;
    ULONG_PTR rva = (ULONG_PTR)ptr - (ULONG_PTR)module;

    if (!ptr) return NULL;"""

NEW = """void *arm64ec_redirect_ptr( HMODULE module, void *ptr, const IMAGE_ARM64EC_METADATA *metadata )
{
    const IMAGE_ARM64EC_REDIRECTION_ENTRY *map;
    int min, max;
    ULONG_PTR rva;

    if (!ptr) return NULL;

    /* """ + MARKER + """: a PE export forwarder (e.g. kernel32!EnterCriticalSection ->
     * NTDLL.RtlEnterCriticalSection, or kernel32!TlsGetValue -> KERNELBASE.TlsGetValue)
     * returns an address inside the target module rather than `module`. Resolve the
     * owning module's base and CHPE RedirectionMetadata before binary-searching. */
    {
        const IMAGE_NT_HEADERS *mod_nt = module ? RtlImageNtHeader( module ) : NULL;
        if (!mod_nt || (ULONG_PTR)ptr < (ULONG_PTR)module ||
            (ULONG_PTR)ptr >= (ULONG_PTR)module + mod_nt->OptionalHeader.SizeOfImage)
        {
            PEB *peb = RtlGetCurrentPeb();
            if (peb && peb->LdrData)
            {
                LIST_ENTRY *list = &peb->LdrData->InLoadOrderModuleList;
                LIST_ENTRY *entry;
                for (entry = list->Flink; entry != list; entry = entry->Flink)
                {
                    LDR_DATA_TABLE_ENTRY *mod_entry =
                        CONTAINING_RECORD( entry, LDR_DATA_TABLE_ENTRY, InLoadOrderLinks );
                    if ((char *)ptr >= (char *)mod_entry->DllBase &&
                        (char *)ptr < (char *)mod_entry->DllBase + mod_entry->SizeOfImage)
                    {
                        const IMAGE_ARM64EC_METADATA *real_meta =
                            arm64ec_get_module_metadata( mod_entry->DllBase );
                        if (!real_meta) return xlate_ios_jit( ptr );
                        module = mod_entry->DllBase;
                        metadata = real_meta;
                        break;
                    }
                }
            }
        }
    }
    if (!metadata) return xlate_ios_jit( ptr );
    map = get_rva( module, metadata->RedirectionMetadata );
    min = 0;
    max = metadata->RedirectionMetadataCount - 1;
    rva = (ULONG_PTR)ptr - (ULONG_PTR)module;"""


def patch_file(path):
    text = open(path, "r", encoding="utf-8", errors="surrogateescape").read()
    if MARKER in text:
        print("patch-wine-ntdll-ec-fwd-redirect: already patched")
        return 0
    n = text.count(OLD)
    if n != 1:
        sys.exit(f"patch-wine-ntdll-ec-fwd-redirect: anchor found {n} times in {path}")
    text = text.replace(OLD, NEW, 1)
    open(path, "w", encoding="utf-8", errors="surrogateescape").write(text)
    print("patch-wine-ntdll-ec-fwd-redirect: patched " + path)
    return 0


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    path = arg if os.path.isfile(arg) else os.path.join(arg, "dlls", "ntdll", "signal_arm64ec.c")
    if not os.path.isfile(path):
        sys.exit("patch-wine-ntdll-ec-fwd-redirect: missing " + path)
    return patch_file(path)


if __name__ == "__main__":
    sys.exit(main())
