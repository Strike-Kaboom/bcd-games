#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""madeira-m5 0.1.717 x64-leaf: the pure x86-64 COM leaf methods linked into madeira_d3d12.dll.

Without arguments, check the sources: madeira_x64_leaf.c keeps every leaf in the ".x64leaf"
section, touches no global, calls nothing, and tail-jumps to its ARM64EC fallback; the header's
layout constants are asserted on both sides; madeira_d3d12.c installs the leaves only behind
bcd.cfg x64-leaf = 1 and sets x64_flags where devices and lists are created; the build script and
the workflow compile and link the x64 object and run this check on the result.

--d3d12 DLL also inspects the linked DLL (modelled on check-x64-graphics-entry.py): every leaf is
in a code-map X64 range on pages no ARM64EC range touches, the section holds no word an ARM64 x18
patcher would rewrite, every jump out of the section lands on the leaf's ARM64EC fallback (an
ARM64EC-range symbol with a nonzero entry-thunk word before it), no leaf calls anything, and the
.hexpthk entries check-x64-graphics-entry.py asserts are still there.
"""
from pathlib import Path
import argparse
import glob
import importlib.util
import os
import re
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'madeira-d3d12/src/pe'
PURE = ['res_GetGPUVirtualAddress', 'res_GetDesc', 'memheap_GetDesc',
        'heap_GetCPUDescriptorHandleForHeapStart', 'heap_GetGPUDescriptorHandleForHeapStart',
        'device_GetDescriptorHandleIncrementSize']
FALLBACK = ['device_CopyDescriptorsSimple', 'device_CreateConstantBufferView',
            'list_SetGraphicsRootDescriptorTable', 'list_SetComputeRootDescriptorTable',
            'list_DrawInstanced', 'list_DrawIndexedInstanced', 'list_SetPipelineState']
LEAVES = PURE + FALLBACK
SECTION = '.x64leaf'
PAGE = 0x1000
IMAGE_SCN_MEM_EXECUTE = 0x20000000


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def body_of(text, signature):
    """The brace-delimited body following the first occurrence of signature."""
    at = text.index(signature)
    brace = text.index('{', at)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
    raise AssertionError(f'unterminated body after {signature!r}')


def host_checks():
    leaf = (SRC / 'madeira_x64_leaf.c').read_text(encoding='utf-8')
    header = (SRC / 'madeira_x64_leaf.h').read_text(encoding='utf-8')
    native = (SRC / 'madeira_d3d12.c').read_text(encoding='utf-8')
    for path in (SRC / 'madeira_x64_leaf.c', SRC / 'madeira_x64_leaf.h', ROOT / 'tests/host/check-x64-leaf.py'):
        head = path.read_text(encoding='utf-8').splitlines()[:2]   # the first line, or the one after a shebang
        assert any('SPDX-License-Identifier: GPL-3.0-only' in l for l in head), f'{path.name}: GPL-3.0 SPDX header'

    # 1. every leaf: one definition, in the section, noinline; nothing else defines code
    assert '#define MAD_X64L_LEAF __attribute__((section(".x64leaf"), noinline))' in leaf, 'the leaf attribute names the section'
    assert '#define MAD_X64L_INLINE static inline __attribute__((always_inline))' in leaf, 'helpers are always_inline'
    assert 'static inline' not in leaf.replace('static inline __attribute__((always_inline))', ''), 'a helper without always_inline could land in .text'
    definitions = re.findall(r'^MAD_X64L_LEAF\b[^\n]*?\bmad_x64l_(\w+)\(', leaf, re.M)          # one-line signatures
    definitions += re.findall(r'^MAD_X64L_LEAF\b[^(\n]*\n\s*mad_x64l_(\w+)\(', leaf, re.M)       # the name on the next line
    assert sorted(definitions) == sorted(LEAVES), f'leaves defined: {sorted(definitions)}'
    for name in LEAVES:
        assert f'mad_x64l_{name}(' in header, f'{name}: declared in the shared header'
    # the fallback declarations name the "#" bodies, the only symbols the object may reach
    for name in FALLBACK:
        assert f'__asm__("#mad_ecfb_{name}")' in leaf, f'{name}: the fallback names the ARM64EC body'

    # 2. bodies: object fields and arguments only; the one jump out is the fallback
    helpers = set(re.findall(r'MAD_X64L_INLINE\s+[\w\s\*]+?\b(mad_x64l_\w+)\(', leaf))
    allowed_calls = helpers | {'sizeof', 'offsetof', 'return', 'if', 'for', 'while', 'MAD_X64L_TAIL'}
    for name in LEAVES:
        body = re.sub(r'/\*.*?\*/', '', body_of(leaf, f'mad_x64l_{name}('), flags=re.S)   # the code, not its comments
        assert not re.search(r'\bg_\w+', body), f'{name}: reads a global'
        calls = set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', body)) - allowed_calls
        calls -= {f'mad_ecfb_{name}'} if name in FALLBACK else set()
        calls = {c for c in calls if not re.fullmatch(r'(struct|const|unsigned|uint64_t|size_t|UINT|SIZE_T|uintptr_t|void|int|D3D12_\w+|ID3D12\w+|D3D12_GPU_VIRTUAL_ADDRESS)', c)}
        assert not calls, f'{name}: calls {sorted(calls)}'
        if name in FALLBACK:
            assert body.count(f'MAD_X64L_TAIL return mad_ecfb_{name}(') == 1, f'{name}: exactly one tail jump to its fallback'
        else:
            assert 'mad_ecfb_' not in body, f'{name}: a pure leaf has no fallback'
    assert 'EnterCriticalSection' not in leaf and 'Acquire' not in leaf and 'alloc(' not in leaf.replace('mad_x64l_', ''), 'no lock, no allocation'

    # 3. the layout contract is asserted on both sides
    constants = re.findall(r'^#define (MAD_X64L_\w+(?:_OFF|_SIZE|_MAX))\s', header, re.M)
    constants += ['MAD_X64L_MC_PSO', 'MAD_X64L_MC_ROOT', 'MAD_X64L_MC_DRAW', 'MAD_X64L_MC_DRAW_INDEXED', 'MAD_X64L_MC_CROOT']
    assert len(constants) >= 20, constants
    header_asserts = re.findall(r'^MAD_X64L_CHECK\((.*)\);', header, re.M)
    native_asserts = [m for m in re.findall(r'_Static_assert\(((?:[^;])*?)"x64-leaf:', native, re.S)]
    for c in constants:
        if c in ('MAD_X64L_CMD_U_OFF',) or not c.startswith('MAD_X64L_MC_'):
            assert any(c in a for a in native_asserts), f'{c}: asserted against the real struct in madeira_d3d12.c'
        if c.endswith(('_OFF', '_SIZE')) and c not in ('MAD_X64L_RTV_SIZE',):
            assert any(c in a for a in header_asserts), f'{c}: asserted against the mirror in the header'
    assert '_Static_assert(MC_PSO == MAD_X64L_MC_PSO && MC_ROOT == MAD_X64L_MC_ROOT' in native, 'enum values asserted'

    # 4. madeira_d3d12.c: external fallbacks that call the static methods; the install behind the switch
    for name in FALLBACK:
        wrapper = body_of(native, f'\nvoid STDMETHODCALLTYPE mad_ecfb_{name}(')
        assert re.search(rf'\b{name}\(This', wrapper), f'{name}: the fallback calls the ARM64EC method'
    init = body_of(native, 'static void mad_x64_leaf_init(void)')
    assert 'mad_cfg_int_pe("x64-leaf", 0)' in init and init.index('if (!want) { g_x64_leaf = 0; return; }') < init.index('MAD_X64L_INSTALL('), 'default off, decided before any slot changes'
    assert init.index('mad_sync_diag_load();') < init.index('MAD_X64L_INSTALL(') and 'mad_scbv_on() > 0 || mad_vc_on()' in init, 'diagnostics veto the leaves before any slot changes'
    installs = re.findall(r'MAD_X64L_INSTALL\((\S+), mad_x64l_(\w+)\);', init)
    assert sorted(n for _, n in installs) == sorted(LEAVES), f'installed: {sorted(n for _, n in installs)}'
    assert 'mad_x64_graphics_entry_pe((const void *)(fn), &__ImageBase)' in init, 'slots name the PE view'
    build = body_of(native, 'static void build_vtables(void)')
    assert build.rstrip().endswith('mad_x64_leaf_init();   /* madeira-m5 0.1.717 x64-leaf: last, so the ARM64EC slots above are what it replaces (only with x64-leaf = 1) */\n}'), 'installed after every ARM64EC slot'
    assert native.count('l->x64_flags = g_x64_leaf > 0 ? MAD_X64L_OK : 0;') == 2, 'both list constructors set x64_flags'
    assert native.count('d->x64_flags = g_x64_leaf > 0 ? MAD_X64L_OK : 0;') == 1, 'the device constructor sets x64_flags'
    assert '#include "madeira_x64_leaf.h"' in native

    # 5. the build compiles, links and checks it
    script = (ROOT / 'tools/build-madeira-d3d12-dll.sh').read_text(encoding='utf-8')
    workflow = (ROOT / '.github/workflows/build-d3d12-m5-dll.yml').read_text(encoding='utf-8')
    for text, what in ((script, 'build script'), (workflow, 'workflow')):
        assert re.search(r'x86_64-w64-mingw32-clang"? -c -O2 -Wall -Werror -fno-builtin -ffreestanding', text), f'{what}: compiles the leaf for x86_64 with -Wall -Werror'
        assert '"$OUT/madeira_x64_leaf.o"' in text and text.index('madeira_x64_leaf.o" "$SRC/madeira_x64_leaf.c"') < text.index('"$SRC/madeira_d3d12.c" "$OUT/madeira_x64_leaf.o"'), f'{what}: links the object into the DLL'
        assert "grep -v '^#mad_ecfb_'" in text, f'{what}: the object reaches nothing but the fallbacks'
        assert 'check-x64-leaf.py" --d3d12 "$OUT/madeira_d3d12.dll"' in text, f'{what}: runs this check on the DLL'
        assert text.index('check-x64-graphics-entry.py" --d3d12') < text.index('check-x64-leaf.py" --d3d12'), f'{what}: after the graphics-entry check'

    # 6. the x86_64 compiler, when it is around: zero warnings, and the header's asserts hold on that side
    cc = find_tool('x86_64-w64-mingw32-clang')
    if cc:
        r = subprocess.run([cc, '-fsyntax-only', '-O2', '-Wall', '-Werror', '-fno-builtin', '-ffreestanding',
                            '-I' + str(SRC), str(SRC / 'madeira_x64_leaf.c')], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        print('PASS x86_64 compile: madeira_x64_leaf.c is warning-free and its mirror asserts hold')
    else:
        print('note: x86_64-w64-mingw32-clang not found; the x86_64 compile runs in the DLL build')
    print(f'PASS leaves: {len(LEAVES)} in {SECTION}, {len(FALLBACK)} with a tail jump to their ARM64EC fallback, no global, no call, no lock')
    print('PASS layout contract: every constant asserted against the real structs and the mirrors')
    print('PASS install: x64-leaf = 0 by default, diagnostics veto it, 13 slots through the PE view, x64_flags at creation')
    print('PASS build: x86_64 object compiled with -Wall -Werror, linked, checked by this script in the script and the workflow')


def find_tool(name):
    for candidate in (os.environ.get(name.upper().replace('-', '_')), shutil.which(name)):
        if candidate and Path(candidate).exists():
            return candidate
    for pattern in (str(ROOT / ('toolchains/llvm-mingw-*/bin/' + name)) + '*', '/opt/llvm-mingw*/bin/' + name + '*'):
        hits = sorted(p for p in glob.glob(pattern) if Path(p).name in (name, name + '.exe'))   # not clang++ or clang-scan-deps
        if hits:
            return hits[-1]
    return None


def disassemble(objdump, dll, pe, section):
    """(function rva, instruction rva, mnemonic, target rva or None) per instruction, from llvm-objdump."""
    out = subprocess.run([objdump, '-d', '--section=' + section, str(dll)], capture_output=True, text=True, check=True).stdout
    rows, function = [], None
    for line in out.splitlines():
        m = re.match(r'^([0-9a-f]{16}) <([^>]+)>:$', line)
        if m:
            function = int(m.group(1), 16) - pe.base
            continue
        m = re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(\S+)\s*(.*)$', line)
        if not m or function is None:
            continue
        mnemonic, operands = m.group(3), m.group(4)
        target = None
        t = re.match(r'0x([0-9a-f]+)', operands)
        if t and (mnemonic.startswith('j') or mnemonic == 'call'):
            target = int(t.group(1), 16) - pe.base
        rows.append((function, int(m.group(1), 16) - pe.base, mnemonic, target))
    assert rows, 'objdump produced no instructions for ' + section
    return rows


def rel32_scan(data, lo, hi, base_rva):
    """Fallback for a build without llvm-objdump: every E9 / 0F 8x rel32 and E8 rel32 encoding in [lo, hi)."""
    found = []
    for i in range(lo, hi):
        if data[i] == 0xE9 and i + 5 <= hi:
            found.append(('jmp', base_rva + i - lo, base_rva + i - lo + 5 + struct.unpack_from('<i', data, i + 1)[0]))
        elif data[i] == 0xE8 and i + 5 <= hi:
            found.append(('call', base_rva + i - lo, base_rva + i - lo + 5 + struct.unpack_from('<i', data, i + 1)[0]))
        elif data[i] == 0x0F and i + 6 <= hi and 0x80 <= data[i + 1] <= 0x8F:
            found.append(('jcc', base_rva + i - lo, base_rva + i - lo + 6 + struct.unpack_from('<i', data, i + 2)[0]))
    return found


def pe_checks(dll, objdump):
    entry = load_module('x64_graphics_entry', ROOT / 'tests/host/check-x64-graphics-entry.py')
    x18_role = load_module('x64_tls_patch', ROOT / 'tools/patch-wine-kernelbase-x64-tls.py').x18_role
    pe = entry.PE(dll)
    sections = {s[0]: s for s in pe.sections}
    assert SECTION in sections, f'{SECTION} section missing'
    name, rva, size, raw, rawsize, flags = sections[SECTION]
    assert flags & IMAGE_SCN_MEM_EXECUTE, f'{SECTION}: not executable'
    assert rva % PAGE == 0, f'{SECTION}: not page-aligned ({rva:#x})'
    lo, hi = rva, rva + size
    page_lo, page_hi = lo & ~(PAGE - 1), (hi + PAGE - 1) & ~(PAGE - 1)

    # 1. the section is one X64 code-map range, on pages no ARM64EC range touches
    ec = [(r_lo, r_lo + r_size) for r_lo, r_size, kind in pe.ranges if kind == 1]
    assert ec, 'no ARM64EC range in the code map'
    for r_lo, r_hi in ec:
        assert r_hi <= page_lo or r_lo >= page_hi, f'{SECTION} pages {page_lo:#x}-{page_hi:#x} overlap ARM64EC range {r_lo:#x}-{r_hi:#x}'
    leaves = {}
    for n in LEAVES:
        sym = 'mad_x64l_' + n
        assert sym in pe.symbols, f'{sym}: not in the symbol table'
        at = pe.symbols[sym]
        assert lo <= at < hi, f'{sym}: {at:#x} outside {SECTION}'
        assert pe.kind(at) == 2, f'{sym}: code map says {pe.kind(at)}, not X64'
        assert pe.symbols.get('#' + sym, at) == at, f'{sym}: the # alias names another address'
        leaves[at] = n
    for s, at in pe.symbols.items():
        if lo <= at < hi and not s.lstrip('#').startswith('mad_x64l_'):
            raise AssertionError(f'{s}: a symbol other than a leaf in {SECTION}')
    assert pe.kind(lo) == 2 and pe.kind(hi - 1) == 2, f'{SECTION}: not wholly in an X64 range'
    print(f'PASS {SECTION}: {len(LEAVES)} leaves at {lo:#x}-{hi:#x}, X64 in the code map, pages {page_lo:#x}-{page_hi:#x} disjoint from every ARM64EC range')

    # 2. no word an ARM64 x18 patcher would rewrite. The patcher (virtual_ios.c) and
    # patch-wine-kernelbase-x64-tls.py read 4-byte-aligned words, as an ARM64 instruction stream is
    # laid out; the unaligned readings are reported, since x64 bytes form them by chance.
    data = pe.data[raw:raw + max(rawsize, size)]
    bad = [(off, struct.unpack_from('<I', data, off)[0]) for off in range(0, len(data) - 3) if x18_role(struct.unpack_from('<I', data, off)[0])]
    aligned = [b for b in bad if b[0] % 4 == 0]
    assert not aligned, f'{SECTION}: x18 encodings at aligned offsets {[hex(o) for o, _ in aligned[:8]]}'
    print(f'PASS {SECTION}: {len(data)} bytes hold no x18_role() encoding at any aligned word'
          + (f' ({len(bad)} unaligned byte offsets read as one: {[hex(o) for o, _ in bad[:4]]}; a word patcher never reads there)' if bad else ''))

    # 3. jumps out of the section: the fallback, and nothing else; no calls at all
    fallbacks = {}
    for n in FALLBACK:
        sym = '#mad_ecfb_' + n
        assert sym in pe.symbols, f'{sym}: ARM64EC fallback missing'
        at = pe.symbols[sym]
        assert pe.kind(at) == 1, f'{sym}: not in an ARM64EC range'
        word = pe.u32(pe.offset(at - 4, 4))
        assert word, f'{sym}: zero entry-thunk word before the body'
        fallbacks[n] = (at, word)
    ordered = sorted(leaves)
    extent = {at: (ordered[i + 1] if i + 1 < len(ordered) else hi) for i, at in enumerate(ordered)}
    out_targets = {n: set() for n in LEAVES}
    calls = []
    if objdump:
        rows = disassemble(objdump, dll, pe, SECTION)
        for function, at, mnemonic, target in rows:
            n = leaves.get(function)
            assert n, f'instruction at {at:#x} belongs to no leaf'
            if mnemonic == 'call':
                calls.append((n, at))
            if target is not None and not (lo <= target < hi):
                out_targets[n].add(target)
        mode = 'llvm-objdump'
    else:
        for at in ordered:
            n = leaves[at]
            for kind, where, target in rel32_scan(data, at - lo, extent[at] - lo, lo):
                if lo <= target < hi:
                    continue
                on_fallback = any(target == f[0] for f in fallbacks.values())
                if kind == 'call':
                    if on_fallback or target in pe.symbols.values():   # a rel32 that lands on a symbol is a real call, not data
                        calls.append((n, where))
                elif on_fallback:
                    out_targets[n].add(target)
        mode = 'rel32 scan (llvm-objdump not found)'
    assert not calls, f'leaves call something: {calls}'
    for n in LEAVES:
        if n in FALLBACK:
            at, word = fallbacks[n]
            assert out_targets[n] == {at}, f'{n}: jumps out of the section to {sorted(map(hex, out_targets[n]))}, expected only #mad_ecfb_{n} at {at:#x}'
        else:
            assert not out_targets[n], f'{n}: a pure leaf jumps out of the section to {sorted(map(hex, out_targets[n]))}'
    print(f'PASS fallbacks ({mode}): {len(FALLBACK)} leaves jump only to their #mad_ecfb_* ARM64EC body, each with a nonzero entry-thunk word; '
          f'{len(PURE)} pure leaves never leave the section; no call anywhere')

    # 4. the .hexpthk entries check-x64-graphics-entry.py asserts
    for method in entry.D3D12_METHODS:
        pe.entry(method)
    print('PASS .hexpthk: the typed x64 graphics entries are intact beside the leaves')


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--d3d12')
    args.add_argument('--objdump', help='llvm-objdump to disassemble .x64leaf with (found in toolchains/ or PATH otherwise)')
    ns = args.parse_args()
    host_checks()
    if ns.d3d12:
        pe_checks(Path(ns.d3d12), ns.objdump or find_tool('llvm-objdump'))
    print('OK check-x64-leaf')
