#!/usr/bin/env python3
"""M5 Turbo optimizations for MetalFX frame generation & Present-FX (build 732):

1. Fast threadgroup-tiled FP16 optical flow (fg_luma / fg_flow / fg_motion):
   - Replaces brute-force 4-nested-loop global-texture-read fg_flow (~43M-319M
     texture reads/frame) with cooperative 8x8 threadgroup half SRAM tiles
     (12x12 cur + up to 28x28 prev = 1.85 KB total), hoisted 5x5 register patch,
     and 2-stage coarse (step-2, always visiting (0,0)) + fine 3x3 refinement.
   - Switches fg_flow dispatch to full uniform 8x8 dispatchThreadgroups: so
     every threadgroup safely reaches threadgroup_barrier before bounds exit.
   - Uses native Apple Silicon half (FP16) textures/math in fg_luma & fg_motion.

2. Opt-in async Present-FX offload (env.MADEIRA_PFX_ASYNC = 1):
   - Moves madeira_pfx_after_commit() off the D3D12SubmitDirect thread onto a
     dedicated QOS_CLASS_USER_INTERACTIVE serial GCD queue so blocking
     [CAMetalLayer nextDrawable] calls and MetalFX FrameGen encoding never stall
     next-frame command list replay (cuts 3.6-10.5 ms Direct-queue Present stalls).
   - Bumps MADEIRA_PFX_PICTURES from 3 -> 4 stand-in textures for smooth ring
     overlap, holds a weak-promoted CAMetalLayer reference released on the main
     queue for MRC safety, and keeps default OFF (0) unless opted in.

Runs after tools/patch-winemetal-frames-made.py. Idempotent; fails by name if
any anchor moves. Run from the repository root.
"""
import pathlib
import sys

PATH = pathlib.Path("dxmt/src/winemetal/unix/winemetal_unix.c")
MARKER = "madeira-bcd: m5-turbo (fp16 tiled fg_flow + async present-fx)"

A_FG_MSL = r'''static const char *g_fg_msl =
  "#include <metal_stdlib>\n"
  "using namespace metal;\n"
  "kernel void fg_luma(texture2d<float, access::sample> src [[texture(0)]],\n"
  "                    texture2d<float, access::write> dst [[texture(1)]],\n"
  "                    uint2 gid [[thread_position_in_grid]]) {\n"
  "  if (gid.x >= dst.get_width() || gid.y >= dst.get_height()) return;\n"
  "  constexpr sampler s(coord::normalized, filter::linear, address::clamp_to_edge);\n"
  "  float2 inv = 1.0 / float2(dst.get_width(), dst.get_height());\n"
  "  float2 uv = (float2(gid) + 0.5) * inv, q = inv * 0.25;\n"
  "  float3 c = src.sample(s, uv + float2(-q.x, -q.y)).rgb + src.sample(s, uv + float2(q.x, -q.y)).rgb\n"
  "           + src.sample(s, uv + float2(-q.x, q.y)).rgb + src.sample(s, uv + float2(q.x, q.y)).rgb;\n"
  "  dst.write(float4(dot(c * 0.25, float3(0.299, 0.587, 0.114)), 0, 0, 1), gid);\n"
  "}\n"
  "kernel void fg_flow(texture2d<float, access::read> cur [[texture(0)]],\n"
  "                    texture2d<float, access::read> prev [[texture(1)]],\n"
  "                    texture2d<float, access::write> flow [[texture(2)]],\n"
  "                    constant int &radius [[buffer(0)]],\n"
  "                    uint2 gid [[thread_position_in_grid]]) {\n"
  "  int W = cur.get_width(), H = cur.get_height();\n"
  "  if ((int)gid.x >= W || (int)gid.y >= H) return;\n"
  "  int2 p = int2(gid), hi = int2(W - 1, H - 1);\n"
  "  float best = 1e9; int2 bd = int2(0);\n"
  "  for (int dy = -radius; dy <= radius; dy++)\n"
  "    for (int dx = -radius; dx <= radius; dx++) {\n"
  "      float sad = 0.002 * float(abs(dx) + abs(dy));\n"
  "      for (int py = -2; py <= 2; py++)\n"
  "        for (int px = -2; px <= 2; px++) {\n"
  "          int2 a = clamp(p + int2(px, py), int2(0), hi);\n"
  "          int2 b = clamp(p + int2(px + dx, py + dy), int2(0), hi);\n"
  "          sad += fabs(cur.read(uint2(a)).r - prev.read(uint2(b)).r);\n"
  "        }\n"
  "      if (sad < best) { best = sad; bd = int2(dx, dy); }\n"
  "    }\n"
  "  flow.write(float4(float2(bd), 0, 0), gid);\n"
  "}\n"
  "kernel void fg_motion(texture2d<float, access::sample> flow [[texture(0)]],\n"
  "                      texture2d<float, access::write> motion [[texture(1)]],\n"
  "                      constant float &scale [[buffer(0)]],\n"
  "                      uint2 gid [[thread_position_in_grid]]) {\n"
  "  if (gid.x >= motion.get_width() || gid.y >= motion.get_height()) return;\n"
  "  constexpr sampler s(coord::normalized, filter::linear, address::clamp_to_edge);\n"
  "  float2 uv = (float2(gid) + 0.5) / float2(motion.get_width(), motion.get_height());\n"
  "  motion.write(float4(flow.sample(s, uv).rg * scale, 0, 0), gid);\n"
  "}\n";'''

NEW_FG_MSL = r'''/* madeira-bcd: m5-turbo (fp16 tiled fg_flow + async present-fx) (tools/patch-winemetal-m5-turbo.py) */
static const char *g_fg_msl =
  "#include <metal_stdlib>\n"
  "using namespace metal;\n"
  "kernel void fg_luma(texture2d<half, access::sample> src [[texture(0)]],\n"
  "                    texture2d<half, access::write> dst [[texture(1)]],\n"
  "                    uint2 gid [[thread_position_in_grid]]) {\n"
  "  if (gid.x >= dst.get_width() || gid.y >= dst.get_height()) return;\n"
  "  constexpr sampler s(coord::normalized, filter::linear, address::clamp_to_edge);\n"
  "  float2 inv = 1.0f / float2(dst.get_width(), dst.get_height());\n"
  "  float2 uv = (float2(gid) + 0.5f) * inv, q = inv * 0.25f;\n"
  "  half3 c = src.sample(s, uv + float2(-q.x, -q.y)).rgb + src.sample(s, uv + float2(q.x, -q.y)).rgb\n"
  "          + src.sample(s, uv + float2(-q.x, q.y)).rgb + src.sample(s, uv + float2(q.x, q.y)).rgb;\n"
  "  dst.write(half4(dot(c * 0.25h, half3(0.299h, 0.587h, 0.114h)), 0.0h, 0.0h, 1.0h), gid);\n"
  "}\n"
  "kernel void fg_flow(texture2d<half, access::read> cur [[texture(0)]],\n"
  "                    texture2d<half, access::read> prev [[texture(1)]],\n"
  "                    texture2d<half, access::write> flow [[texture(2)]],\n"
  "                    constant int &radius [[buffer(0)]],\n"
  "                    uint2 gid [[thread_position_in_grid]],\n"
  "                    uint2 lid [[thread_position_in_threadgroup]],\n"
  "                    uint2 tgp [[threadgroup_position_in_grid]]) {\n"
  "  threadgroup half t_cur[144];\n"
  "  threadgroup half t_prev[784];\n"
  "  int W = int(cur.get_width()), H = int(cur.get_height());\n"
  "  int2 hi = int2(W - 1, H - 1);\n"
  "  int r = clamp(radius, 1, 8);\n"
  "  int span = 12 + 2 * r;\n"
  "  int2 base = int2(tgp * 8u);\n"
  "  uint tid = lid.y * 8u + lid.x;\n"
  "  for (uint idx = tid; idx < 144u; idx += 64u) {\n"
  "    int lx = int(idx % 12u), ly = int(idx / 12u);\n"
  "    t_cur[idx] = cur.read(uint2(clamp(base + int2(lx - 2, ly - 2), int2(0), hi))).r;\n"
  "  }\n"
  "  uint ptotal = uint(span * span);\n"
  "  for (uint idx = tid; idx < ptotal; idx += 64u) {\n"
  "    int lx = int(idx % uint(span)), ly = int(idx / uint(span));\n"
  "    t_prev[idx] = prev.read(uint2(clamp(base + int2(lx - 2 - r, ly - 2 - r), int2(0), hi))).r;\n"
  "  }\n"
  "  threadgroup_barrier(mem_flags::mem_threadgroup);\n"
  "  if ((int)gid.x >= W || (int)gid.y >= H) return;\n"
  "  half cp[25];\n"
  "  int cx0 = int(lid.x), cy0 = int(lid.y);\n"
  "  for (int py = 0; py < 5; py++)\n"
  "    for (int px = 0; px < 5; px++)\n"
  "      cp[py * 5 + px] = t_cur[(cy0 + py) * 12 + (cx0 + px)];\n"
  "  int r2 = r & ~1;\n"
  "  half best = half(65000.0h); int2 bd = int2(0);\n"
  "  for (int dy = -r2; dy <= r2; dy += 2) {\n"
  "    int py0 = cy0 + r + dy;\n"
  "    for (int dx = -r2; dx <= r2; dx += 2) {\n"
  "      int px0 = cx0 + r + dx;\n"
  "      half sad = half(0.002h) * half(abs(dx) + abs(dy));\n"
  "      for (int py = 0; py < 5; py++) {\n"
  "        int row = (py0 + py) * span + px0;\n"
  "        int crow = py * 5;\n"
  "        sad += fabs(cp[crow + 0] - t_prev[row + 0]) + fabs(cp[crow + 1] - t_prev[row + 1])\n"
  "             + fabs(cp[crow + 2] - t_prev[row + 2]) + fabs(cp[crow + 3] - t_prev[row + 3])\n"
  "             + fabs(cp[crow + 4] - t_prev[row + 4]);\n"
  "      }\n"
  "      if (sad < best) { best = sad; bd = int2(dx, dy); }\n"
  "    }\n"
  "  }\n"
  "  int2 cbd = bd;\n"
  "  for (int oy = -1; oy <= 1; oy++) {\n"
  "    for (int ox = -1; ox <= 1; ox++) {\n"
  "      if (ox == 0 && oy == 0) continue;\n"
  "      int dx = clamp(cbd.x + ox, -r, r), dy = clamp(cbd.y + oy, -r, r);\n"
  "      int py0 = cy0 + r + dy, px0 = cx0 + r + dx;\n"
  "      half sad = half(0.002h) * half(abs(dx) + abs(dy));\n"
  "      for (int py = 0; py < 5; py++) {\n"
  "        int row = (py0 + py) * span + px0;\n"
  "        int crow = py * 5;\n"
  "        sad += fabs(cp[crow + 0] - t_prev[row + 0]) + fabs(cp[crow + 1] - t_prev[row + 1])\n"
  "             + fabs(cp[crow + 2] - t_prev[row + 2]) + fabs(cp[crow + 3] - t_prev[row + 3])\n"
  "             + fabs(cp[crow + 4] - t_prev[row + 4]);\n"
  "      }\n"
  "      if (sad < best) { best = sad; bd = int2(dx, dy); }\n"
  "    }\n"
  "  }\n"
  "  flow.write(half4(half(bd.x), half(bd.y), 0.0h, 0.0h), gid);\n"
  "}\n"
  "kernel void fg_motion(texture2d<half, access::sample> flow [[texture(0)]],\n"
  "                      texture2d<half, access::write> motion [[texture(1)]],\n"
  "                      constant float &scale [[buffer(0)]],\n"
  "                      uint2 gid [[thread_position_in_grid]]) {\n"
  "  if (gid.x >= motion.get_width() || gid.y >= motion.get_height()) return;\n"
  "  constexpr sampler s(coord::normalized, filter::linear, address::clamp_to_edge);\n"
  "  float2 uv = (float2(gid) + 0.5f) / float2(motion.get_width(), motion.get_height());\n"
  "  motion.write(half4(flow.sample(s, uv).rg * half(scale), 0.0h, 0.0h), gid);\n"
  "}\n";'''

A_FLOW_DISPATCH = "      madeira_fg_dispatch(enc, g_fg.k_flow, g_fg.flow.width, g_fg.flow.height);\n"
NEW_FLOW_DISPATCH = (
    "      [enc setComputePipelineState:g_fg.k_flow];   /* madeira-bcd: m5-turbo uniform 8x8 TG for threadgroup_barrier */\n"
    "      [enc dispatchThreadgroups:MTLSizeMake((g_fg.flow.width + 7) / 8, (g_fg.flow.height + 7) / 8, 1)\n"
    "          threadsPerThreadgroup:MTLSizeMake(8, 8, 1)];\n"
)

A_PFX_PICS = "#define MADEIRA_PFX_PICTURES 3\n"
NEW_PFX_PICS = "#define MADEIRA_PFX_PICTURES 4   /* madeira-bcd: m5-turbo extra ring slot for async present-fx */\n"

A_PFX_AFTER_VTI = r'''static void madeira_pfx_after_commit(id<MTLCommandBuffer> cb) {
  MadeiraPFXDrawable *px = objc_getAssociatedObject(cb, &g_pfx_key);
  unsigned long long n;
  if (!px) return;
  [px retain];
  objc_setAssociatedObject(cb, &g_pfx_key, nil, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
  if (px->_pending) {
    px->_pending = 0;
    atomic_fetch_sub_explicit(&g_pfx_pending, 1, memory_order_relaxed);
  }
  if (madeira_vti_want() && madeira_vti_take(cb, px)) {   /* madeira-bcd: vt-interp: its worker presents this frame and gives the picture back */
    [px release];
    return;
  }
  @autoreleasepool {
    id<MTLCommandBuffer> out = [cb.commandQueue commandBuffer];
    if (out && px->_mode == 1) {
      id<CAMetalDrawable> d = madeira_pfx_resolve(out, px);
      if (d) {
        madeira_log_present_cadence("presentDrawableAfterMinDuration", px->_after);
        [out presentDrawable:d afterMinimumDuration:px->_after];
      }
      madeira_pfx_commit(out);
    } else if (out) {
      struct unixcall_generic_obj_obj_noret p;
      memset(&p, 0, sizeof p);
      p.handle = (obj_handle_t)out;
      p.arg = (obj_handle_t)px;
      g_pfx_tls.deferred = 1;
      g_pfx_tls.committed = 0;
      _MTLCommandBuffer_presentDrawable(&p);
      g_pfx_tls.deferred = 0;
      if (!g_pfx_tls.committed) madeira_pfx_commit(out);
    }
  }
  madeira_pfx_slot_free(px);
  [px release];
  n = atomic_fetch_add_explicit(&g_pfx_frames, 1, memory_order_relaxed) + 1;
  if (n == 1 || (n % 1800) == 0)
    dprintf(STDERR_FILENO, "[present-fx] madeira-bcd %llu frames: %llu enlarged by MetalFX, %llu copied, %llu bilinear, %llu dropped "
                           "(generated frames included)\n", n, atomic_load_explicit(&g_pfx_scaled, memory_order_relaxed),
            atomic_load_explicit(&g_pfx_copied, memory_order_relaxed), atomic_load_explicit(&g_pfx_bilinear, memory_order_relaxed),
            atomic_load_explicit(&g_pfx_dropped, memory_order_relaxed));
}'''

A_PFX_AFTER = r'''static void madeira_pfx_after_commit(id<MTLCommandBuffer> cb) {
  MadeiraPFXDrawable *px = objc_getAssociatedObject(cb, &g_pfx_key);
  unsigned long long n;
  if (!px) return;
  [px retain];
  objc_setAssociatedObject(cb, &g_pfx_key, nil, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
  if (px->_pending) {
    px->_pending = 0;
    atomic_fetch_sub_explicit(&g_pfx_pending, 1, memory_order_relaxed);
  }
  @autoreleasepool {
    id<MTLCommandBuffer> out = [cb.commandQueue commandBuffer];
    if (out && px->_mode == 1) {
      id<CAMetalDrawable> d = madeira_pfx_resolve(out, px);
      if (d) {
        madeira_log_present_cadence("presentDrawableAfterMinDuration", px->_after);
        [out presentDrawable:d afterMinimumDuration:px->_after];
      }
      madeira_pfx_commit(out);
    } else if (out) {
      struct unixcall_generic_obj_obj_noret p;
      memset(&p, 0, sizeof p);
      p.handle = (obj_handle_t)out;
      p.arg = (obj_handle_t)px;
      g_pfx_tls.deferred = 1;
      g_pfx_tls.committed = 0;
      _MTLCommandBuffer_presentDrawable(&p);
      g_pfx_tls.deferred = 0;
      if (!g_pfx_tls.committed) madeira_pfx_commit(out);
    }
  }
  madeira_pfx_slot_free(px);
  [px release];
  n = atomic_fetch_add_explicit(&g_pfx_frames, 1, memory_order_relaxed) + 1;
  if (n == 1 || (n % 1800) == 0)
    dprintf(STDERR_FILENO, "[present-fx] madeira-bcd %llu frames: %llu enlarged by MetalFX, %llu copied, %llu bilinear, %llu dropped "
                           "(generated frames included)\n", n, atomic_load_explicit(&g_pfx_scaled, memory_order_relaxed),
            atomic_load_explicit(&g_pfx_copied, memory_order_relaxed), atomic_load_explicit(&g_pfx_bilinear, memory_order_relaxed),
            atomic_load_explicit(&g_pfx_dropped, memory_order_relaxed));
}'''

def make_new_pfx_after(with_vti: bool) -> str:
    vti = (
        "  if (madeira_vti_want() && madeira_vti_take(cb, px)) {   /* madeira-bcd: vt-interp: its worker presents this frame and gives the picture back */\n"
        "    [px release];\n"
        "    return;\n"
        "  }\n"
    ) if with_vti else ""
    return r'''/* madeira-bcd: m5-turbo async present-fx (opt-in: env.MADEIRA_PFX_ASYNC = 1). */
static int g_pfx_async_on = -1;
static dispatch_queue_t g_pfx_async_q;
static dispatch_once_t g_pfx_async_once;
static int madeira_pfx_async_enabled(void) {
  if (g_pfx_async_on < 0) {
    const char *e = getenv("MADEIRA_PFX_ASYNC");
    g_pfx_async_on = (e && *e && *e != '0') ? 1 : 0;
    if (g_pfx_async_on)
      dprintf(STDERR_FILENO, "[present-fx] m5-turbo async present offload ON (MADEIRA_PFX_ASYNC=1)\n");
  }
  return g_pfx_async_on;
}
static dispatch_queue_t madeira_pfx_async_queue(void) {
  dispatch_once(&g_pfx_async_once, ^{
    dispatch_queue_attr_t attr = dispatch_queue_attr_make_with_qos_class(DISPATCH_QUEUE_SERIAL, QOS_CLASS_USER_INTERACTIVE, 0);
    g_pfx_async_q = dispatch_queue_create("com.madeira.pfx.present", attr);
  });
  return g_pfx_async_q;
}
static void madeira_pfx_run_present(id<MTLCommandQueue> q, MadeiraPFXDrawable *px, CAMetalLayer *layer_keep) {
  unsigned long long n;
  @autoreleasepool {
    id<MTLCommandBuffer> out = q ? [q commandBuffer] : nil;
    if (out && px->_mode == 1) {
      id<CAMetalDrawable> d = madeira_pfx_resolve(out, px);
      if (d) {
        madeira_log_present_cadence("presentDrawableAfterMinDuration", px->_after);
        [out presentDrawable:d afterMinimumDuration:px->_after];
      }
      madeira_pfx_commit(out);
    } else if (out) {
      struct unixcall_generic_obj_obj_noret p;
      memset(&p, 0, sizeof p);
      p.handle = (obj_handle_t)out;
      p.arg = (obj_handle_t)px;
      g_pfx_tls.deferred = 1;
      g_pfx_tls.committed = 0;
      _MTLCommandBuffer_presentDrawable(&p);
      g_pfx_tls.deferred = 0;
      if (!g_pfx_tls.committed) madeira_pfx_commit(out);
    }
  }
  madeira_pfx_slot_free(px);
  [px release];
  [q release];
  if (layer_keep) dispatch_async(dispatch_get_main_queue(), ^{ [layer_keep release]; });
  n = atomic_fetch_add_explicit(&g_pfx_frames, 1, memory_order_relaxed) + 1;
  if (n == 1 || (n % 1800) == 0)
    dprintf(STDERR_FILENO, "[present-fx] madeira-bcd %llu frames: %llu enlarged by MetalFX, %llu copied, %llu bilinear, %llu dropped "
                           "(generated frames included)\n", n, atomic_load_explicit(&g_pfx_scaled, memory_order_relaxed),
            atomic_load_explicit(&g_pfx_copied, memory_order_relaxed), atomic_load_explicit(&g_pfx_bilinear, memory_order_relaxed),
            atomic_load_explicit(&g_pfx_dropped, memory_order_relaxed));
}
static void madeira_pfx_after_commit(id<MTLCommandBuffer> cb) {
  MadeiraPFXDrawable *px = objc_getAssociatedObject(cb, &g_pfx_key);
  id<MTLCommandQueue> q;
  if (!px) return;
  [px retain];
  objc_setAssociatedObject(cb, &g_pfx_key, nil, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
  if (px->_pending) {
    px->_pending = 0;
    atomic_fetch_sub_explicit(&g_pfx_pending, 1, memory_order_relaxed);
  }
''' + vti + r'''  q = [cb.commandQueue retain];
  if (madeira_pfx_async_enabled() && q) {
    CAMetalLayer *layer_keep = nil;
    if (px->_entry) {
      @autoreleasepool {
        CAMetalLayer *tmp_layer = (CAMetalLayer *)objc_loadWeak(&px->_entry->weak);
        if (tmp_layer) layer_keep = [tmp_layer retain];
      }
      if (!layer_keep) {
        madeira_pfx_slot_free(px);
        [px release];
        [q release];
        return;
      }
    }
    dispatch_async(madeira_pfx_async_queue(), ^{
      madeira_pfx_run_present(q, px, layer_keep);
    });
    return;
  }
  madeira_pfx_run_present(q, px, nil);
}'''


def main():
    if not PATH.exists():
        print(f"::error::{PATH} not found (run from the repository root)")
        return 1
    s = PATH.read_text()
    if MARKER in s:
        print("patch-winemetal-m5-turbo: already patched")
        return 0
    pairs = []
    if "static const char *g_fg_msl =" in s:
        pairs.append(("g_fg_msl", A_FG_MSL, NEW_FG_MSL))
        pairs.append(("fg_flow dispatch", A_FLOW_DISPATCH, NEW_FLOW_DISPATCH))
    if "madeira-bcd: present-fx" in s:
        pairs.append(("MADEIRA_PFX_PICTURES", A_PFX_PICS, NEW_PFX_PICS))
        if A_PFX_AFTER_VTI in s:
            pairs.append(("madeira_pfx_after_commit", A_PFX_AFTER_VTI, make_new_pfx_after(True)))
        else:
            pairs.append(("madeira_pfx_after_commit", A_PFX_AFTER, make_new_pfx_after(False)))
    if not pairs:
        print("patch-winemetal-m5-turbo: older dxmt tree without framegen/present-fx; nothing to do")
        return 0
    for name, old, _ in pairs:
        if s.count(old) != 1:
            print(f"::error::patch-winemetal-m5-turbo: anchor '{name}' found {s.count(old)} times (want 1) in {PATH}")
            return 1
    for _, old, new in pairs:
        s = s.replace(old, new, 1)
    PATH.write_text(s)
    print("patch-winemetal-m5-turbo: patched (" + ", ".join(n for n, _, _ in pairs) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
