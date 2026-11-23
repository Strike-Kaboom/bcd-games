#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Modified 2026-11-23 for BCD-M5 fork (Strike-Kaboom/bcd-games).
# Includes work from BCD by thebcd69 (https://github.com/thebcd69/bcd-games).
"""madeira-m5: DXMT low-latency Present + silence native-BC [bc-stream] spam.

Targets two measured Dark Souls III (and general D3D11) bottlenecks:
  1. Input lag (~110+ ms):
     - dxmt_command_queue.hpp hardcodes max_latency_ = 3 with no config clamp.
       We add MADEIRA_MAX_FRAME_LATENCY (default 1; 0 restores upstream 3; 1..16
       clamps both initial latency and SetMaxLatency()).
     - d3d11_swapchain.cpp: pace MADEIRA_FPS_CAP on the game's Present1() thread
       right after PresentBoundary() (using QPC + Sleep + short spin) so input
       is sampled right before rendering the next frame instead of 3 frames early
       (opt-out via MADEIRA_D3D11_PRESENT_PACE=0).
  2. Synchronous 45 MB log storm on native-BC GPUs (Apple M5 bc=1):
     - d3d11_context_impl.cpp: BCStreamReport() skips logging when total==0 and
       no fallback decode/clamp/copy translation happened (removes 74,735 ERR
       lines per Dark Souls III session).

Runs from a directory containing dxmt/src/... (same convention as all
tools/patch-dxmt-*.py scripts; included in tools/build-d3d11-dll.sh BCD_PATCHES).
"""
import pathlib
import sys

MARK = "[m5-latency] madeira-m5"


def edit_one(path: pathlib.Path, name: str, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    if new in text:
        return False
    n = text.count(old)
    if n != 1:
        sys.exit(f"patch-dxmt-m5-latency: anchor '{name}' found {n} times in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
    return True


def main():
    changed = False

    # 1. dxmt/src/dxmt/dxmt_command_queue.hpp: max_latency_ cap (default 1; MADEIRA_MAX_FRAME_LATENCY=0 -> 3)
    cq = pathlib.Path("dxmt/src/dxmt/dxmt_command_queue.hpp")
    cq_old_field = "  uint32_t max_latency_ = 3;"
    cq_new_field = """  uint32_t max_latency_ = 1; /* madeira-m5: default 1 (override via MADEIRA_MAX_FRAME_LATENCY) */
  uint32_t max_latency_cap_ = 1;"""
    cq_old_set = "  void SetMaxLatency(uint32_t value) { max_latency_ = value; };"
    cq_new_set = """  void InitMaxLatencyCap();

  void SetMaxLatency(uint32_t value) {
    if (value < 1) value = 1;
    max_latency_ = value < max_latency_cap_ ? value : max_latency_cap_;
  };"""
    changed |= edit_one(cq, "max_latency_ field", cq_old_field, cq_new_field)
    changed |= edit_one(cq, "SetMaxLatency clamp", cq_old_set, cq_new_set)

    # Define InitMaxLatencyCap() and call it from CommandQueue constructor (uses Win32-aware env::getEnvVar)
    cqc = pathlib.Path("dxmt/src/dxmt/dxmt_command_queue.cpp")
    cqc_old_def = "CommandQueue::CommandQueue(WMT::Device device) :"
    cqc_new_def = """void
CommandQueue::InitMaxLatencyCap() {
  std::string env_s = env::getEnvVar("MADEIRA_MAX_FRAME_LATENCY");
  uint32_t cap = 1;
  if (!env_s.empty()) {
    long v = std::strtol(env_s.c_str(), nullptr, 10);
    cap = (v == 0) ? 16u : (v < 1 ? 1u : (v > 16 ? 16u : static_cast<uint32_t>(v)));
  }
  max_latency_cap_ = cap;
  max_latency_ = (env_s == "0") ? 3u : (3u < cap ? 3u : cap);
  WARN(\"""" + MARK + """ maxFrameLatency=", max_latency_, " cap=", max_latency_cap_);
}

CommandQueue::CommandQueue(WMT::Device device) :"""
    cqc_old_call = "  event = device.newSharedEvent();"
    cqc_new_call = """  event = device.newSharedEvent();
  InitMaxLatencyCap();"""
    changed |= edit_one(cqc, "CommandQueue InitMaxLatencyCap def", cqc_old_def, cqc_new_def)
    changed |= edit_one(cqc, "CommandQueue InitMaxLatencyCap call", cqc_old_call, cqc_new_call)

    # 2. dxmt/src/d3d11/d3d11_swapchain.cpp: game-thread Present1 pacing for MADEIRA_FPS_CAP
    sc = pathlib.Path("dxmt/src/d3d11/d3d11_swapchain.cpp")
    sc_old = """    cmd_queue.PresentBoundary();

    {
      double inside_ms = std::chrono::duration<double, std::milli>("""
    sc_new = """    cmd_queue.PresentBoundary();

    /* """ + MARK + """: pace MADEIRA_FPS_CAP on the game's Present1() thread so the
     * game samples input right before rendering the next frame instead of queuing
     * frames ahead of the encode-thread limiter. MADEIRA_D3D11_PRESENT_PACE=0 disables. */
    {
      static int s_pace_init = 0;
      static double s_period_qpc = 0.0;
      static double s_qpc_per_ms = 0.0;
      static LARGE_INTEGER s_next_qpc = {};
      if (!s_pace_init) {
        s_pace_init = 1;
        std::string en = env::getEnvVar("MADEIRA_D3D11_PRESENT_PACE");
        std::string cap_s = env::getEnvVar("MADEIRA_FPS_CAP");
        if (en != "0" && !cap_s.empty()) {
          long cap = std::strtol(cap_s.c_str(), nullptr, 10);
          if (cap >= 10 && cap <= 240) {
            LARGE_INTEGER freq = {};
            if (QueryPerformanceFrequency(&freq) && freq.QuadPart > 0) {
              s_period_qpc = static_cast<double>(freq.QuadPart) / static_cast<double>(cap);
              s_qpc_per_ms = static_cast<double>(freq.QuadPart) / 1000.0;
              WARN(\"""" + MARK + """ game-thread Present1 pacer active: ", cap, " fps");
            }
          }
        }
      }
      if (s_period_qpc > 0.0) {
        LARGE_INTEGER now = {};
        QueryPerformanceCounter(&now);
        int64_t period = static_cast<int64_t>(s_period_qpc);
        if (s_next_qpc.QuadPart == 0 || now.QuadPart > s_next_qpc.QuadPart + period) {
          s_next_qpc.QuadPart = now.QuadPart + period;
        } else {
          int64_t rem = s_next_qpc.QuadPart - now.QuadPart;
          if (rem > 0) {
            double rem_ms = static_cast<double>(rem) / s_qpc_per_ms;
            if (rem_ms > 2.5) {
              Sleep(static_cast<DWORD>(rem_ms - 2.0));
            }
            for (;;) {
              QueryPerformanceCounter(&now);
              if (now.QuadPart >= s_next_qpc.QuadPart) break;
              SwitchToThread();
            }
          }
          s_next_qpc.QuadPart += period;
        }
      }
    }

    {
      double inside_ms = std::chrono::duration<double, std::milli>("""
    changed |= edit_one(sc, "Present1 game-thread pacer", sc_old, sc_new)

    # 3. dxmt/src/d3d11/d3d11_context_impl.cpp: silence [bc-stream] spam when native BC handles everything
    ctx = pathlib.Path("dxmt/src/d3d11/d3d11_context_impl.cpp")
    ctx_old = """  uint32_t total = 0;
  for (int i = 0; i < 16; i++) total += g_bc_stream_ok[i].load(std::memory_order_relaxed);
  ERR("[bc-stream] ml744 decoded total=", total,"""
    ctx_new = """  uint32_t total = 0;
  for (int i = 0; i < 16; i++) total += g_bc_stream_ok[i].load(std::memory_order_relaxed);
  /* madeira-m5: silence 74,000+ [bc-stream] ERR lines on native hardware-BC GPUs when nothing decoded */
  if (total == 0 &&
      g_bc_stream_fail.load(std::memory_order_relaxed) == 0 &&
      g_bc_clamp_xlated.load(std::memory_order_relaxed) == 0 &&
      g_bc_clamp_dropped.load(std::memory_order_relaxed) == 0 &&
      g_cp_xlated.load(std::memory_order_relaxed) == 0 &&
      g_cp_dropped.load(std::memory_order_relaxed) == 0 &&
      g_cp_bc_stg_decoded.load(std::memory_order_relaxed) == 0 &&
      g_cp_bc_stg_fail.load(std::memory_order_relaxed) == 0)
    return;
  ERR("[bc-stream] ml744 decoded total=", total,"""
    changed |= edit_one(ctx, "BCStreamReport quiet on native BC", ctx_old, ctx_new)

    print("patch-dxmt-m5-latency: " + ("patched" if changed else "already patched"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
