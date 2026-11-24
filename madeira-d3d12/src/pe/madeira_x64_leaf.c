/* SPDX-License-Identifier: GPL-3.0-only */
/* madeira-m5 0.1.717 x64-leaf: the pure x86-64 half of madeira_d3d12.dll (see madeira_x64_leaf.h).
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

_Static_assert(sizeof(D3D12_RESOURCE_DESC) % 8 == 0, "D3D12_RESOURCE_DESC is copied in 8-byte words");
_Static_assert(sizeof(D3D12_HEAP_DESC) % 8 == 0, "D3D12_HEAP_DESC is copied in 8-byte words");

/* Plain word loops: -fno-builtin keeps the compiler from turning them into memcpy/memset calls. */
MAD_X64L_INLINE void mad_x64l_copy_words(uint64_t *to, const uint64_t *from, size_t nwords) {
    size_t i;
    for (i = 0; i < nwords; i++) to[i] = from[i];
}
MAD_X64L_INLINE void mad_x64l_zero_cmd(struct mad_x64l_cmd *c) {
    uint64_t *p = (uint64_t *)c;
    unsigned i;
    for (i = 0; i < MAD_X64L_CMD_SIZE / 8; i++) p[i] = 0;
}
/* mad_list_push's fast half: 1 with the command appended (zeroed, kind set), 0 when the ARM64EC
 * body must take it (no fast path on this list, or the command array is full and must grow).
 * A closed list records nothing, exactly as mad_list_push returns NULL for it; that is reported
 * as "done" (*c == NULL) rather than as a fallback, so it costs no transition either. */
MAD_X64L_INLINE int mad_x64l_push(struct mad_x64l_list *l, int kind, struct mad_x64l_cmd **c) {
    *c = NULL;
    if (!(l->x64_flags & MAD_X64L_OK) || l->ncmds >= l->ccap) return 0;
    if (l->closed) return 1;
    *c = &l->cmds[l->ncmds++];
    mad_x64l_zero_cmd(*c);
    (*c)->kind = kind;
    return 1;
}
MAD_X64L_INLINE UINT mad_x64l_stride(D3D12_DESCRIPTOR_HEAP_TYPE type) {   /* mad_descriptor_stride */
    return type == D3D12_DESCRIPTOR_HEAP_TYPE_RTV || type == D3D12_DESCRIPTOR_HEAP_TYPE_DSV ? MAD_X64L_RTV_SIZE : MAD_X64L_DESC_SIZE;
}

/* ---- pure field reads: no slow path, no fallback ------------------------------------------ */
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
    if (c) c->u.pso = pso;
}
