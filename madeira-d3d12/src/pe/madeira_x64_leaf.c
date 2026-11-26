/* SPDX-License-Identifier: GPL-3.0-only */
/* madeira-m5 0.1.717 x64-leaf (0.1.718 Phase B, 0.1.723 Phase C, 0.1.728 Phase D, 0.1.729 Phase E: 42 leaves):
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
/* 0.1.729 Phase E */
void STDMETHODCALLTYPE mad_ecfb_device_CreateShaderResourceView(ID3D12Device *This, ID3D12Resource *res, const D3D12_SHADER_RESOURCE_VIEW_DESC *desc, D3D12_CPU_DESCRIPTOR_HANDLE h)
    __asm__("#mad_ecfb_device_CreateShaderResourceView");
void STDMETHODCALLTYPE mad_ecfb_device_CreateSampler(ID3D12Device *This, const D3D12_SAMPLER_DESC *desc, D3D12_CPU_DESCRIPTOR_HANDLE h)
    __asm__("#mad_ecfb_device_CreateSampler");
void STDMETHODCALLTYPE mad_ecfb_list_ResourceBarrier(ID3D12GraphicsCommandList *This, UINT n, const D3D12_RESOURCE_BARRIER *b)
    __asm__("#mad_ecfb_list_ResourceBarrier");
void STDMETHODCALLTYPE mad_ecfb_list_DiscardResource(ID3D12GraphicsCommandList *This, ID3D12Resource *res, const D3D12_DISCARD_REGION *region)
    __asm__("#mad_ecfb_list_DiscardResource");
ULONG STDMETHODCALLTYPE mad_ecfb_res_Release(ID3D12Resource *This)
    __asm__("#mad_ecfb_res_Release");
ULONG STDMETHODCALLTYPE mad_ecfb_pso_Release(ID3D12PipelineState *This)
    __asm__("#mad_ecfb_pso_Release");
ULONG STDMETHODCALLTYPE mad_ecfb_memheap_Release(ID3D12Heap *This)
    __asm__("#mad_ecfb_memheap_Release");

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
MAD_X64L_INLINE ULONG mad_x64l_addref(volatile int32_t *p) {
    return (ULONG)__sync_add_and_fetch(p, 1);
}
MAD_X64L_INLINE int mad_x64l_try_release(volatile int32_t *p, ULONG *out) {
    int32_t cur = *p;
    while (cur > 1) {
        int32_t prev = __sync_val_compare_and_swap(p, cur, cur - 1);
        if (prev == cur) { *out = (ULONG)(cur - 1); return 1; }
        cur = prev;
    }
    return 0;
}
MAD_X64L_INLINE uint32_t mad_x64l_float_bits(float f) {
    union { float f; uint32_t u; } v;
    v.f = f;
    return v.u;
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
/* 0.1.729 Phase E: pure atomic COM AddRef leaves */
MAD_X64L_LEAF ULONG STDMETHODCALLTYPE mad_x64l_res_AddRef(ID3D12Resource *This) {
    return mad_x64l_addref(&((struct mad_x64l_obj *)This)->refs);
}
MAD_X64L_LEAF ULONG STDMETHODCALLTYPE mad_x64l_pso_AddRef(ID3D12PipelineState *This) {
    return mad_x64l_addref(&((struct mad_x64l_obj *)This)->refs);
}
MAD_X64L_LEAF ULONG STDMETHODCALLTYPE mad_x64l_memheap_AddRef(ID3D12Heap *This) {
    return mad_x64l_addref(&((struct mad_x64l_obj *)This)->refs);
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
/* 0.1.729: aligned(32) shifts the `jae rel32` encoding off an accidental aligned ARM64 x18_role() bit pattern */
MAD_X64L_LEAF __attribute__((aligned(32))) void STDMETHODCALLTYPE mad_x64l_list_IASetIndexBuffer(ID3D12GraphicsCommandList *This, const D3D12_INDEX_BUFFER_VIEW *view) {
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

/* ---- 0.1.728 Phase D + 0.1.729 cc=2 value-aware fence poll, lifecycle, heaps, RT, copy, Map -- */
MAD_X64L_LEAF UINT64 STDMETHODCALLTYPE mad_x64l_fence_GetCompletedValue(ID3D12Fence *This) {
    const struct mad_x64l_fence *f = (const struct mad_x64l_fence *)This;
    int32_t fl;
    uint64_t v;
    if (!f || !((fl = f->x64_flags) & MAD_X64L_OK)) goto fallback;
    if (mad_x64l_load_i32(&f->ndeferred) > 0) {
        mad_x64l_acq_fence();
        v = mad_x64l_load_u64(&f->value);
        if (!(fl & MAD_X64L_FENCE_CC2) || v >= mad_x64l_load_u64((const volatile uint64_t *)&f->committed))
            goto fallback;
        mad_x64l_acq_fence();   /* lfence -> ARM64 dmb ld for FEX_TSOENABLED = 0 acquire ordering */
        return v;
    }
    v = mad_x64l_load_u64(&f->value);
    mad_x64l_acq_fence();   /* lfence -> ARM64 dmb ld for FEX_TSOENABLED = 0 acquire ordering */
    return v;
fallback:;
    MAD_X64L_TAIL return mad_ecfb_fence_GetCompletedValue(This);
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

/* ---- 0.1.729 Phase E: Release, CreateSRV, CreateSampler, ResourceBarrier, DiscardResource -- */
MAD_X64L_LEAF ULONG STDMETHODCALLTYPE mad_x64l_res_Release(ID3D12Resource *This) {
    ULONG n;
    if (This && mad_x64l_try_release(&((struct mad_x64l_obj *)This)->refs, &n)) return n;
    MAD_X64L_TAIL return mad_ecfb_res_Release(This);
}
MAD_X64L_LEAF ULONG STDMETHODCALLTYPE mad_x64l_pso_Release(ID3D12PipelineState *This) {
    ULONG n;
    if (This && mad_x64l_try_release(&((struct mad_x64l_obj *)This)->refs, &n)) return n;
    MAD_X64L_TAIL return mad_ecfb_pso_Release(This);
}
MAD_X64L_LEAF ULONG STDMETHODCALLTYPE mad_x64l_memheap_Release(ID3D12Heap *This) {
    ULONG n;
    if (This && mad_x64l_try_release(&((struct mad_x64l_obj *)This)->refs, &n)) return n;
    MAD_X64L_TAIL return mad_ecfb_memheap_Release(This);
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_device_CreateShaderResourceView(ID3D12Device *This, ID3D12Resource *res,
                                                                              const D3D12_SHADER_RESOURCE_VIEW_DESC *desc,
                                                                              D3D12_CPU_DESCRIPTOR_HANDLE h) {
    const struct mad_x64l_device *d = (const struct mad_x64l_device *)This;
    const struct mad_x64l_resource *r = (const struct mad_x64l_resource *)res;
    struct mad_x64l_desc *e = (struct mad_x64l_desc *)(uintptr_t)h.ptr;
    int32_t dfl, rfl;
    if (!e) return;
    if (!d || !((dfl = d->x64_flags) & MAD_X64L_OK)) goto fallback;
    if (!r) { e->gpu_va = 0; e->texture_view_id = 0; e->metadata = 0; return; }
    if (r->buffer) {
        if (desc && desc->ViewDimension == D3D12_SRV_DIMENSION_BUFFER && !(dfl & MAD_X64L_DEV_RAW_TYPED) &&
            (desc->Buffer.StructureByteStride || (desc->Buffer.Flags & D3D12_BUFFER_SRV_FLAG_RAW))) {
            uint64_t stride = desc->Buffer.StructureByteStride ? (uint64_t)desc->Buffer.StructureByteStride : 4ull;
            e->gpu_va = r->gpu_address + desc->Buffer.FirstElement * stride;
            e->texture_view_id = 0;
            e->metadata = (uint64_t)desc->Buffer.NumElements * stride;
            return;
        }
        goto fallback;
    }
    if (r->texture && !r->is_depth && ((rfl = mad_x64l_load_i32(&r->x64_flags)) & MAD_X64L_RES_SRV_LISTED)) {
        if (!desc) {
            e->gpu_va = 0;
            e->texture_view_id = r->gpu_resource_id;
            e->metadata = 0;
            return;
        }
        if (desc->Shader4ComponentMapping == 0x1688u &&
            (desc->Format == DXGI_FORMAT_UNKNOWN || desc->Format == r->desc.Format)) {
            int ok = 0;
            uint32_t rmips = r->x64_mips;
            uint32_t rlayers = r->x64_layers;
            if (desc->ViewDimension == D3D12_SRV_DIMENSION_TEXTURE2D) {
                ok = (rfl & MAD_X64L_RES_TEX_2DARRAY) && rlayers == 1 &&
                     desc->Texture2D.MostDetailedMip == 0 && desc->Texture2D.PlaneSlice == 0 &&
                     (desc->Texture2D.MipLevels == 0 || desc->Texture2D.MipLevels == ~0u || desc->Texture2D.MipLevels >= rmips) &&
                     desc->Texture2D.ResourceMinLODClamp <= 0.0f;
            } else if (desc->ViewDimension == D3D12_SRV_DIMENSION_TEXTURE2DARRAY) {
                ok = (rfl & MAD_X64L_RES_TEX_2DARRAY) &&
                     desc->Texture2DArray.MostDetailedMip == 0 && desc->Texture2DArray.FirstArraySlice == 0 &&
                     desc->Texture2DArray.PlaneSlice == 0 &&
                     (desc->Texture2DArray.MipLevels == 0 || desc->Texture2DArray.MipLevels == ~0u || desc->Texture2DArray.MipLevels >= rmips) &&
                     (desc->Texture2DArray.ArraySize == 0 || desc->Texture2DArray.ArraySize == ~0u || desc->Texture2DArray.ArraySize >= rlayers) &&
                     desc->Texture2DArray.ResourceMinLODClamp <= 0.0f;
            } else if (desc->ViewDimension == D3D12_SRV_DIMENSION_TEXTURE3D) {
                ok = (rfl & MAD_X64L_RES_TEX_3D) &&
                     desc->Texture3D.MostDetailedMip == 0 &&
                     (desc->Texture3D.MipLevels == 0 || desc->Texture3D.MipLevels == ~0u || desc->Texture3D.MipLevels >= rmips) &&
                     desc->Texture3D.ResourceMinLODClamp <= 0.0f;
            } else if (desc->ViewDimension == D3D12_SRV_DIMENSION_TEXTURECUBE) {
                ok = (rfl & MAD_X64L_RES_TEX_CUBEARRAY) && rlayers == 6 &&
                     desc->TextureCube.MostDetailedMip == 0 &&
                     (desc->TextureCube.MipLevels == 0 || desc->TextureCube.MipLevels == ~0u || desc->TextureCube.MipLevels >= rmips) &&
                     desc->TextureCube.ResourceMinLODClamp <= 0.0f;
            }
            if (ok) {
                e->gpu_va = 0;
                e->texture_view_id = r->gpu_resource_id;
                e->metadata = 0;
                return;
            }
        }
    }
fallback:;
    MAD_X64L_TAIL return mad_ecfb_device_CreateShaderResourceView(This, res, desc, h);
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_device_CreateSampler(ID3D12Device *This, const D3D12_SAMPLER_DESC *desc,
                                                                   D3D12_CPU_DESCRIPTOR_HANDLE h) {
    const struct mad_x64l_device *d = (const struct mad_x64l_device *)This;
    struct mad_x64l_desc *e = (struct mad_x64l_desc *)(uintptr_t)h.ptr;
    const struct mad_x64l_smp_ent *tbl;
    int32_t n, i;
    uint32_t filter, border;
    float max_lod;
    if (!e) return;
    if (!d || (d->x64_flags & (MAD_X64L_OK | MAD_X64L_DEV_SMP_CACHE)) != (MAD_X64L_OK | MAD_X64L_DEV_SMP_CACHE) || !desc) goto fallback;
    filter = (uint32_t)desc->Filter;
    if (((filter >> 7) & 3u) >= 2u) goto fallback;   /* MIN/MAX reduction samplers log via mad_sampler_log */
    n = mad_x64l_load_i32(&d->smp_x64_n);
    mad_x64l_acq_fence();
    tbl = d->smp_x64;
    if (!tbl || n <= 0) goto fallback;
    border = (desc->BorderColor[0] > 0.5f) ? 2u : (desc->BorderColor[3] > 0.5f) ? 1u : 0u;
    max_lod = desc->MaxLOD > 1000.0f ? 1000.0f : desc->MaxLOD;
    for (i = 0; i < n; i++) {
        if (tbl[i].filter == filter && tbl[i].au == (uint32_t)desc->AddressU &&
            tbl[i].av == (uint32_t)desc->AddressV && tbl[i].aw == (uint32_t)desc->AddressW &&
            tbl[i].aniso == desc->MaxAnisotropy && tbl[i].cmp == (uint32_t)desc->ComparisonFunc &&
            tbl[i].border == border && tbl[i].min_lod == desc->MinLOD && tbl[i].max_lod == max_lod) {
            e->gpu_va = tbl[i].id;
            e->texture_view_id = 0;
            e->metadata = (uint64_t)mad_x64l_float_bits(desc->MipLODBias);
            return;
        }
    }
fallback:;
    MAD_X64L_TAIL return mad_ecfb_device_CreateSampler(This, desc, h);
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_ResourceBarrier(ID3D12GraphicsCommandList *This, UINT n,
                                                                   const D3D12_RESOURCE_BARRIER *b) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    struct mad_x64l_cmd *c;
    UINT i, base_n;
    int have_tail;
    if (!n) return;
    if (!l || !(l->x64_flags & MAD_X64L_OK) || !b) goto fallback;
    if (l->closed) return;
    have_tail = (l->ncmds > 0 && l->cmds[l->ncmds - 1].kind == MAD_X64L_MC_BARRIER);
    base_n = have_tail ? (UINT)l->cmds[l->ncmds - 1].u.barrier.n : 0u;
    if (n > MAD_X64L_BAR_MAX || base_n > MAD_X64L_BAR_MAX - n || (!have_tail && l->ncmds >= l->ccap)) goto fallback;
    for (i = 0; i < n; i++) {
        if (b[i].Type == D3D12_RESOURCE_BARRIER_TYPE_TRANSITION) {
            if (!b[i].Transition.pResource) goto fallback;
        } else if (b[i].Type == D3D12_RESOURCE_BARRIER_TYPE_UAV) {
            if (!b[i].UAV.pResource) goto fallback;
        } else {
            goto fallback;
        }
    }
    if (have_tail) {
        c = &l->cmds[l->ncmds - 1];
        if (c->u.barrier.n == 0 && !c->u.barrier.all) c->u.barrier.cls_noref = MAD_X64L_BC_NONE;
    } else {
        c = &l->cmds[l->ncmds++];
        c->kind = MAD_X64L_MC_BARRIER;
        c->u.barrier.uav_mask = 0;
        c->u.barrier.n = 0;
        c->u.barrier.all = 0;
        c->u.barrier.all_tex = 0;
        c->u.barrier.cls_noref = MAD_X64L_BC_NONE;
        c->u.barrier.vsread = 0;
        c->u.barrier.spill = 0;
    }
    for (i = 0; i < n; i++) {
        void *r;
        uint8_t cls = MAD_X64L_BC_ALL;
        int vs = 0, f5_vs = 0, uav_haz = 0;
        const UINT W = D3D12_RESOURCE_STATE_RENDER_TARGET | D3D12_RESOURCE_STATE_UNORDERED_ACCESS | D3D12_RESOURCE_STATE_DEPTH_WRITE |
                       D3D12_RESOURCE_STATE_STREAM_OUT | D3D12_RESOURCE_STATE_COPY_DEST | D3D12_RESOURCE_STATE_RESOLVE_DEST;
        const UINT F5_VS = D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER |
                           D3D12_RESOURCE_STATE_INDEX_BUFFER | D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT;
        if (b[i].Type == D3D12_RESOURCE_BARRIER_TYPE_TRANSITION) {
            UINT bs = (UINT)b[i].Transition.StateBefore, as = (UINT)b[i].Transition.StateAfter;
            r = (void *)b[i].Transition.pResource;
            if (b[i].Flags & D3D12_RESOURCE_BARRIER_FLAG_BEGIN_ONLY) {
                cls = (uint8_t)(MAD_X64L_BC_RAR | MAD_X64L_BCF_BEGIN_ONLY);
            } else {
                uint8_t bcf = !as ? (uint8_t)MAD_X64L_BCF_TO_COMMON
                    : !(as & ~(UINT)(D3D12_RESOURCE_STATE_RENDER_TARGET | D3D12_RESOURCE_STATE_DEPTH_WRITE)) ? (uint8_t)MAD_X64L_BCF_TO_RT_DSW : 0u;
                if (!as || (as & W) || !bs) {
                    cls = MAD_X64L_BC_ALL;
                    if (!bs || !as || (bs & D3D12_RESOURCE_STATE_UNORDERED_ACCESS) || (as & D3D12_RESOURCE_STATE_UNORDERED_ACCESS)) uav_haz = 1;
                    if (as & F5_VS) f5_vs = 1;
                } else if (!(bs & W)) {
                    cls = MAD_X64L_BC_RAR;
                    if (as & F5_VS) f5_vs = 1;
                } else if (!(bs & ~(UINT)(D3D12_RESOURCE_STATE_RENDER_TARGET | D3D12_RESOURCE_STATE_DEPTH_WRITE))) {
                    cls = MAD_X64L_BC_RAW_ATT;
                    if (as & ~(UINT)(D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_DEPTH_READ)) { vs = 1; f5_vs = 1; }
                } else if (bs == D3D12_RESOURCE_STATE_COPY_DEST) {
                    cls = MAD_X64L_BC_RAW_COPY;
                    if (as & F5_VS) f5_vs = 1;
                } else if (bs == D3D12_RESOURCE_STATE_UNORDERED_ACCESS) {
                    cls = MAD_X64L_BC_RAW_UAV;
                    uav_haz = 1;
                    if (as & F5_VS) f5_vs = 1;
                } else {
                    uav_haz = 1;
                    if (as & F5_VS) f5_vs = 1;
                }
                cls = (uint8_t)(cls | bcf);
            }
        } else {
            r = (void *)b[i].UAV.pResource;
            cls = MAD_X64L_BC_RAW_UAV;
            uav_haz = 1;
        }
        if (uav_haz) c->u.barrier.uav_mask |= (uint16_t)(1u << c->u.barrier.n);
        c->u.barrier.cls[c->u.barrier.n] = cls;
        c->u.barrier.res[c->u.barrier.n++] = r;
        if (vs) c->u.barrier.vsread |= 1u;
        if (f5_vs) c->u.barrier.vsread |= 2u;
    }
    return;
fallback:;
    MAD_X64L_TAIL return mad_ecfb_list_ResourceBarrier(This, n, b);
}
MAD_X64L_LEAF void STDMETHODCALLTYPE mad_x64l_list_DiscardResource(ID3D12GraphicsCommandList *This, ID3D12Resource *res,
                                                                   const D3D12_DISCARD_REGION *region) {
    struct mad_x64l_list *l = (struct mad_x64l_list *)This;
    const struct mad_x64l_resource *r = (const struct mad_x64l_resource *)res;
    struct mad_x64l_cmd *c;
    UINT whole;
    if (!l || !(l->x64_flags & MAD_X64L_OK)) goto fallback;
    if (!r || !r->texture) return;
    if (!region) {
        whole = 1;
    } else if (region->NumRects && region->pRects) {
        whole = 0;
    } else {
        UINT mips = r->desc.MipLevels > r->x64_mips ? (UINT)r->desc.MipLevels : (UINT)r->x64_mips;
        UINT layers = r->desc.Dimension == D3D12_RESOURCE_DIMENSION_TEXTURE3D ? 1u : (r->desc.DepthOrArraySize ? (UINT)r->desc.DepthOrArraySize : 1u);
        UINT planes = (r->is_depth && r->has_stencil) ? 2u : 1u;
        if (!mips) mips = 1;
        whole = (region->FirstSubresource == 0 && region->NumSubresources >= mips * layers * planes) ? 1u : 0u;
    }
    if (whole && !(mad_x64l_load_i32(&r->x64_flags) & MAD_X64L_RES_IN_DSET)) goto fallback;
    if (!mad_x64l_push(l, MAD_X64L_MC_DISCARD, &c)) goto fallback;
    if (c) {
        c->u.discard.res = res;
        c->u.discard.whole = whole;
    }
    return;
fallback:;
    MAD_X64L_TAIL return mad_ecfb_list_DiscardResource(This, res, region);
}
