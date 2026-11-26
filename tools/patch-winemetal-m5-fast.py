#!/usr/bin/env python3
"""M5 fast path for madeira-d3d12: unretained command buffers (MadeiraCtl op 25)
and inline compute encoder memoryBarrierWithScope: (command type 12, probe op 26).

1. MadeiraCtl op 25 (cb-unretained = 1):
   Creates a Metal command buffer via [queue commandBufferWithUnretainedReferences]
   when a->ptr != 0 (returning handle in a->len, a->ret = 1), or probes support
   when a->ptr == 0 (a->ret = 1 in local mode). Avoids Apple IOGPU per-resource
   retain/release/dedup tables inside IOGPUCommandQueueSubmitCommandBuffers while
   madeira-d3d12 guarantees GPU-lifetime retention for all bound objects.

2. Compute command type 12 (MAD_WMT_COMPUTE_MEM_BARRIER, cs-barrier-keep = 1)
   and MadeiraCtl op 26 probe:
   Encodes [encoder memoryBarrierWithScope:(MTLBarrierScope)scope] inline inside
   an open MTLComputeCommandEncoder so UAV/buffer/texture barriers no longer
   require closing and reopening the compute encoder with a full MTLFence drain.

Local mode only (wmtr_enabled() leaves ret = 0). Idempotent; fails by name if
any anchor moves or cases 25/26/12 are already taken. Run from the repo root.
"""
import pathlib
import re
import sys

PATH = pathlib.Path("dxmt/src/winemetal/unix/winemetal_unix.c")
MARKER = "madeira-bcd: m5 fast path (unretained CB + compute memoryBarrier)"

ANCHOR_SIZE_FN = "static uint32_t wmt_compute_cmd_size(unsigned type, const struct wmtcmd_base *c, uint32_t *inline_len) {\n"
STRUCT_DECL = r'''/* madeira-bcd: m5 fast path (unretained CB + compute memoryBarrier) (tools/patch-winemetal-m5-fast.py).
 * Compute command 12: inline [encoder memoryBarrierWithScope:(MTLBarrierScope)scope]
 * inside an open compute encoder. */
#define MAD_WMT_COMPUTE_MEM_BARRIER 12u
struct mad_wmtcmd_compute_mem_barrier {
  enum WMTComputeCommandType type;
  uint16_t reserved[3];
  struct WMTMemoryPointer next;
  uint64_t scope;
};

'''

ANCHOR_SIZE_CASE = "  case WMTComputeCommandUpdateFence:       return sizeof(struct wmtcmd_compute_fence_op);\n"
ADD_SIZE_CASE = "  case MAD_WMT_COMPUTE_MEM_BARRIER:        return sizeof(struct mad_wmtcmd_compute_mem_barrier);\n"

ANCHOR_ENC_SWITCH = "    switch ((enum WMTComputeCommandType)next->type) {\n"
REPL_ENC_SWITCH = "    switch ((unsigned)next->type) {\n"

ANCHOR_ENC_CASE = """    case WMTComputeCommandWaitForFence: {
      struct wmtcmd_compute_fence_op *body = (struct wmtcmd_compute_fence_op *)next;
      [encoder waitForFence:(id<MTLFence>)body->fence];
      break;
    }
"""
ADD_ENC_CASE = """    case MAD_WMT_COMPUTE_MEM_BARRIER: {
      struct mad_wmtcmd_compute_mem_barrier *body = (struct mad_wmtcmd_compute_mem_barrier *)next;
      [encoder memoryBarrierWithScope:(MTLBarrierScope)body->scope];
      break;
    }
"""

ANCHOR_CTL_FN = "static NTSTATUS _madeira_ctl(void *args) {\n"
ANCHOR_CTL_END = "  default: break;\n  }\n  return STATUS_SUCCESS;\n}\n"
CTL_CASES = """  case 25: {  /* madeira-bcd: m5 fast path (unretained CB, tools/patch-winemetal-m5-fast.py) */
    id<MTLCommandBuffer> cb;
    if (wmtr_enabled()) break;
    if (!a->ptr) { a->ret = 1u; break; }
    cb = [(id<MTLCommandQueue>)(uintptr_t)a->ptr commandBufferWithUnretainedReferences];
    a->len = (uint64_t)(uintptr_t)cb;
    a->ret = cb ? 1u : 0u;
    break;
  }
  case 26:    /* madeira-bcd: m5 fast path (compute memoryBarrier probe) */
    if (!wmtr_enabled()) a->ret = 1u;
    break;
"""


def main():
    src = PATH.read_text()
    if MARKER in src:
        print("patch-winemetal-m5-fast: already patched")
        return 0
    for name, anchor in [
        ("wmt_compute_cmd_size", ANCHOR_SIZE_FN),
        ("wmt_compute_cmd_size UpdateFence", ANCHOR_SIZE_CASE),
        ("compute encodeCommands switch", ANCHOR_ENC_SWITCH),
        ("compute encodeCommands WaitForFence", ANCHOR_ENC_CASE),
        ("_madeira_ctl", ANCHOR_CTL_FN),
    ]:
        if src.count(anchor) != 1:
            sys.exit(f"patch-winemetal-m5-fast: anchor '{name}' not found once (count={src.count(anchor)})")

    fn_at = src.index(ANCHOR_CTL_FN)
    fn_end = src.index("\n}\n", fn_at) + 3
    ctl_body = src[fn_at:fn_end]
    if not ctl_body.endswith(ANCHOR_CTL_END):
        sys.exit("patch-winemetal-m5-fast: _madeira_ctl no longer ends with its default case")
    for op in (25, 26):
        if re.search(rf"^\s*case {op}:", ctl_body, re.M):
            sys.exit(f"patch-winemetal-m5-fast: _madeira_ctl already has case {op}")

    ctl_body = ctl_body[:-len(ANCHOR_CTL_END)] + CTL_CASES + ANCHOR_CTL_END
    src = src[:fn_at] + ctl_body + src[fn_end:]

    src = src.replace(ANCHOR_SIZE_FN, STRUCT_DECL + ANCHOR_SIZE_FN, 1)
    src = src.replace(ANCHOR_SIZE_CASE, ANCHOR_SIZE_CASE + ADD_SIZE_CASE, 1)
    src = src.replace(ANCHOR_ENC_SWITCH, REPL_ENC_SWITCH, 1)
    src = src.replace(ANCHOR_ENC_CASE, ANCHOR_ENC_CASE + ADD_ENC_CASE, 1)

    PATH.write_text(src)
    print("patch-winemetal-m5-fast: added MadeiraCtl ops 25/26 and compute memoryBarrierWithScope (cmd 12)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
