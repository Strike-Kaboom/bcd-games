#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Modified 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""madeira-m5: Apple Silicon (M5 / ARMv9.2) FEX-Emu optimizations & bug fixes.

Applied to the FEX submodule during tools/build-xtajit64.sh right before
compiling arm64ecfex (xtajit64.dll):

  1. CPUFeatures.cpp: wire probed M5 ARMv9.2 features from FEX_MADEIRA_HOSTPROBE
     (FRINTTS, RPRES, CSSC, ECV, WFXT) into FEXCore::HostFeatures (opt-out via
     MADEIRA_M5_ISA=0 or standard FEX_HOSTFEATURES disable flags) and set
     Apple Silicon 128-byte cache line sizes when LSE2=1 is probed.
  2. Core.cpp (volatile-metadata TSO bug): fix ForceTSOValidRanges gating so
     blocks inside a valid volatile-metadata range set BlockInForceTSOValidRange
     even when no individual instruction in the block is volatile, and guard
     against dereferencing ForceTSOInstructions.end() (upstream FEX 444c37fe2 /
     PR #6150).
  3. Core.cpp (CompileBlock hot-path cleanup): remove the racy cross-core
     __sync_add/sub_and_fetch Boyer-Moore hot-RIP estimator (62M atomic RMWs
     and unsigned underflow in Dark Souls III), the 4-slot global thread array
     writes on every dispatch, and the leftover hardcoded FMOD RIP switch
     (which dereferenced rbx/*rbx/**rbx on 0x140006feb). Keeps rpm_cas_snapshot
     and a relaxed-atomic [CB_SUMMARY] every 65536 calls when MADEIRA_CB_SUMMARY=1.
  4. LookupCache.h: replace std::chrono::system_clock::now() (which triggers an
     iOS Mach exec-fault redirect) with hardware CNTVCT_EL0/CNTFRQ_EL0, and raise
     MIN_L1_ENTRIES (8K -> 32K) and MAX_L1_ENTRIES (128K -> 512K) for 12 GB+ iPads
     to curb L1 cache thrashing (61.3M misses in Dark Souls III).
  5. Module.cpp: default MADEIRA_SMC_HOT_PAGE to 64 (upstream FEX default;
     MADEIRA_SMC_HOT_PAGE=0 still disables it) to avoid SMC recompile storms.

Usage:
  patch-fex-ios-m5-opt.py FEX_DIR
"""
import os
import sys

MARK = "madeira-m5-opt-v1"


def patch_file(path, edits):
    text = open(path, "r", encoding="utf-8", errors="surrogateescape").read()
    changed = False
    for name, old, new in edits:
        if new in text:
            continue
        n = text.count(old)
        if n != 1:
            sys.exit(f"patch-fex-ios-m5-opt: anchor '{name}' found {n} times in {path}")
        text = text.replace(old, new, 1)
        changed = True
    if changed:
        open(path, "w", encoding="utf-8", errors="surrogateescape").write(text)
    return changed


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fex = sys.argv[1]

    # 1. Source/Windows/Common/CPUFeatures.cpp
    cpuf = os.path.join(fex, "Source", "Windows", "Common", "CPUFeatures.cpp")
    cpuf_old = """    HostFeatures.SupportsTSOImm9 = Has("LRCPC2", '1') && !(Override & FEXCore::Config::HostFeatures::DISABLELRCPC2);
    HostFeatures.SupportsAFP = (Override & FEXCore::Config::HostFeatures::ENABLEAFP) && !Has("AFP", '0');
    LogMan::Msg::IFmt("FEX: ml1231 iOS ARM64EC host features: LRCPC2={} AFP={} (probe {})", HostFeatures.SupportsTSOImm9,
                      HostFeatures.SupportsAFP, Probe ? Probe : "none");"""
    cpuf_new = """    HostFeatures.SupportsTSOImm9 = Has("LRCPC2", '1') && !(Override & FEXCore::Config::HostFeatures::DISABLELRCPC2);
    HostFeatures.SupportsAFP = (Override & FEXCore::Config::HostFeatures::ENABLEAFP) && !Has("AFP", '0');
    /* """ + MARK + """: wire probed Apple M-series ARMv9.2 ISA features (opt-out: MADEIRA_M5_ISA=0) */
    const char* M5IsaEnv = getenv("MADEIRA_M5_ISA");
    const bool M5IsaOn = !(M5IsaEnv && M5IsaEnv[0] == '0' && M5IsaEnv[1] == '\\0');
    if (M5IsaOn) {
      HostFeatures.SupportsFRINTTS = Has("FRINTTS", '1') && !(Override & FEXCore::Config::HostFeatures::DISABLEFRINTTS);
      HostFeatures.SupportsRPRES = Has("RPRES", '1') && !(Override & FEXCore::Config::HostFeatures::DISABLERPRES);
      HostFeatures.SupportsCSSC = Has("CSSC", '1') && !(Override & FEXCore::Config::HostFeatures::DISABLECSSC);
      HostFeatures.SupportsECV = Has("ECV", '1');
      HostFeatures.SupportsWFXT = Has("WFXT", '1');
      if (Has("LSE2", '1')) {
        HostFeatures.DCacheLineSize = 128;
        HostFeatures.ICacheLineSize = 128;
      }
    }
    LogMan::Msg::IFmt("FEX: """ + MARK + """ host features: LRCPC2={} AFP={} FRINTTS={} RPRES={} CSSC={} ECV={} WFXT={} line={} (probe {})",
                      HostFeatures.SupportsTSOImm9, HostFeatures.SupportsAFP,
                      HostFeatures.SupportsFRINTTS, HostFeatures.SupportsRPRES,
                      HostFeatures.SupportsCSSC, HostFeatures.SupportsECV,
                      HostFeatures.SupportsWFXT, HostFeatures.DCacheLineSize,
                      Probe ? Probe : "none");"""
    patch_file(cpuf, [("CPUFeatures M5 ISA", cpuf_old, cpuf_new)])

    # 2 & 3. FEXCore/Source/Interface/Core/Core.cpp
    core = os.path.join(fex, "FEXCore", "Source", "Interface", "Core", "Core.cpp")
    tso_old = """      bool BlockInForceTSOValidRange = false;
      auto InstForceTSOIt = ForceTSOInstructions.end();
      if (ForceTSOValidRanges.Contains({Block.Entry, Block.Entry + Block.Size})) {
        if (auto It = ForceTSOInstructions.lower_bound(Block.Entry); *It < Block.Entry + Block.Size) {
          InstForceTSOIt = It;
          BlockInForceTSOValidRange = true;
        }
      }"""
    tso_new = """      /* """ + MARK + """: volatile-metadata TSO fix (upstream 444c37fe2 / PR #6150) */
      bool BlockInForceTSOValidRange = false;
      auto InstForceTSOIt = ForceTSOInstructions.end();
      if (ForceTSOValidRanges.Contains({Block.Entry, Block.Entry + Block.Size})) {
        BlockInForceTSOValidRange = true;
        if (auto It = ForceTSOInstructions.lower_bound(Block.Entry);
            It != ForceTSOInstructions.end() && *It < Block.Entry + Block.Size) {
          InstForceTSOIt = It;
        }
      }"""

    cb_old_start = """  /* iOS-Madeira 2026-05-18 low-noise summary. Replaces per-call log (which"""
    cb_old_end = """  static_cast<ContextImpl*>(Thread->CTX)->SyscallHandler->PreCompile();"""
    core_text = open(core, "r", encoding="utf-8", errors="surrogateescape").read()
    if MARK + " CompileBlock lean" not in core_text:
        i0 = core_text.find(cb_old_start)
        i1 = core_text.find(cb_old_end)
        if i0 == -1 or i1 == -1 or i1 <= i0:
            sys.exit(f"patch-fex-ios-m5-opt: CompileBlock instrumentation anchors not found in {core}")
        cb_block = core_text[i0:i1]
        cb_new = """  /* """ + MARK + """ CompileBlock lean: removed racy Boyer-Moore cross-core atomics,
   * 4-slot global thread array writes, and hardcoded FMOD RIP switch/dereferences.
   * Keeps lightweight relaxed-atomic compile counter and rpm_cas_snapshot drain. */
  {
    uint64_t total = __atomic_add_fetch(&g_cb_total, 1, __ATOMIC_RELAXED);
    if ((total & 0xFFFFull) == 0) {
      static int s_cb_summary = -1;
      if (s_cb_summary < 0) {
        const char* e = getenv("MADEIRA_CB_SUMMARY");
        s_cb_summary = (e && e[0] == '1' && !e[1]) ? 1 : 0;
      }
      if (s_cb_summary) {
        uint64_t reals = __atomic_load_n(&g_cb_real_compiles, __ATOMIC_RELAXED);
        auto* T = Frame ? Frame->Thread : nullptr;
        LogMan::Msg::EFmt("[CB_SUMMARY] total={} real_compiles={} cache_hits={} hit_rate={}% L1mask=0x{:x} cacheL1=0x{:x}",
                          total, reals, total - reals,
                          (total > 0) ? (100 * (total - reals) / total) : 0,
                          Frame ? Frame->State.L1Mask : 0,
                          (T && T->LookupCache) ? T->LookupCache->GetL1Pointer() : 0);
      }
#ifdef FEX_IOS_HOST
      {
        rpm_cas_snapshot Snap;
        if (rpm_cas_snapshot_take(&Snap)) {
          LogMan::Msg::EFmt("[rpm-cas] ml622 loop={} {} page=0x{:x} block=0x{:x} heap=0x{:x} atomic=0x{:x} "
                            "teb=0x{:x} ret=0x{:x} class={} ptype={} idx={}/{} list_size={} used={} is_full={} "
                            "prev_token=0x{:x} cur_token=0x{:x} | fail changed={} unchanged={} invalid={}",
                            Snap.which_loop, Snap.quarantined ? "QUARANTINED (block leaked, spin abandoned)" : "spinning",
                            Snap.page_addr, Snap.block_addr, Snap.heap_addr, Snap.atomic_addr, Snap.owner_teb,
                            Snap.ret_addr, Snap.size_class, Snap.page_type, Snap.block_index, Snap.block_count,
                            Snap.list_size, Snap.block_used, Snap.is_full, Snap.prev_token, Snap.cur_token,
                            Snap.fail_changed, Snap.fail_unchanged, Snap.fail_invalid);
        }
      }
#endif
    }
  }

"""
        patch_file(core, [("Core.cpp volatile TSO", tso_old, tso_new), ("Core.cpp CompileBlock lean", cb_block, cb_new)])
    else:
        patch_file(core, [("Core.cpp volatile TSO", tso_old, tso_new)])

    # 4. FEXCore/Source/Interface/Core/LookupCache.h
    lc = os.path.join(fex, "FEXCore", "Source", "Interface", "Core", "LookupCache.h")
    lc_clock_old = """    const auto CurrentTime = std::chrono::system_clock::now();
    const auto Period = CurrentTime - LastPeriod;
    if (Period >= SamplePeriod) {
      // If larger than the sample period then check if we need to increase L1 cache size.
      const double AveragePerSecond = static_cast<double>(L2L3CacheHits) /
                                      static_cast<double>(std::chrono::duration_cast<std::chrono::milliseconds>(Period).count()) * 1000.0;"""
    lc_clock_new = """#if defined(FEX_IOS_HOST) && (defined(__aarch64__) || defined(__arm64ec__))
    /* """ + MARK + """: read CNTVCT_EL0/CNTFRQ_EL0 directly to avoid iOS exec-fault traps on system_clock::now() */
    uint64_t NowTicks = 0, FreqTicks = 0;
    asm volatile("mrs %0, cntvct_el0" : "=r"(NowTicks));
    asm volatile("mrs %0, cntfrq_el0" : "=r"(FreqTicks));
    if (LastPeriodTicks == 0) {
      LastPeriodTicks = NowTicks;
      L2L3CacheHits = 0;
      return;
    }
    const uint64_t DeltaTicks = NowTicks - LastPeriodTicks;
    if (FreqTicks != 0 && DeltaTicks >= FreqTicks) {
      const double AveragePerSecond = static_cast<double>(L2L3CacheHits) * static_cast<double>(FreqTicks) / static_cast<double>(DeltaTicks);
#else
    const auto CurrentTime = std::chrono::system_clock::now();
    const auto Period = CurrentTime - LastPeriod;
    if (Period >= SamplePeriod) {
      // If larger than the sample period then check if we need to increase L1 cache size.
      const double AveragePerSecond = static_cast<double>(L2L3CacheHits) /
                                      static_cast<double>(std::chrono::duration_cast<std::chrono::milliseconds>(Period).count()) * 1000.0;
#endif"""
    lc_upd_old = """      // Update Last period to start again.
      LastPeriod = CurrentTime;
      L2L3CacheHits = 0;"""
    lc_upd_new = """      // Update Last period to start again.
#if defined(FEX_IOS_HOST) && (defined(__aarch64__) || defined(__arm64ec__))
      LastPeriodTicks = NowTicks;
#else
      LastPeriod = CurrentTime;
#endif
      L2L3CacheHits = 0;"""
    lc_size_old = """  constexpr static size_t MIN_L1_ENTRIES = 8 * 1024;        // Must be a power of 2
#ifdef FEX_IOS_HOST
  /* iOS-Madeira ml363: cap the dynamic-L1 growth ceiling at 128K entries (2MB)"""
    lc_size_new = """#ifdef FEX_IOS_HOST
  /* """ + MARK + """: 32K min (512KB) -> 512K max (8MB) for 12GB+ iPads (demand-paged per thread) */
  constexpr static size_t MIN_L1_ENTRIES = 32 * 1024;       // Must be a power of 2
#else
  constexpr static size_t MIN_L1_ENTRIES = 8 * 1024;        // Must be a power of 2
#endif
#ifdef FEX_IOS_HOST
  /* iOS-Madeira ml363: cap the dynamic-L1 growth ceiling at 128K entries (2MB)"""
    lc_max_old = """  constexpr static size_t MAX_L1_ENTRIES = 128 * 1024; // Must be a power of 2"""
    lc_max_new = """  constexpr static size_t MAX_L1_ENTRIES = 512 * 1024; // Must be a power of 2 (madeira-m5-opt-v1)"""
    lc_field_old = """  std::chrono::time_point<std::chrono::system_clock> LastPeriod {};"""
    lc_field_new = """  std::chrono::time_point<std::chrono::system_clock> LastPeriod {};
  uint64_t LastPeriodTicks {};"""
    patch_file(lc, [
        ("LookupCache CNTVCT clock", lc_clock_old, lc_clock_new),
        ("LookupCache CNTVCT update", lc_upd_old, lc_upd_new),
        ("LookupCache MIN_L1_ENTRIES", lc_size_old, lc_size_new),
        ("LookupCache MAX_L1_ENTRIES", lc_max_old, lc_max_new),
        ("LookupCache LastPeriodTicks", lc_field_old, lc_field_new),
    ])

    # 5. Source/Windows/ARM64EC/Module.cpp (default MADEIRA_SMC_HOT_PAGE = 64)
    mod = os.path.join(fex, "Source", "Windows", "ARM64EC", "Module.cpp")
    smc_old = """    uint32_t HotThreshold = 0;
    if (const char* Hot = getenv("MADEIRA_SMC_HOT_PAGE"); Hot && *Hot) {
      HotThreshold = static_cast<uint32_t>(strtoul(Hot, nullptr, 0));
    }"""
    smc_new = """    /* """ + MARK + """: default hot SMC page threshold to upstream 64 (MADEIRA_SMC_HOT_PAGE=0 disables) */
    uint32_t HotThreshold = 64;
    if (const char* Hot = getenv("MADEIRA_SMC_HOT_PAGE"); Hot && *Hot) {
      HotThreshold = static_cast<uint32_t>(strtoul(Hot, nullptr, 0));
    }"""
    patch_file(mod, [("Module.cpp SMC hot page default", smc_old, smc_new)])

    print("patch-fex-ios-m5-opt: all 5 M5 optimizations applied cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
