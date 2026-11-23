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
  5. Module.cpp & InvalidationTracker.{h,cpp}: scale hot SMC page tracking to
     512 slots, align hot-page tracking and re-protection skips to Apple
     Silicon's 16 KB hardware page size on iOS (so neighbor 4 KB re-protects
     never silently re-write-protect a hot 16 KB page), and default
     MADEIRA_SMC_HOT_PAGE to 8 (MADEIRA_SMC_HOT_PAGE=0 disables) so hot SMC
     pages promote immediately instead of triggering 100k+ Mach exceptions and
     128 MB JIT code-cache rollovers.
  6. Core.cpp (IosSkipInvalidationCallRetReset): fix the broken direct-mapped
     Table[256] (Thread >> 12) & 255 hash that threw away 15/16 slots on 64 KB-
     aligned Thread pointers (causing 142k / 1.13 TB of redundant 8 MB callret
     resets), upgrade to a 1024-entry open-addressed table keyed on >> 16, and
     default MADEIRA_CALLRET_RESET_RATE to 500 ms on iOS (0 disables).
  7. InvalidationTracker.cpp (non-exec VirtualAlloc/VirtualFree fast path):
     add a shared_lock interval-intersection check in HandleMemoryProtection-
     Notification and InvalidateAlignedInterval (Free=true) so freeing ordinary
     non-executable data buffers never acquires CodeInvalidationMutex (stop-
     the-world) or loops all threads or acquires IntervalsLock exclusively.

Usage:
  patch-fex-ios-m5-opt.py FEX_DIR
"""
import os
import sys

MARK = "madeira-m5-opt-v1"
MARK_V2 = "madeira-m5-opt-v2"


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

    # 6. FEXCore/Source/Interface/Core/Core.cpp (callret reset hash-collision fix + 500ms default)
    callret_old = """static bool IosSkipInvalidationCallRetReset(FEXCore::Core::InternalThreadState* Thread) {
  static uint64_t IntervalTicks = ~0ULL;
  if (IntervalTicks == ~0ULL) {
    uint64_t Ms = 0;
    if (const char* Rate = getenv("MADEIRA_CALLRET_RESET_RATE"); Rate && *Rate) {
      Ms = strtoull(Rate, nullptr, 0);
    }
    uint64_t Frequency = 0;
    if (Ms) {
      __asm volatile("mrs %0, cntfrq_el0" : "=r"(Frequency));
    }
    IntervalTicks = Frequency / 1000 * Ms;
  }
  if (!IntervalTicks) {
    return false;
  }

  uint64_t Now;
  __asm volatile("mrs %0, cntvct_el0" : "=r"(Now));
  // Direct-mapped by thread: a collision only means an extra reset.
  struct LastReset {
    FEXCore::Core::InternalThreadState* Thread;
    uint64_t Ticks;
  };
  static LastReset Table[256];
  auto& Entry = Table[(reinterpret_cast<uintptr_t>(Thread) >> 12) & 255];
  if (Entry.Thread == Thread && Now - Entry.Ticks < IntervalTicks) {
    static uint64_t Skipped = 0;
    if ((++Skipped & 0xfff) == 1) {
      LogMan::Msg::EFmt("[callret] invalidation resets skipped={} (at most one per thread every {} ticks; "
                        "MADEIRA_CALLRET_RESET_RATE=0 disables)", Skipped, IntervalTicks);
    }
    return true;
  }
  Entry = {Thread, Now};
  return false;
}"""
    callret_new = """static bool IosSkipInvalidationCallRetReset(FEXCore::Core::InternalThreadState* Thread) {
  /* """ + MARK_V2 + """: default 500 ms rate limit (MADEIRA_CALLRET_RESET_RATE=0 disables) and
   * collision-free 1024-slot open-addressed table keyed on >> 16 (64 KB-aligned Thread pointers
   * previously collided in 16/256 buckets with >> 12, causing 140k+ redundant 8 MB resets). */
  static uint64_t IntervalTicks = ~0ULL;
  if (IntervalTicks == ~0ULL) {
    uint64_t Ms = 500;
    if (const char* Rate = getenv("MADEIRA_CALLRET_RESET_RATE"); Rate && *Rate) {
      Ms = strtoull(Rate, nullptr, 0);
    }
    uint64_t Frequency = 0;
    if (Ms) {
      __asm volatile("mrs %0, cntfrq_el0" : "=r"(Frequency));
    }
    IntervalTicks = Frequency / 1000 * Ms;
  }
  if (!IntervalTicks) {
    return false;
  }

  uint64_t Now;
  __asm volatile("mrs %0, cntvct_el0" : "=r"(Now));
  struct LastReset {
    FEXCore::Core::InternalThreadState* Thread;
    uint64_t Ticks;
  };
  static constexpr size_t TableSize = 1024;
  static LastReset Table[TableSize];
  const uintptr_t Key = reinterpret_cast<uintptr_t>(Thread);
  const size_t BaseIdx = ((Key >> 16) ^ (Key >> 26)) & (TableSize - 1);
  LastReset* Slot = nullptr;
  for (size_t Probe = 0; Probe < 16; ++Probe) {
    auto& Cand = Table[(BaseIdx + Probe) & (TableSize - 1)];
    if (Cand.Thread == Thread) {
      Slot = &Cand;
      break;
    }
    if (!Cand.Thread && !Slot) {
      Slot = &Cand;
    }
  }
  if (!Slot) {
    Slot = &Table[BaseIdx];
  }
  if (Slot->Thread == Thread && Now - Slot->Ticks < IntervalTicks) {
    static uint64_t Skipped = 0;
    if ((++Skipped & 0xfff) == 1) {
      LogMan::Msg::EFmt("[callret] """ + MARK_V2 + """ invalidation resets skipped={} (at most one per thread every {} ticks; "
                        "MADEIRA_CALLRET_RESET_RATE=0 disables)", Skipped, IntervalTicks);
    }
    return true;
  }
  *Slot = {Thread, Now};
  return false;
}"""
    patch_file(core, [("Core.cpp callret reset table", callret_old, callret_new)])

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

    # 5. Source/Windows/ARM64EC/Module.cpp (default MADEIRA_SMC_HOT_PAGE = 8)
    mod = os.path.join(fex, "Source", "Windows", "ARM64EC", "Module.cpp")
    smc_old = """    uint32_t HotThreshold = 0;
    if (const char* Hot = getenv("MADEIRA_SMC_HOT_PAGE"); Hot && *Hot) {
      HotThreshold = static_cast<uint32_t>(strtoul(Hot, nullptr, 0));
    }"""
    smc_new = """    /* """ + MARK_V2 + """: default hot SMC page threshold to 8 faults/sec per 16 KB page (MADEIRA_SMC_HOT_PAGE=0 disables) */
    uint32_t HotThreshold = 8;
    if (const char* Hot = getenv("MADEIRA_SMC_HOT_PAGE"); Hot && *Hot) {
      HotThreshold = static_cast<uint32_t>(strtoul(Hot, nullptr, 0));
    }"""
    patch_file(mod, [("Module.cpp SMC hot page default", smc_old, smc_new)])

    # 7. Source/Windows/Common/InvalidationTracker.h (512 hot-SMC slots)
    inv_h = os.path.join(fex, "Source", "Windows", "Common", "InvalidationTracker.h")
    invh_old = """  static constexpr size_t HotFaultSlots = 64;
  static constexpr size_t MaxHotPages = 64;"""
    invh_new = """  /* """ + MARK_V2 + """: scale hot SMC tables for multi-page protectors (e.g. Dark Souls III's ~49 hot 16 KB pages) */
  static constexpr size_t HotFaultSlots = 512;
  static constexpr size_t MaxHotPages = 512;"""
    patch_file(inv_h, [("InvalidationTracker.h hot SMC capacity", invh_old, invh_new)])

    # 8. Source/Windows/Common/InvalidationTracker.cpp (non-exec fast paths + 16 KB iOS hot-SMC pages)
    inv_c = os.path.join(fex, "Source", "Windows", "Common", "InvalidationTracker.cpp")
    inv_prot_old = """  const auto AlignedBase = Address & FEXCore::Utils::FEX_PAGE_MASK;
  const auto AlignedSize = (Address - AlignedBase + Size + FEXCore::Utils::FEX_PAGE_SIZE - 1) & FEXCore::Utils::FEX_PAGE_MASK;

  const bool NeedsInvalidate = [&]() {
    std::unique_lock Lock(IntervalsLock);"""
    inv_prot_new = """  const auto AlignedBase = Address & FEXCore::Utils::FEX_PAGE_MASK;
  const auto AlignedSize = (Address - AlignedBase + Size + FEXCore::Utils::FEX_PAGE_SIZE - 1) & FEXCore::Utils::FEX_PAGE_MASK;

#if defined(FEX_IOS_HOST) && defined(ARCHITECTURE_arm64ec)
  /* """ + MARK_V2 + """: avoid exclusive IntervalsLock on ordinary non-exec VirtualAlloc/Protect calls */
  if (!ProtHasExec(Prot)) {
    std::shared_lock Lock(IntervalsLock);
    if (!DEPDisabled && !XIntervals.Intersect({AlignedBase, AlignedBase + AlignedSize})) {
      return;
    }
  }
#endif

  const bool NeedsInvalidate = [&]() {
    std::unique_lock Lock(IntervalsLock);"""

    inv_free_old = """  const auto AlignedBase = Address & FEXCore::Utils::FEX_PAGE_MASK;
  const auto AlignedSize = std::max(Size, (Address - AlignedBase + Size + FEXCore::Utils::FEX_PAGE_SIZE - 1) & FEXCore::Utils::FEX_PAGE_MASK);

  InvalidateIntervalInternal(AlignedBase, AlignedSize);"""
    inv_free_new = """  const auto AlignedBase = Address & FEXCore::Utils::FEX_PAGE_MASK;
  const auto AlignedSize = std::max(Size, (Address - AlignedBase + Size + FEXCore::Utils::FEX_PAGE_SIZE - 1) & FEXCore::Utils::FEX_PAGE_MASK);

#if defined(FEX_IOS_HOST) && defined(ARCHITECTURE_arm64ec)
  /* """ + MARK_V2 + """: skip stop-the-world CodeInvalidationMutex + all-thread loop + exclusive IntervalsLock
   * when freeing an ordinary non-executable buffer above 4 GB (eliminates 60+/frame lock storms in DS3). */
  if (Free && Address && AlignedBase >= 0x100000000ULL && AlignedSize < (1ULL << 30)) {
    std::shared_lock Lock(IntervalsLock);
    const FEXCore::IntervalList<uint64_t>::Interval Range {AlignedBase, AlignedBase + AlignedSize};
    if (!XIntervals.Intersect(Range) && !RWXIntervals.Intersect(Range)) {
      return;
    }
  }
#endif

  InvalidateIntervalInternal(AlignedBase, AlignedSize);"""

    inv_hot_fault_old = """  if (NeedsInvalidate) {
    // MADEIRA: a page that turns hot here is invalidated below as usual, once: from then on nothing
    // compiled from it relies on the write trap.
    if (CountSMCWriteFault(FaultAddress & FEXCore::Utils::FEX_PAGE_MASK)) {
      static std::atomic<uint32_t> HotLogCount {0};
      if (HotLogCount.fetch_add(1, std::memory_order_relaxed) < 16) {
        LogMan::Msg::EFmt("[smc-hot] page {:#x} took {} write faults within a second: no longer write-protected, its blocks "
                          "validate their code per instruction (MADEIRA_SMC_HOT_PAGE=0 disables)",
                          FaultAddress & FEXCore::Utils::FEX_PAGE_MASK, HotPageThreshold);
      }
    }
    // IntervalsLock cannot be held during invalidation
    {
      std::scoped_lock Lock(CTX.GetCodeInvalidationMutex());

      InvalidateIntervalInternalLocked(FaultAddress & FEXCore::Utils::FEX_PAGE_MASK, FEXCore::Utils::FEX_PAGE_SIZE);"""
    inv_hot_fault_new = """  if (NeedsInvalidate) {
    /* """ + MARK_V2 + """: on Apple Silicon (16 KB hardware mprotect pages), key hot SMC pages at 16 KB
     * and invalidate the entire 16 KB hardware page once on promotion so neighbor 4 KB reprotects never re-trap it. */
#ifdef FEX_IOS_HOST
    constexpr uint64_t HotPageSize = 0x4000ULL;
    constexpr uint64_t HotPageMask = ~(HotPageSize - 1);
#else
    constexpr uint64_t HotPageSize = FEXCore::Utils::FEX_PAGE_SIZE;
    constexpr uint64_t HotPageMask = FEXCore::Utils::FEX_PAGE_MASK;
#endif
    const bool BecameHot = CountSMCWriteFault(FaultAddress & HotPageMask);
    if (BecameHot) {
      static std::atomic<uint32_t> HotLogCount {0};
      if (HotLogCount.fetch_add(1, std::memory_order_relaxed) < 16) {
        LogMan::Msg::EFmt("[smc-hot] page {:#x} took {} write faults within a second: no longer write-protected, its blocks "
                          "validate their code per instruction (MADEIRA_SMC_HOT_PAGE=0 disables)",
                          FaultAddress & HotPageMask, HotPageThreshold);
      }
    }
    // IntervalsLock cannot be held during invalidation
    {
      std::scoped_lock Lock(CTX.GetCodeInvalidationMutex());

      if (BecameHot) {
        InvalidateIntervalInternalLocked(FaultAddress & HotPageMask, HotPageSize);
      } else {
        InvalidateIntervalInternalLocked(FaultAddress & FEXCore::Utils::FEX_PAGE_MASK, FEXCore::Utils::FEX_PAGE_SIZE);
      }"""

    inv_hot_helpers_old = """bool InvalidationTracker::IsHotSMCPage(uint64_t Address) const {
  const auto Used = HotPagesUsed.load(std::memory_order_acquire);
  if (!Used) {
    return false;
  }
  const auto Page = Address & FEXCore::Utils::FEX_PAGE_MASK;
  for (uint32_t i = 0; i < Used; ++i) {
    if (HotPages[i].load(std::memory_order_acquire) == Page) {
      return true;
    }
  }
  return false;
}

bool InvalidationTracker::CountSMCWriteFault(uint64_t Page) {
  // madeira-bcd (round 632): hot pages are off unless MADEIRA_SMC_HOT_PAGE names a threshold; then a write fault reads no clock and
  // takes no lock (the threshold is written once, in EnableHotSMCPages, before any guest code runs).
  if (!HotPageThreshold) {
    return false;
  }
  uint64_t Now, Frequency;
  __asm volatile("mrs %0, cntvct_el0" : "=r"(Now));
  __asm volatile("mrs %0, cntfrq_el0" : "=r"(Frequency));

  std::scoped_lock Lock(HotPagesLock);
  if (!HotPageThreshold || !Page) {
    return false;
  }

  // Direct-mapped: a page evicted by another one simply starts counting again.
  auto& Slot = HotFaults[(Page >> FEXCore::Utils::FEX_PAGE_SHIFT) % HotFaultSlots];
  if (Slot.Page != Page || Now - Slot.WindowStart > Frequency) {
    Slot = {Page, Now, 0};
  }
  if (++Slot.Count < HotPageThreshold) {
    return false;
  }
  Slot = {};

  const auto Used = HotPagesUsed.load(std::memory_order_relaxed);
  for (uint32_t i = 0; i < Used; ++i) {
    if (!HotPages[i].load(std::memory_order_relaxed)) {
      HotPages[i].store(Page, std::memory_order_release);
      return true;
    }
  }
  if (Used == MaxHotPages) {
    // Table full: this page keeps the write trap.
    return false;
  }
  HotPages[Used].store(Page, std::memory_order_release);
  HotPagesUsed.store(Used + 1, std::memory_order_release);
  return true;
}

void InvalidationTracker::ForgetHotSMCPages(uint64_t Begin, uint64_t End) {
  if (!HotPagesUsed.load(std::memory_order_acquire)) {
    return;
  }
  std::scoped_lock Lock(HotPagesLock);
  const auto Used = HotPagesUsed.load(std::memory_order_relaxed);
  for (uint32_t i = 0; i < Used; ++i) {
    const auto Page = HotPages[i].load(std::memory_order_relaxed);
    if (Page && Page >= Begin && Page < End) {
      HotPages[i].store(0, std::memory_order_release);
    }
  }
}"""
    inv_hot_helpers_new = """bool InvalidationTracker::IsHotSMCPage(uint64_t Address) const {
  const auto Used = HotPagesUsed.load(std::memory_order_acquire);
  if (!Used) {
    return false;
  }
#ifdef FEX_IOS_HOST
  const auto Page = Address & ~0x3FFFULL;
#else
  const auto Page = Address & FEXCore::Utils::FEX_PAGE_MASK;
#endif
  for (uint32_t i = 0; i < Used; ++i) {
    if (HotPages[i].load(std::memory_order_acquire) == Page) {
      return true;
    }
  }
  return false;
}

bool InvalidationTracker::CountSMCWriteFault(uint64_t Page) {
  if (!HotPageThreshold) {
    return false;
  }
  uint64_t Now, Frequency;
  __asm volatile("mrs %0, cntvct_el0" : "=r"(Now));
  __asm volatile("mrs %0, cntfrq_el0" : "=r"(Frequency));

  std::scoped_lock Lock(HotPagesLock);
  if (!HotPageThreshold || !Page) {
    return false;
  }

#ifdef FEX_IOS_HOST
  constexpr uint32_t HotPageShift = 14;
#else
  constexpr uint32_t HotPageShift = FEXCore::Utils::FEX_PAGE_SHIFT;
#endif
  auto& Slot = HotFaults[(Page >> HotPageShift) % HotFaultSlots];
  if (Slot.Page != Page || Now - Slot.WindowStart > Frequency) {
    Slot = {Page, Now, 0};
  }
  if (++Slot.Count < HotPageThreshold) {
    return false;
  }
  Slot = {};

  const auto Used = HotPagesUsed.load(std::memory_order_relaxed);
  for (uint32_t i = 0; i < Used; ++i) {
    if (HotPages[i].load(std::memory_order_relaxed) == Page) {
      return false;
    }
  }
  for (uint32_t i = 0; i < Used; ++i) {
    if (!HotPages[i].load(std::memory_order_relaxed)) {
      HotPages[i].store(Page, std::memory_order_release);
      return true;
    }
  }
  if (Used == MaxHotPages) {
    return false;
  }
  HotPages[Used].store(Page, std::memory_order_release);
  HotPagesUsed.store(Used + 1, std::memory_order_release);
  return true;
}

void InvalidationTracker::ForgetHotSMCPages(uint64_t Begin, uint64_t End) {
  if (!HotPagesUsed.load(std::memory_order_acquire)) {
    return;
  }
  std::scoped_lock Lock(HotPagesLock);
#ifdef FEX_IOS_HOST
  constexpr uint64_t HotPageSize = 0x4000ULL;
#else
  constexpr uint64_t HotPageSize = FEXCore::Utils::FEX_PAGE_SIZE;
#endif
  const auto Used = HotPagesUsed.load(std::memory_order_relaxed);
  for (uint32_t i = 0; i < Used; ++i) {
    const auto Page = HotPages[i].load(std::memory_order_relaxed);
    if (Page && Page + HotPageSize > Begin && Page < End) {
      HotPages[i].store(0, std::memory_order_release);
    }
  }
}"""

    inv_reprot_old = """        // MADEIRA: never write-protect a hot page again; protect the runs of pages around it.
        uint64_t RunBegin = Address;
        for (uint64_t Page = Address & FEXCore::Utils::FEX_PAGE_MASK; Page < ProtectEnd; Page += FEXCore::Utils::FEX_PAGE_SIZE) {
          if (IsHotSMCPage(Page)) {
            if (RunBegin < std::max(Page, Address)) {
              Protect(RunBegin, std::max(Page, Address));
            }
            RunBegin = std::min(Page + FEXCore::Utils::FEX_PAGE_SIZE, ProtectEnd);
          }
        }
        if (RunBegin < ProtectEnd) {
          Protect(RunBegin, ProtectEnd);
        }"""
    inv_reprot_new = """        // """ + MARK_V2 + """: never write-protect a hot 16 KB Apple Silicon page again; protect runs around it.
#ifdef FEX_IOS_HOST
        constexpr uint64_t StepSize = 0x4000ULL;
        constexpr uint64_t StepMask = ~(StepSize - 1);
#else
        constexpr uint64_t StepSize = FEXCore::Utils::FEX_PAGE_SIZE;
        constexpr uint64_t StepMask = FEXCore::Utils::FEX_PAGE_MASK;
#endif
        uint64_t RunBegin = Address;
        for (uint64_t Page = Address & StepMask; Page < ProtectEnd; Page += StepSize) {
          if (IsHotSMCPage(Page)) {
            const uint64_t SkipStart = std::max(Page, Address);
            if (RunBegin < SkipStart) {
              Protect(RunBegin, SkipStart);
            }
            RunBegin = std::min(Page + StepSize, ProtectEnd);
          }
        }
        if (RunBegin < ProtectEnd) {
          Protect(RunBegin, ProtectEnd);
        }"""

    patch_file(inv_c, [
        ("InvalidationTracker.cpp HandleMemoryProtection fast path", inv_prot_old, inv_prot_new),
        ("InvalidationTracker.cpp InvalidateAlignedInterval fast path", inv_free_old, inv_free_new),
        ("InvalidationTracker.cpp 16KB hot SMC promotion", inv_hot_fault_old, inv_hot_fault_new),
        ("InvalidationTracker.cpp 16KB hot SMC helpers", inv_hot_helpers_old, inv_hot_helpers_new),
        ("InvalidationTracker.cpp 16KB hot SMC reprotect skip", inv_reprot_old, inv_reprot_new),
    ])

    print("patch-fex-ios-m5-opt: all 8 M5 v2 optimizations applied cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
