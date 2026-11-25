/* SPDX-License-Identifier: GPL-3.0-only */
/* madeira-m5 0.1.717 x64-leaf (0.1.718 Phase B, 0.1.723 Phase C, 0.1.728 Phase D: 32 leaves):
 * the pure x86-64 half of madeira_d3d12.dll (see madeira_x64_leaf.h).
 *
 * Compiled with x86_64-w64-mingw32-clang -c -O2 -Wall -fno-builtin -ffreestanding and linked into
 * the ARM64EC DLL by tools/build-madeira-d3d12-dll.sh. Every function here lives in the ".x64leaf"
 * section, which LLD places on pages of its own and classifies X64 in the ARM64EC code map, so FEX
 * executes it as translated x64 and never exits the JIT for it. The ARM64EC side installs these
 * addresses (through mad_x64_graphics_entry_pe, so the slot names the PE view) in the COM vtables
 * only with bcd.cfg x64-leaf = 1.
 *
 * Rules every leaf keeps, and tests/host/check-x64-leaf.py verifies on the linked DLL:
 *   - it reads and writes fields of the object it was called on, and its arguments; no image
 *     global, no lock, no allocation, no call (the only code reached outside the section is the
 *     ARM64EC fallback, by a tail jump);
 *   - the fast path is taken only when the object's x64_flags say so and every bound holds;
 *     anything else jumps to the ARM64EC body with the arguments untouched, so the slow path is
 *     exactly the code that ran before;
 *   - helpers are always_inline, so no x64 code lands in .text. */
#include <windows.h>
#include <d3d12.h>
#include <stdint.h>
#include <stddef.h>
#include "madeira_x64_leaf.h"

#if !defined(__x86_64__) || defined(__arm64ec__)
#error "madeira_x64_leaf.c is the pure x86-64 half of the DLL: compile it with x86_64-w64-mingw32-clang"
#endif

#define MAD_X64L_LEAF __attribute__((section(".x64leaf"), noinline))
#define MAD_X64L_TAIL __attribute__((musttail))
#define MAD_X64L_INLINE static inline __attribute__((always_inline))

/* The ARM64EC fallbacks (madeira_d3d12.c, external linkage), named by their "#" bodies: the jump
 * lands on the ARM64EC code, and FEX takes the entry thunk whose offset sits in the word before it. */
void STDMETHODCALLTYPE mad_ecfb_device_CopyDescriptorsSimple(ID3D12Device *This, UINT n, D3D12_CPU_DESCRIPTOR_HANDLE dst,
                                                            D3D12_CPU_DESCRIPTOR_HANDLE src, D3D12_DESCRIPTOR_HEAP_TYPE type)
    __asm__("#mad_ecfb_device_CopyDescriptorsSimple");
void STDMETHODCALLTYPE mad_ecfb_device_CreateConstantBufferView(ID3D12Device *This, const D3D12_CONSTANT_BUFFER_VIEW_DESC *desc,
                                                               D3D12_CPU_DESCRIPTOR_HANDLE h)
    __asm__("#mad_ecfb_device_CreateConstantBufferView");
void STDMETHODCALLTYPE mad_ecfb_list_SetGraphicsRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h)
    __asm__("#mad_ecfb_list_SetGraphicsRootDescriptorTable");
void STDMETHODCALLTYPE mad_ecfb_list_SetComputeRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h)
    __asm__("#mad_ecfb_list_SetComputeRootDescriptorTable");
void STDMETHODCALLTYPE mad_ecfb_list_DrawInstanced(ID3D12GraphicsCommandList *This, UINT vcount, UINT icount, UINT vstart, UINT istart)
    __asm__("#mad_ecfb_list_DrawInstanced");
void STDMETHODCALLTYPE mad_ecfb_list_DrawIndexedInstanced(ID3D12GraphicsCommandList *This, UINT icount, UINT inst, UINT start, INT base, UINT istart)
    __asm__("#mad_ecfb_list_DrawIndexedInstanced");
void STDMETHODCALLTYPE mad_ecfb_list_SetPipelineState(ID3D12GraphicsCommandList *This, ID3D12PipelineState *pso)
    __asm__("#mad_ecfb_list_SetPipelineState");
/* 0.1.718 Phase B */
void STDMETHODCALLTYPE mad_ecfb_list_SetGraphicsRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs)
    __asm__("#mad_ecfb_list_SetGraphicsRootSignature");
void STDMETHODCALLTYPE mad_ecfb_list_SetComputeRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs)
    __asm__("#mad_ecfb_list_SetComputeRootSignature");
void STDMETHODCALLTYPE mad_ecfb_list_RSSetViewports(ID3D12GraphicsCommandList *This, UINT n, const D3D12_VIEWPORT *vp)
    __asm__("#mad_ecfb_list_RSSetViewports");
void STDMETHODCALLTYPE mad_ecfb_list_RSSetScissorRects(ID3D12GraphicsCommandList *This, UINT n, const D3D12_RECT *r)
    __asm__("#mad_ecfb_list_RSSetScissorRects");
void STDMETHODCALLTYPE mad_ecfb_list_IASetPrimitiveTopology(ID3D12GraphicsCommandList *This, D3D12_PRIMITIVE_TOPOLOGY t)
    __asm__("#mad_ecfb_list_IASetPrimitiveTopology");
void STDMETHODCALLTYPE mad_ecfb_list_OMSetStencilRef(ID3D12GraphicsCommandList *This, UINT ref)
    __asm__("#mad_ecfb_list_OMSetStencilRef");
void STDMETHODCALLTYPE mad_ecfb_list_OMSetBlendFactor(ID3D12GraphicsCommandList *This, const FLOAT f[4])
    __asm__("#mad_ecfb_list_OMSetBlendFactor");
void STDMETHODCALLTYPE mad_ecfb_list_Dispatch(ID3D12GraphicsCommandList *This, UINT x, UINT y, UINT z)
    __asm__("#mad_ecfb_list_Dispatch");
/* 0.1.723 Phase C */
void STDMETHODCALLTYPE mad_ecfb_list_IASetIndexBuffer(ID3D12GraphicsCommandList *This, const D3D12_INDEX_BUFFER_VIEW *view)
    __asm__("#mad_ecfb_list_IASetIndexBuffer");
void STDMETHODCALLTYPE mad_ecfb_list_IASetVertexBuffers(ID3D12GraphicsCommandList *This, UINT start, UINT n, const D3D12_VERTEX_BUFFER_VIEW *views)
    __asm__("#mad_ecfb_list_IASetVertexBuffers");
/* 0.1.728 Phase D */
UINT64 STDMETHODCALLTYPE mad_ecfb_fence_GetCompletedValue(ID3D12Fence *This)
    __asm__("#mad_ecfb_fence_GetCompletedValue");
HRESULT STDMETHODCALLTYPE mad_ecfb_alloc_Reset(ID3D12CommandAllocator *This)
    __asm__("#mad_ecfb_alloc_Reset");
HRESULT STDMETHODCALLTYPE mad_ecfb_list_Close(ID3D12GraphicsCommandList *This)
    __asm__("#mad_ecfb_list_Close");
HRESULT STDMETHODCALLTYPE mad_ecfb_list_Reset(ID3D12GraphicsCommandList *This, ID3D12CommandAllocator *allocator, ID3D12PipelineState *pso)
    __asm__("#mad_ecfb_list_Reset");
void STDMETHODCALLTYPE mad_ecfb_list_SetDescriptorHeaps(ID3D12GraphicsCommandList *This, UINT n, ID3D12DescriptorHeap *const *heaps)
    __asm__("#mad_ecfb_list_SetDescriptorHeaps");
void STDMETHODCALLTYPE mad_ecfb_list_OMSetRenderTargets(ID3D12GraphicsCommandList *This, UINT n, const D3D12_CPU_DESCRIPTOR_HANDLE *rtvs, BOOL single, const D3D12_CPU_DESCRIPTOR_HANDLE *dsv)
    __asm__("#mad_ecfb_list_OMSetRenderTargets");
void STDMETHODCALLTYPE mad_ecfb_list_CopyBufferRegion(ID3D12GraphicsCommandList *This, ID3D12Resource *dst, UINT64 dst_off, ID3D12Resource *src, UINT64 src_off, UINT64 len)
    __asm__("#mad_ecfb_list_CopyBufferRegion");
HRESULT STDMETHODCALLTYPE mad_ecfb_res_Map(ID3D12Resource *This, UINT sub, const D3D12_RANGE *read_range, void **data)
    __asm__("#mad_ecfb_res_Map");

_Static_assert(sizeof(D3D12_RESOURCE_DESC) % 8 == 0, "D3D12_RESOURCE_DESC is copied in 8-byte words");
_Static_assert(sizeof(D3D12_HEAP_DESC) % 8 == 0, "D3D12_HEAP_DESC is copied in 8-byte words");

/* Plain word loops: -fno-builtin keeps the compiler from turning them into memcpy/memset calls. */
MAD_X64L_INLINE void mad_x64l_copy_words(uint64_t *to, const uint64_t *from, size_t nwords) {
    size_t i;
    for (i = 0; i < nwords; i++) to[i] = from[i];
}
MAD_X64L_INLINE void mad_x64l_copy_words32(uint32_t *to, const uint32_t *from, size_t nwords) {   /* 0.1.718: 4-byte-aligned structs (viewport, rect, blend) */
    size_t i;
    for (i = 0; i < nwords; i++) to[i] = from[i];
}
/* 0.1.728 Phase D: inline memory-ordering and atomic helpers (no external calls, FEX_TSOENABLED=0 safe). */
MAD_X64L_INLINE void mad_x64l_acq_fence(void) {
    __asm__ __volatile__("lfence" ::: "memory");
}
MAD_X64L_INLINE int32_t mad_x64l_load_i32(const volatile int32_t *p) {
    return *p;
}
MAD_X64L_INLINE uint64_t mad_x64l_load_u64(const volatile uint64_t *p) {
    return *p;
}
MAD_X64L_INLINE void mad_x64l_atomic_inc(volatile int32_t *p) {
    __sync_fetch_and_add(p, 1);
}
MAD_X64L_INLINE void mad_x64l_atomic_dec(volatile int32_t *p) {
    __sync_fetch_and_sub(p, 1);
}
/* mad_list_push's fast half (0.1.728: active-field-only push -- each leaf initializes every field its replay
 * case reads instead of zeroing all 160 bytes per command, cutting recording store traffic by ~75%). */
MAD_X64L_INLINE int mad_x64l_push(struct mad_x64l_list *l, int kind, struct mad_x64l_cmd **c) {
    *c = NULL;
    if (!(l->x64_flags & MAD_X64L_OK) || l->ncmds >= l->ccap) return 0;
    if (l->closed) return 1;
    *c = &l->cmds[l->ncmds++];
    (*c)->kind = kind;
    return 1;
}
MAD_X64L_INLINE UINT mad_x64l_stride(D3D12_DESCRIPTOR_HEAP_TYPE type) {   /* mad_descriptor_stride */
    return type == D3D12_DESCRIPTOR_HEAP_TYPE_RTV || type == D3D12_DESCRIPTOR_HEAP_TYPE_DSV ? MAD_X64L_RTV_SIZE : MAD_X64L_DESC_SIZE;
}

/* ---- pure field reads / writes: no slow path, no fallback --------------------------------- */
MAD_X64L_LEAF D3D12_GPU_VIRTUAL_ADDRESS STDMETHODCALLTYPE mad_x64l_res_GetGPUVirtualAddress(ID3D12Resource *This) {
    return (D3D12_GPU_VIRTUAL_ADDRESS)((const struct mad_x64l_resource *)This)->gpu_address;
}
MAD_X64L_LEAF D3D12_RESOURCE_DESC * STDMETHODCALLTYPE mad_x64l_res_GetDesc(ID3D12Resource *This, D3D12_RESOURCE_DESC *ret) {
    mad_x64l_copy_words((uint64_t *)ret, (const uint64_t *)&((const struct mad_x64l_resource *)This)->desc, sizeof(D3D12_RESOURCE_DESC) / 8);
    return ret;
}
MAD_X64L_LEAF D3D12_HEAP_DESC * STDMETHODCALLTYPE mad_x64l_memheap_GetDesc(ID3D12Heap *This, D3D12_HEAP_DESC *ret) {
    mad_x64l_copy_words((uint64_t *)ret, (const uint64_t *)&((const struct mad_x64l_memheap *)This)->desc, sizeof(D3D12_HEAP_DESC) / 8);
    return ret;
}
MAD_X64L_LEAF D3D12_CPU_DESCRIPTOR_HANDLE * STDMETHODCALLTYPE
mad_x64l_heap_GetCPUDescriptorHandleForHeapStart(ID3D12DescriptorHeap *This, D3D12_CPU_DESCRIPTOR_HANDLE *out) {
    const struct mad_x64l_heap *h = (const struct mad_x64l_heap *)This;
    if (out) out->ptr = h->cpu ? (SIZE_T)(uintptr_t)h->cpu : (SIZE_T)(uintptr_t)h->slots;
    return out;
}
MAD_X64L_LEAF D3D12_GPU_DESCRIPTOR_HANDLE * STDMETHODCALLTYPE
mad_x64l_heap_GetGPUDescriptorHandleForHeapStart(ID3D12DescriptorHeap *This, D3D12_GPU_DESCRIPTOR_HANDLE *out) {
    if (out) out->ptr = ((const struct mad_x64l_heap *)This)->gpu_address;
    return out;
}
MAD_X64L_LEAF UINT STDMETHODCALLTYPE mad_x64l_device_GetDescriptorHandleIncrementSize(ID3D12Device *This, D3D12_DESCRIPTOR_HEAP_TYPE type) {
    (void)This;
    return mad_x64l_stride(type);
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_res_Unmap(ID3D12Resource *This, UINT sub, const D3D12_RANGE *written) {
    struct mad_x64l_resource *r = (struct mad_x64l_resource *)This;
    (void)sub; (void)written;
    if (mad_x64l_load_i32(&r->mapped)) mad_x64l_atomic_dec(&r->mapped);
}

/* ---- device: descriptor writes (desc-guard and view-census are off when x64_flags is set) ---- */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_device_CopyDescriptorsSimple(ID3D12Device *This, UINT n, D3D12_CPU_DESCRIPTOR_HANDLE dst,
                                                                          D3D12_CPU_DESCRIPTOR_HANDLE src, D3D12_DESCRIPTOR_HEAP_TYPE type) {
    const struct mad_x64l_device *d = (const struct mad_x64l_device *)This;
    uint64_t *to; const uint64_t *from; size_t q, i;
    if (!d || !(d->x64_flags & MAD_X64L_OK)) { MAD_X64L_TAIL return mad_ecfb_device_CopyDescriptorsSimple(This, n, dst, src, type); }
    if (!n || !dst.ptr || !src.ptr) return;
    q = (size_t)n * mad_x64l_stride(type) / 8;   /* both strides are multiples of 8 */
    to = (uint64_t *)(uintptr_t)dst.ptr; from = (const uint64_t *)(uintptr_t)src.ptr;
    if (to == from) return;
    if (to < from || to >= from + q) { for (i = 0; i < q; i++) to[i] = from[i]; }   /* memmove: forward when safe */
    else { for (i = q; i-- > 0;) to[i] = from[i]; }                                  /* else backward */
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_device_CreateConstantBufferView(ID3D12Device *This, const D3D12_CONSTANT_BUFFER_VIEW_DESC *desc,
                                                                             D3D12_CPU_DESCRIPTOR_HANDLE h) {
    const struct mad_x64l_device *d = (const struct mad_x64l_device *)This;
    struct mad_x64l_desc *e = (struct mad_x64l_desc *)(uintptr_t)h.ptr;
    /* a null view reads the device's null buffer: the ARM64EC body knows where that is */
    if (!d || !(d->x64_flags & MAD_X64L_OK) || !desc || !desc->BufferLocation) { MAD_X64L_TAIL return mad_ecfb_device_CreateConstantBufferView(This, desc, h); }
    if (!e) return;
    e->gpu_va = desc->BufferLocation;   /* mad_set_buffer_descriptor */
    e->texture_view_id = 0;
    e->metadata = desc->SizeInBytes & 0xffffffffu;
}

/* ---- command list: one appended command each (static-cbv is off when x64_flags is set) ------ */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_SetGraphicsRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (index >= MAD_X64L_ROOT_PARAM_MAX || !mad_x64l_push(l, MAD_X64L_MC_ROOT, &c)) { MAD_X64L_TAIL return mad_ecfb_list_SetGraphicsRootDescriptorTable(This, index, h); }
    if (c) { c->u.root.index = index; c->u.root.value = h.ptr; }   /* mad_record_root(l, index, h.ptr, 0) */
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_SetComputeRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (index >= MAD_X64L_ROOT_PARAM_MAX || !mad_x64l_push(l, MAD_X64L_MC_CROOT, &c)) { MAD_X64L_TAIL return mad_ecfb_list_SetComputeRootDescriptorTable(This, index, h); }
    if (c) { c->u.root.index = index; c->u.root.value = h.ptr; }   /* mad_record_croot(l, index, h.ptr, 0) */
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_DrawInstanced(ID3D12GraphicsCommandList *This, UINT vcount, UINT icount, UINT vstart, UINT istart) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_DRAW, &c)) { MAD_X64L_TAIL return mad_ecfb_list_DrawInstanced(This, vcount, icount, vstart, istart); }
    if (c) { c->u.draw.vcount = vcount; c->u.draw.icount = icount; c->u.draw.vstart = vstart; c->u.draw.istart = istart; }
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_DrawIndexedInstanced(ID3D12GraphicsCommandList *This, UINT icount, UINT inst, UINT start, INT base, UINT istart) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_DRAW_INDEXED, &c)) { MAD_X64L_TAIL return mad_ecfb_list_DrawIndexedInstanced(This, icount, inst, start, base, istart); }
    if (c) { c->u.drawi.icount = icount; c->u.drawi.inst = inst; c->u.drawi.start = start; c->u.drawi.base = base; c->u.drawi.istart = istart; }
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_SetPipelineState(ID3D12GraphicsCommandList *This, ID3D12PipelineState *pso) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_PSO, &c)) { MAD_X64L_TAIL return mad_ecfb_list_SetPipelineState(This, pso); }
    if (c) {
        c->u.pso = pso;
        if (pso) {
            const struct mad_x64l_pso *p = (const struct mad_x64l_pso *)pso;
            if (!p->rps && !p->cps) l->has_lazy_pso = 1;
        }
    }
}

/* ---- 0.1.718 Phase B: the trivial batch (Round 4 report, section 5.1 rank 2). Each ARM64EC body is one push and one
 * field; the static-cbv branches of the root-signature setters and Dispatch are dead while the leaves are installed
 * (mad_x64_leaf_init vetoes the install when static-cbv is on, and g_scbv_on never changes afterwards). ------------- */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_SetGraphicsRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_ROOTSIG, &c)) { MAD_X64L_TAIL return mad_ecfb_list_SetGraphicsRootSignature(This, rs); }
    if (c) c->u.rootsig = rs;
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_SetComputeRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_CROOTSIG, &c)) { MAD_X64L_TAIL return mad_ecfb_list_SetComputeRootSignature(This, rs); }
    if (c) c->u.rootsig = rs;
}
/* list_RSSetViewports / list_RSSetScissorRects record nothing for n == 0 or a NULL array (before the push, so no
 * transition either way); only the first entry is kept. */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_RSSetViewports(ID3D12GraphicsCommandList *This, UINT n, const D3D12_VIEWPORT *vp) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!n || !vp) return;
    if (!mad_x64l_push(l, MAD_X64L_MC_VP, &c)) { MAD_X64L_TAIL return mad_ecfb_list_RSSetViewports(This, n, vp); }
    if (c) mad_x64l_copy_words32((uint32_t *)&c->u.vp, (const uint32_t *)vp, sizeof(D3D12_VIEWPORT) / 4);
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_RSSetScissorRects(ID3D12GraphicsCommandList *This, UINT n, const D3D12_RECT *r) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!n || !r) return;
    if (!mad_x64l_push(l, MAD_X64L_MC_SCISSOR, &c)) { MAD_X64L_TAIL return mad_ecfb_list_RSSetScissorRects(This, n, r); }
    if (c) mad_x64l_copy_words32((uint32_t *)&c->u.scissor, (const uint32_t *)r, sizeof(D3D12_RECT) / 4);
}
/* The ARM64EC body logs once for an adjacency or patch topology (t >= MAD_X64L_TOPO_FALLBACK): those take the slow path. */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_IASetPrimitiveTopology(ID3D12GraphicsCommandList *This, D3D12_PRIMITIVE_TOPOLOGY t) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if ((unsigned)t >= MAD_X64L_TOPO_FALLBACK || !mad_x64l_push(l, MAD_X64L_MC_TOPO, &c)) { MAD_X64L_TAIL return mad_ecfb_list_IASetPrimitiveTopology(This, t); }
    if (c) c->u.topo = t;
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_OMSetStencilRef(ID3D12GraphicsCommandList *This, UINT ref) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_STENCIL_REF, &c)) { MAD_X64L_TAIL return mad_ecfb_list_OMSetStencilRef(This, ref); }
    if (c) c->u.stencil_ref = ref;
}
/* list_OMSetBlendFactor: a NULL factor means 1, 1, 1, 1. */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_OMSetBlendFactor(ID3D12GraphicsCommandList *This, const FLOAT f[4]) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_BLEND_FACTOR, &c)) { MAD_X64L_TAIL return mad_ecfb_list_OMSetBlendFactor(This, f); }
    if (c) {
        if (f) mad_x64l_copy_words32((uint32_t *)c->u.blend.rgba, (const uint32_t *)f, 4);
        else { c->u.blend.rgba[0] = c->u.blend.rgba[1] = c->u.blend.rgba[2] = c->u.blend.rgba[3] = 1.0f; }
    }
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_Dispatch(ID3D12GraphicsCommandList *This, UINT x, UINT y, UINT z) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_DISPATCH, &c)) { MAD_X64L_TAIL return mad_ecfb_list_Dispatch(This, x, y, z); }
    if (c) { c->u.dispatch.x = x; c->u.dispatch.y = y; c->u.dispatch.z = z; }
}

/* ---- 0.1.723 Phase C: deferred-VA index/vertex buffer setters (42.8k x64->EC calls/s in HFW).
 * Store the GPU VA in the command and resolve it on the ARM64EC replay worker (as MC_ROOT already
 * does), so record-time calls never leave FEX. ------------------------------------------------- */
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_IASetIndexBuffer(ID3D12GraphicsCommandList *This, const D3D12_INDEX_BUFFER_VIEW *view) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    if (!mad_x64l_push(l, MAD_X64L_MC_IB, &c)) { MAD_X64L_TAIL return mad_ecfb_list_IASetIndexBuffer(This, view); }
    if (c) {
        c->u.ib.res = NULL;
        c->u.ib.off = 0;
        if (view) {
            c->u.ib.gpu_va = view->BufferLocation;
            c->u.ib.type = view->Format == DXGI_FORMAT_R32_UINT ? MAD_X64L_IB_U32 : MAD_X64L_IB_U16;
        } else {
            c->u.ib.gpu_va = 0;
            c->u.ib.type = MAD_X64L_IB_U16;
        }
    }
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_IASetVertexBuffers(ID3D12GraphicsCommandList *This, UINT start, UINT n,
                                                                      const D3D12_VERTEX_BUFFER_VIEW *views) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    UINT i;
    if (!n) return;
    if (!(l->x64_flags & MAD_X64L_OK) || n > 16 || (uint64_t)l->ncmds + n > (uint64_t)l->ccap) { MAD_X64L_TAIL return mad_ecfb_list_IASetVertexBuffers(This, start, n, views); }
    if (l->closed) return;
    for (i = 0; i < n; i++) {
        struct mad_x64l_cmd *c = &l->cmds[l->ncmds++];
        c->kind = MAD_X64L_MC_VB;
        c->u.vb.slot = start + i;
        c->u.vb.res = NULL;
        c->u.vb.off = 0;
        if (views && views[i].BufferLocation) {
            c->u.vb.gpu_va = views[i].BufferLocation;
            c->u.vb.stride = views[i].StrideInBytes;
        } else {
            c->u.vb.gpu_va = 0;
            c->u.vb.stride = 0;
        }
    }
}

/* ---- 0.1.728 Phase D: fence poll, command lifecycle, heaps, render targets, buffer copy, Map --- */
MAD_X64L_LEAF UINT64 STDMETHODCALLTYPE mad_x64l_fence_GetCompletedValue(ID3D12Fence *This) {
    const struct mad_x64l_fence *f = (const struct mad_x64l_fence *)This;
    uint64_t v;
    if (!f || !(f->x64_flags & MAD_X64L_OK) || mad_x64l_load_i32(&f->ndeferred) > 0) {
        MAD_X64L_TAIL return mad_ecfb_fence_GetCompletedValue(This);
    }
    v = mad_x64l_load_u64(&f->value);
    mad_x64l_acq_fence();   /* lfence -> ARM64 dmb ld for FEX_TSOENABLED = 0 acquire ordering */
    return v;
}
MAD_X64L_LEAF HRESULT STDMETHODCALLTYPE mad_x64l_alloc_Reset(ID3D12CommandAllocator *This) {
    struct mad_x64l_alloc *a = (struct mad_x64l_alloc *)This;
    if (!a || mad_x64l_load_i32(&a->recording)) { MAD_X64L_TAIL return mad_ecfb_alloc_Reset(This); }
    mad_x64l_atomic_inc(&a->generation);
    return S_OK;
}
MAD_X64L_LEAF HRESULT STDMETHODCALLTYPE mad_x64l_list_Close(ID3D12GraphicsCommandList *This) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    if (!l || !(l->x64_flags & MAD_X64L_OK) || l->closed) { MAD_X64L_TAIL return mad_ecfb_list_Close(This); }
    l->closed = 1;
    l->recorded_generation = l->alloc ? mad_x64l_load_i32(&l->alloc->generation) : 0;
    if (l->alloc) mad_x64l_atomic_dec(&l->alloc->recording);
    return S_OK;
}
MAD_X64L_LEAF HRESULT STDMETHODCALLTYPE mad_x64l_list_Reset(ID3D12GraphicsCommandList *This,
                                                            ID3D12CommandAllocator *allocator,
                                                            ID3D12PipelineState *pso) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_alloc *a = (struct mad_x64l_alloc *)allocator;
    if (!l || !(l->x64_flags & MAD_X64L_OK) || !l->closed || !a ||
        mad_x64l_load_i32(&l->inflight) || l->alloc != a || l->nrings ||
        (l->type == D3D12_COMMAND_LIST_TYPE_BUNDLE && pso)) {
        MAD_X64L_TAIL return mad_ecfb_list_Reset(This, allocator, pso);
    }
    mad_x64l_atomic_inc(&a->recording);
    l->recorded_generation = mad_x64l_load_i32(&a->generation);
    l->closed = 0;
    l->ncmds = 0;
    l->nused = 0;
    l->ncdata = 0;
    l->has_lazy_pso = 0;
    l->ring_used = 0;
    return S_OK;
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_SetDescriptorHeaps(ID3D12GraphicsCommandList *This,
                                                                      UINT n, ID3D12DescriptorHeap *const *heaps) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    UINT i;
    if (!heaps) return;
    if (!mad_x64l_push(l, MAD_X64L_MC_HEAPS, &c)) { MAD_X64L_TAIL return mad_ecfb_list_SetDescriptorHeaps(This, n, heaps); }
    if (c) {
        c->u.heaps.srv = NULL;
        c->u.heaps.smp = NULL;
        for (i = 0; i < n; i++) {
            struct mad_x64l_heap *h = (struct mad_x64l_heap *)heaps[i];
            if (!h || !h->buffer) continue;
            if (h->type == D3D12_DESCRIPTOR_HEAP_TYPE_SAMPLER) c->u.heaps.smp = h; else c->u.heaps.srv = h;
        }
    }
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_OMSetRenderTargets(ID3D12GraphicsCommandList *This, UINT n,
                                                                      const D3D12_CPU_DESCRIPTOR_HANDLE *rtvs,
                                                                      BOOL single, const D3D12_CPU_DESCRIPTOR_HANDLE *dsv) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    UINT i, lim;
    if (!mad_x64l_push(l, MAD_X64L_MC_RTS, &c)) { MAD_X64L_TAIL return mad_ecfb_list_OMSetRenderTargets(This, n, rtvs, single, dsv); }
    if (c) {
        lim = n > 8 ? 8 : n;
        for (i = 0; i < lim && rtvs; i++) {
            SIZE_T h = single ? rtvs[0].ptr + (SIZE_T)i * MAD_X64L_RTV_SIZE : rtvs[i].ptr;
            if (h) {
                const struct mad_x64l_rtv *slot = (const struct mad_x64l_rtv *)(uintptr_t)h;
                c->u.rts.rt[i] = slot->res;
                c->u.rts.v[i] = slot->p;
            } else {
                c->u.rts.rt[i] = NULL;
                c->u.rts.v[i].level = 0; c->u.rts.v[i].slice = 0; c->u.rts.v[i].layers = 1; c->u.rts.v[i].plane = 0;
            }
        }
        for (; i < 8; i++) {
            c->u.rts.rt[i] = NULL;
            c->u.rts.v[i].level = 0; c->u.rts.v[i].slice = 0; c->u.rts.v[i].layers = 1; c->u.rts.v[i].plane = 0;
        }
        c->u.rts.n = rtvs ? lim : 0;
        if (dsv && dsv->ptr) {
            const struct mad_x64l_rtv *slot = (const struct mad_x64l_rtv *)(uintptr_t)dsv->ptr;
            c->u.rts.depth = slot->res;
            c->u.rts.dv = slot->p;
        } else {
            c->u.rts.depth = NULL;
            c->u.rts.dv.level = 0; c->u.rts.dv.slice = 0; c->u.rts.dv.layers = 1; c->u.rts.dv.plane = 0;
        }
    }
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_CopyBufferRegion(ID3D12GraphicsCommandList *This,
                                                                    ID3D12Resource *dst, UINT64 dst_off,
                                                                    ID3D12Resource *src, UINT64 src_off, UINT64 len) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    const struct mad_x64l_resource *d = (const struct mad_x64l_resource *)dst;
    const struct mad_x64l_resource *s = (const struct mad_x64l_resource *)src;
    struct mad_x64l_cmd *c;
    if (!d || !s || !len) return;
    if (dst_off > d->size || len > d->size - dst_off || src_off > s->size || len > s->size - src_off ||
        !mad_x64l_push(l, MAD_X64L_MC_COPY_BB, &c)) {
        MAD_X64L_TAIL return mad_ecfb_list_CopyBufferRegion(This, dst, dst_off, src, src_off, len);
    }
    if (c) {
        c->u.bb.dst = dst;
        c->u.bb.src = src;
        c->u.bb.doff = dst_off;
        c->u.bb.soff = src_off;
        c->u.bb.len = len;
    }
}
MAD_X64L_LEAF HRESULT STDMETHODCALLTYPE mad_x64l_res_Map(ID3D12Resource *This, UINT sub,
                                                         const D3D12_RANGE *read_range, void **data) {
    struct mad_x64l_resource *r = (struct mad_x64l_resource *)This;
    if (!r || sub != 0 || !r->cpu) { MAD_X64L_TAIL return mad_ecfb_res_Map(This, sub, read_range, data); }
    mad_x64l_atomic_inc(&r->mapped);
    if (data) *data = r->cpu;
    return S_OK;
}
