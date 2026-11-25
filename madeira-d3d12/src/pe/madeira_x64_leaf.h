/* SPDX-License-Identifier: GPL-3.0-only */
/* madeira-m5 0.1.717 x64-leaf (0.1.718 Phase B, 0.1.723 Phase C, 0.1.728 Phase D: 32 leaves):
 * the layout contract between madeira_d3d12.c (ARM64EC) and madeira_x64_leaf.c (pure x86-64), included by both.
 *
 * Horizon Forbidden West makes 1.3-1.5 M x64->ARM64EC transitions a second, 69 % of them into
 * four COM methods whose bodies are a handful of loads and stores (Round 3 forensic report,
 * section 4.2). Each transition costs 110-150 instructions and a full barrier (section 4.3).
 * With bcd.cfg x64-leaf = 1 the vtable slots of thirty-two such methods (0.1.717: 13; 0.1.718 Phase B: +8;
 * 0.1.723 Phase C: +2; 0.1.728 Phase D: +9: fence_GetCompletedValue, alloc_Reset, list_Close, list_Reset,
 * list_SetDescriptorHeaps, list_OMSetRenderTargets, list_CopyBufferRegion, res_Map, res_Unmap) name x86-64
 * code linked into the DLL (section ".x64leaf", classified X64 in the ARM64EC code map), which FEX runs as
 * translated x64 without leaving the JIT. Every leaf reads and writes only fields of the object
 * it was called on, at the offsets below, and tail-jumps to the ARM64EC body for anything else.
 * Default 0: the vtables are exactly what they were.
 *
 * The two compilers share the Windows x64 data ABI, so the mirror structs here lay out like the
 * real ones; madeira_d3d12.c asserts the real structs against the same constants, and both sides
 * assert the mirrors, so a field that moves on either side stops the build instead of the game.
 * Requires <d3d12.h> (D3D12_RESOURCE_DESC, D3D12_HEAP_DESC, the handle types) before it. */
#ifndef MADEIRA_X64_LEAF_H
#define MADEIRA_X64_LEAF_H

#include <stddef.h>
#include <stdint.h>

/* x64_flags (per device, per command list, per fence): bit 0 set = the x64 leaves may take their fast path
 * on this object. Written once, when the object is created, by ARM64EC code; the leaves only read
 * it. It is set only when x64-leaf = 1 and no diagnostic mode that hooks these methods (desc-guard
 * and the other sync diagnostics, static-cbv, view-census, trace-buffer-size) was selected at device creation. */
#define MAD_X64L_OK 1

/* struct mad_cmd: the recorded command. kind at 0, the union at 8, 160 bytes in all. */
#define MAD_X64L_CMD_SIZE          160
#define MAD_X64L_CMD_U_OFF         8
#define MAD_X64L_MC_PSO            0    /* enum mad_ck */
#define MAD_X64L_MC_ROOT           1
#define MAD_X64L_MC_HEAPS          2    /* 0.1.728 Phase D */
#define MAD_X64L_MC_VP             3    /* 0.1.718 Phase B */
#define MAD_X64L_MC_SCISSOR        4
#define MAD_X64L_MC_TOPO           5
#define MAD_X64L_MC_IB             6    /* 0.1.723 Phase C */
#define MAD_X64L_MC_VB             7
#define MAD_X64L_MC_RTS            8    /* 0.1.728 Phase D */
#define MAD_X64L_MC_DRAW           11
#define MAD_X64L_MC_DRAW_INDEXED   12
#define MAD_X64L_MC_BLEND_FACTOR   17
#define MAD_X64L_MC_COPY_BB        19   /* 0.1.728 Phase D */
#define MAD_X64L_MC_DISPATCH       23
#define MAD_X64L_MC_ROOTSIG        25
#define MAD_X64L_MC_STENCIL_REF    27
#define MAD_X64L_MC_CROOTSIG       28
#define MAD_X64L_MC_CROOT          29
#define MAD_X64L_IB_U16            0    /* WMTIndexTypeUInt16 */
#define MAD_X64L_IB_U32            1    /* WMTIndexTypeUInt32 */
/* list_IASetPrimitiveTopology logs once from this value on (D3D_PRIMITIVE_TOPOLOGY_LINELIST_ADJ): the leaf takes the slow path there */
#define MAD_X64L_TOPO_FALLBACK     10
#define MAD_X64L_ROOT_PARAM_MAX    64   /* MAD_ROOT_PARAM_MAX: a root parameter index at or past it takes the slow path */

/* struct mad_descriptor (24 bytes) and struct mad_rtv (16 bytes): the two descriptor strides. */
#define MAD_X64L_DESC_SIZE         24
#define MAD_X64L_RTV_SIZE          16

/* struct mad_device: x64_flags sits in the padding after device_lost. */
#define MAD_X64L_DEV_X64_FLAGS_OFF 60

/* struct mad_list: x64_flags sits in the padding after type; has_lazy_pso in padding after inflight. */
#define MAD_X64L_LIST_TYPE_OFF     32
#define MAD_X64L_LIST_X64_FLAGS_OFF 36
#define MAD_X64L_LIST_ALLOC_OFF    40
#define MAD_X64L_LIST_CLOSED_OFF   48
#define MAD_X64L_LIST_RECGEN_OFF   52
#define MAD_X64L_LIST_CMDS_OFF     64
#define MAD_X64L_LIST_NCMDS_OFF    72
#define MAD_X64L_LIST_CCAP_OFF     76
#define MAD_X64L_LIST_NUSED_OFF    88
#define MAD_X64L_LIST_INFLIGHT_OFF 96
#define MAD_X64L_LIST_LAZY_PSO_OFF 100
#define MAD_X64L_LIST_NRINGS_OFF   128
#define MAD_X64L_LIST_RING_USED_OFF 132
#define MAD_X64L_LIST_NCDATA_OFF   160

/* struct mad_alloc (0.1.728 Phase D) */
#define MAD_X64L_ALLOC_RECORDING_OFF 36
#define MAD_X64L_ALLOC_GEN_OFF     40

/* struct mad_fence (0.1.728 Phase D) */
#define MAD_X64L_FENCE_VALUE_OFF   80
#define MAD_X64L_FENCE_X64_FLAGS_OFF 132
#define MAD_X64L_FENCE_NDEFERRED_OFF 152

/* struct mad_pso (0.1.728 Phase D: rps/cps fast check in SetPipelineState) */
#define MAD_X64L_PSO_RPS_OFF       32
#define MAD_X64L_PSO_CPS_OFF       40

/* struct mad_resource */
#define MAD_X64L_RES_CPU_OFF       88
#define MAD_X64L_RES_SIZE_OFF      96
#define MAD_X64L_RES_GPU_ADDRESS_OFF 112
#define MAD_X64L_RES_MAPPED_OFF    120
#define MAD_X64L_RES_DESC_OFF      208

/* struct mad_heap (a descriptor heap) */
#define MAD_X64L_HEAP_TYPE_OFF     32
#define MAD_X64L_HEAP_SLOTS_OFF    40
#define MAD_X64L_HEAP_BUFFER_OFF   56
#define MAD_X64L_HEAP_CPU_OFF      64
#define MAD_X64L_HEAP_GPU_ADDRESS_OFF 72

/* struct mad_memheap (an ID3D12Heap) */
#define MAD_X64L_MEMHEAP_DESC_OFF  40

/* ---- mirrors: what the x64 side sees ------------------------------------------------------ */
struct mad_x64l_rtvp { uint16_t level, slice, layers, plane; };
struct mad_x64l_rtv { void *res; struct mad_x64l_rtvp p; };
struct mad_x64l_cmd {
    int kind; int pad_;
    union {
        void *pso;
        struct { unsigned index; unsigned pad_; uint64_t value; } root;
        struct { void *srv, *smp; } heaps;   /* 0.1.728 Phase D */
        struct { unsigned vcount, icount, vstart, istart; } draw;
        struct { unsigned icount, inst, start; int base; unsigned istart; } drawi;
        /* 0.1.718 Phase B */
        void *rootsig;
        unsigned stencil_ref;
        D3D12_VIEWPORT vp;
        D3D12_RECT scissor;
        D3D12_PRIMITIVE_TOPOLOGY topo;
        struct { unsigned x, y, z; } dispatch;
        struct { float rgba[4]; } blend;
        /* 0.1.723 Phase C */
        struct { void *res; uint64_t off; uint64_t gpu_va; uint8_t type; } ib;
        struct { unsigned slot; unsigned pad_; void *res; uint64_t off; uint64_t gpu_va; unsigned stride; } vb;
        /* 0.1.728 Phase D */
        struct { void *rt[8]; unsigned n; unsigned pad_; void *depth; struct mad_x64l_rtvp v[8], dv; } rts;
        struct { void *dst, *src; uint64_t doff, soff, len; } bb;
        unsigned char raw[MAD_X64L_CMD_SIZE - MAD_X64L_CMD_U_OFF];
    } u;
};
struct mad_x64l_desc { uint64_t gpu_va, texture_view_id, metadata; };
struct mad_x64l_device {
    void *vtbl; int refs; const void *iid; const char *name;
    uint64_t mtl_device, mtl_queue, dsso;
    int device_lost;
    int x64_flags;
};
struct mad_x64l_alloc {
    void *vtbl; int refs; const void *iid; const char *name;
    int type;
    volatile int32_t recording;
    volatile int32_t generation;
};
struct mad_x64l_fence {
    unsigned char head[MAD_X64L_FENCE_VALUE_OFF];
    uint64_t value;
    unsigned char mid1[MAD_X64L_FENCE_X64_FLAGS_OFF - MAD_X64L_FENCE_VALUE_OFF - 8];
    int32_t x64_flags;
    unsigned char mid2[MAD_X64L_FENCE_NDEFERRED_OFF - MAD_X64L_FENCE_X64_FLAGS_OFF - 4];
    volatile int32_t ndeferred;
};
struct mad_x64l_pso {
    unsigned char head[MAD_X64L_PSO_RPS_OFF];
    uint64_t rps;
    uint64_t cps;
};
struct mad_x64l_list {
    void *vtbl; int refs; const void *iid; const char *name;
    int type;
    int x64_flags;
    struct mad_x64l_alloc *alloc;
    int closed;
    int32_t recorded_generation;
    void *device;
    struct mad_x64l_cmd *cmds;
    unsigned ncmds, ccap;
    void *used;
    unsigned nused, ucap;
    volatile int32_t inflight;
    int32_t has_lazy_pso;
    void *rings, *ring_cpu, *ring_gpu;
    unsigned nrings, ring_used;
    void *ring_q;
    uint64_t ring_batch;
    void *cdata;
    unsigned ncdata, cdcap;
};
struct mad_x64l_heap {
    void *vtbl; int refs; const void *iid; const char *name;
    int type; int pad_;
    struct mad_x64l_rtv *slots;
    int shader_visible; int pad2_;
    uint64_t buffer;
    struct mad_x64l_desc *cpu;
    uint64_t gpu_address;
    unsigned count;
};
struct mad_x64l_resource {
    unsigned char head[MAD_X64L_RES_CPU_OFF];
    void *cpu;
    uint64_t size;
    unsigned char mid0[MAD_X64L_RES_GPU_ADDRESS_OFF - MAD_X64L_RES_SIZE_OFF - 8];
    uint64_t gpu_address;
    volatile int32_t mapped;
    unsigned char mid1[MAD_X64L_RES_DESC_OFF - MAD_X64L_RES_MAPPED_OFF - 4];
    D3D12_RESOURCE_DESC desc;
};
struct mad_x64l_memheap {
    unsigned char head[MAD_X64L_MEMHEAP_DESC_OFF];
    D3D12_HEAP_DESC desc;
};

/* The mirrors against the constants: compiled on both sides. */
#define MAD_X64L_CHECK(c) _Static_assert(c, "madeira_x64_leaf.h: " #c)
MAD_X64L_CHECK(sizeof(struct mad_x64l_cmd) == MAD_X64L_CMD_SIZE);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u) == MAD_X64L_CMD_U_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.root.value) == MAD_X64L_CMD_U_OFF + 8);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.heaps.smp) == MAD_X64L_CMD_U_OFF + 8);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.drawi.base) == MAD_X64L_CMD_U_OFF + 12);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.rootsig) == MAD_X64L_CMD_U_OFF && offsetof(struct mad_x64l_cmd, u.stencil_ref) == MAD_X64L_CMD_U_OFF);   /* 0.1.718 Phase B */
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.vp) == MAD_X64L_CMD_U_OFF && sizeof(D3D12_VIEWPORT) == 24 && sizeof(D3D12_VIEWPORT) % 4 == 0);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.scissor) == MAD_X64L_CMD_U_OFF && sizeof(D3D12_RECT) == 16 && sizeof(D3D12_RECT) % 4 == 0);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.topo) == MAD_X64L_CMD_U_OFF && sizeof(D3D12_PRIMITIVE_TOPOLOGY) == 4);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.dispatch.z) == MAD_X64L_CMD_U_OFF + 8 && offsetof(struct mad_x64l_cmd, u.blend.rgba[3]) == MAD_X64L_CMD_U_OFF + 12);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.ib.gpu_va) == MAD_X64L_CMD_U_OFF + 16 && offsetof(struct mad_x64l_cmd, u.ib.type) == MAD_X64L_CMD_U_OFF + 24);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.vb.slot) == MAD_X64L_CMD_U_OFF && offsetof(struct mad_x64l_cmd, u.vb.gpu_va) == MAD_X64L_CMD_U_OFF + 24 && offsetof(struct mad_x64l_cmd, u.vb.stride) == MAD_X64L_CMD_U_OFF + 32);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.rts.depth) == MAD_X64L_CMD_U_OFF + 72 && offsetof(struct mad_x64l_cmd, u.rts.dv) == MAD_X64L_CMD_U_OFF + 144);
MAD_X64L_CHECK(offsetof(struct mad_x64l_cmd, u.bb.doff) == MAD_X64L_CMD_U_OFF + 16 && offsetof(struct mad_x64l_cmd, u.bb.len) == MAD_X64L_CMD_U_OFF + 32);
MAD_X64L_CHECK(sizeof(struct mad_x64l_desc) == MAD_X64L_DESC_SIZE);
MAD_X64L_CHECK(sizeof(struct mad_x64l_rtv) == MAD_X64L_RTV_SIZE);
MAD_X64L_CHECK(offsetof(struct mad_x64l_device, x64_flags) == MAD_X64L_DEV_X64_FLAGS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, type) == MAD_X64L_LIST_TYPE_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, x64_flags) == MAD_X64L_LIST_X64_FLAGS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, alloc) == MAD_X64L_LIST_ALLOC_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, closed) == MAD_X64L_LIST_CLOSED_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, recorded_generation) == MAD_X64L_LIST_RECGEN_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, cmds) == MAD_X64L_LIST_CMDS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, ncmds) == MAD_X64L_LIST_NCMDS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, ccap) == MAD_X64L_LIST_CCAP_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, nused) == MAD_X64L_LIST_NUSED_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, inflight) == MAD_X64L_LIST_INFLIGHT_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, has_lazy_pso) == MAD_X64L_LIST_LAZY_PSO_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, nrings) == MAD_X64L_LIST_NRINGS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, ring_used) == MAD_X64L_LIST_RING_USED_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_list, ncdata) == MAD_X64L_LIST_NCDATA_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_alloc, recording) == MAD_X64L_ALLOC_RECORDING_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_alloc, generation) == MAD_X64L_ALLOC_GEN_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_fence, value) == MAD_X64L_FENCE_VALUE_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_fence, x64_flags) == MAD_X64L_FENCE_X64_FLAGS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_fence, ndeferred) == MAD_X64L_FENCE_NDEFERRED_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_pso, rps) == MAD_X64L_PSO_RPS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_pso, cps) == MAD_X64L_PSO_CPS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_resource, cpu) == MAD_X64L_RES_CPU_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_resource, size) == MAD_X64L_RES_SIZE_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_resource, gpu_address) == MAD_X64L_RES_GPU_ADDRESS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_resource, mapped) == MAD_X64L_RES_MAPPED_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_resource, desc) == MAD_X64L_RES_DESC_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_heap, type) == MAD_X64L_HEAP_TYPE_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_heap, slots) == MAD_X64L_HEAP_SLOTS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_heap, buffer) == MAD_X64L_HEAP_BUFFER_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_heap, cpu) == MAD_X64L_HEAP_CPU_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_heap, gpu_address) == MAD_X64L_HEAP_GPU_ADDRESS_OFF);
MAD_X64L_CHECK(offsetof(struct mad_x64l_memheap, desc) == MAD_X64L_MEMHEAP_DESC_OFF);

/* ---- the thirty-two leaves (defined in madeira_x64_leaf.c, installed by madeira_d3d12.c) ---- */
D3D12_GPU_VIRTUAL_ADDRESS STDMETHODCALLTYPE mad_x64l_res_GetGPUVirtualAddress(ID3D12Resource *This);
D3D12_RESOURCE_DESC * STDMETHODCALLTYPE mad_x64l_res_GetDesc(ID3D12Resource *This, D3D12_RESOURCE_DESC *ret);
D3D12_HEAP_DESC * STDMETHODCALLTYPE mad_x64l_memheap_GetDesc(ID3D12Heap *This, D3D12_HEAP_DESC *ret);
D3D12_CPU_DESCRIPTOR_HANDLE * STDMETHODCALLTYPE mad_x64l_heap_GetCPUDescriptorHandleForHeapStart(ID3D12DescriptorHeap *This, D3D12_CPU_DESCRIPTOR_HANDLE *out);
D3D12_GPU_DESCRIPTOR_HANDLE * STDMETHODCALLTYPE mad_x64l_heap_GetGPUDescriptorHandleForHeapStart(ID3D12DescriptorHeap *This, D3D12_GPU_DESCRIPTOR_HANDLE *out);
UINT STDMETHODCALLTYPE mad_x64l_device_GetDescriptorHandleIncrementSize(ID3D12Device *This, D3D12_DESCRIPTOR_HEAP_TYPE type);
void STDMETHODCALLTYPE mad_x64l_res_Unmap(ID3D12Resource *This, UINT sub, const D3D12_RANGE *written);   /* 0.1.728 Phase D */
void STDMETHODCALLTYPE mad_x64l_device_CopyDescriptorsSimple(ID3D12Device *This, UINT n, D3D12_CPU_DESCRIPTOR_HANDLE dst,
                                                            D3D12_CPU_DESCRIPTOR_HANDLE src, D3D12_DESCRIPTOR_HEAP_TYPE type);
void STDMETHODCALLTYPE mad_x64l_device_CreateConstantBufferView(ID3D12Device *This, const D3D12_CONSTANT_BUFFER_VIEW_DESC *desc,
                                                               D3D12_CPU_DESCRIPTOR_HANDLE h);
void STDMETHODCALLTYPE mad_x64l_list_SetGraphicsRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h);
void STDMETHODCALLTYPE mad_x64l_list_SetComputeRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h);
void STDMETHODCALLTYPE mad_x64l_list_DrawInstanced(ID3D12GraphicsCommandList *This, UINT vcount, UINT icount, UINT vstart, UINT istart);
void STDMETHODCALLTYPE mad_x64l_list_DrawIndexedInstanced(ID3D12GraphicsCommandList *This, UINT icount, UINT inst, UINT start, INT base, UINT istart);
void STDMETHODCALLTYPE mad_x64l_list_SetPipelineState(ID3D12GraphicsCommandList *This, ID3D12PipelineState *pso);
/* 0.1.718 Phase B: the trivial batch */
void STDMETHODCALLTYPE mad_x64l_list_SetGraphicsRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs);
void STDMETHODCALLTYPE mad_x64l_list_SetComputeRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs);
void STDMETHODCALLTYPE mad_x64l_list_RSSetViewports(ID3D12GraphicsCommandList *This, UINT n, const D3D12_VIEWPORT *vp);
void STDMETHODCALLTYPE mad_x64l_list_RSSetScissorRects(ID3D12GraphicsCommandList *This, UINT n, const D3D12_RECT *r);
void STDMETHODCALLTYPE mad_x64l_list_IASetPrimitiveTopology(ID3D12GraphicsCommandList *This, D3D12_PRIMITIVE_TOPOLOGY t);
void STDMETHODCALLTYPE mad_x64l_list_OMSetStencilRef(ID3D12GraphicsCommandList *This, UINT ref);
void STDMETHODCALLTYPE mad_x64l_list_OMSetBlendFactor(ID3D12GraphicsCommandList *This, const FLOAT f[4]);
void STDMETHODCALLTYPE mad_x64l_list_Dispatch(ID3D12GraphicsCommandList *This, UINT x, UINT y, UINT z);
/* 0.1.723 Phase C: deferred-VA index/vertex buffer setters */
void STDMETHODCALLTYPE mad_x64l_list_IASetIndexBuffer(ID3D12GraphicsCommandList *This, const D3D12_INDEX_BUFFER_VIEW *view);
void STDMETHODCALLTYPE mad_x64l_list_IASetVertexBuffers(ID3D12GraphicsCommandList *This, UINT start, UINT n, const D3D12_VERTEX_BUFFER_VIEW *views);
/* 0.1.728 Phase D: fence poll, lifecycle, render targets, heaps, buffer copy, Map */
UINT64 STDMETHODCALLTYPE mad_x64l_fence_GetCompletedValue(ID3D12Fence *This);
HRESULT STDMETHODCALLTYPE mad_x64l_alloc_Reset(ID3D12CommandAllocator *This);
HRESULT STDMETHODCALLTYPE mad_x64l_list_Close(ID3D12GraphicsCommandList *This);
HRESULT STDMETHODCALLTYPE mad_x64l_list_Reset(ID3D12GraphicsCommandList *This, ID3D12CommandAllocator *allocator, ID3D12PipelineState *pso);
void STDMETHODCALLTYPE mad_x64l_list_SetDescriptorHeaps(ID3D12GraphicsCommandList *This, UINT n, ID3D12DescriptorHeap *const *heaps);
void STDMETHODCALLTYPE mad_x64l_list_OMSetRenderTargets(ID3D12GraphicsCommandList *This, UINT n, const D3D12_CPU_DESCRIPTOR_HANDLE *rtvs, BOOL single, const D3D12_CPU_DESCRIPTOR_HANDLE *dsv);
void STDMETHODCALLTYPE mad_x64l_list_CopyBufferRegion(ID3D12GraphicsCommandList *This, ID3D12Resource *dst, UINT64 dst_off, ID3D12Resource *src, UINT64 src_off, UINT64 len);
HRESULT STDMETHODCALLTYPE mad_x64l_res_Map(ID3D12Resource *This, UINT sub, const D3D12_RANGE *read_range, void **data);

/* ---- the twenty-five ARM64EC fallbacks (madeira_d3d12.c) the leaves with a slow path jump to ----
 * External linkage, so each has an entry thunk and the word before its body that FEX reads
 * ([target - 4]). The x64 side declares them itself, naming the "#" bodies. */
#if defined(__arm64ec__)
void STDMETHODCALLTYPE mad_ecfb_device_CopyDescriptorsSimple(ID3D12Device *This, UINT n, D3D12_CPU_DESCRIPTOR_HANDLE dst,
                                                            D3D12_CPU_DESCRIPTOR_HANDLE src, D3D12_DESCRIPTOR_HEAP_TYPE type);
void STDMETHODCALLTYPE mad_ecfb_device_CreateConstantBufferView(ID3D12Device *This, const D3D12_CONSTANT_BUFFER_VIEW_DESC *desc,
                                                               D3D12_CPU_DESCRIPTOR_HANDLE h);
void STDMETHODCALLTYPE mad_ecfb_list_SetGraphicsRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h);
void STDMETHODCALLTYPE mad_ecfb_list_SetComputeRootDescriptorTable(ID3D12GraphicsCommandList *This, UINT index, D3D12_GPU_DESCRIPTOR_HANDLE h);
void STDMETHODCALLTYPE mad_ecfb_list_DrawInstanced(ID3D12GraphicsCommandList *This, UINT vcount, UINT icount, UINT vstart, UINT istart);
void STDMETHODCALLTYPE mad_ecfb_list_DrawIndexedInstanced(ID3D12GraphicsCommandList *This, UINT icount, UINT inst, UINT start, INT base, UINT istart);
void STDMETHODCALLTYPE mad_ecfb_list_SetPipelineState(ID3D12GraphicsCommandList *This, ID3D12PipelineState *pso);
void STDMETHODCALLTYPE mad_ecfb_list_SetGraphicsRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs);   /* 0.1.718 Phase B */
void STDMETHODCALLTYPE mad_ecfb_list_SetComputeRootSignature(ID3D12GraphicsCommandList *This, ID3D12RootSignature *rs);
void STDMETHODCALLTYPE mad_ecfb_list_RSSetViewports(ID3D12GraphicsCommandList *This, UINT n, const D3D12_VIEWPORT *vp);
void STDMETHODCALLTYPE mad_ecfb_list_RSSetScissorRects(ID3D12GraphicsCommandList *This, UINT n, const D3D12_RECT *r);
void STDMETHODCALLTYPE mad_ecfb_list_IASetPrimitiveTopology(ID3D12GraphicsCommandList *This, D3D12_PRIMITIVE_TOPOLOGY t);
void STDMETHODCALLTYPE mad_ecfb_list_OMSetStencilRef(ID3D12GraphicsCommandList *This, UINT ref);
void STDMETHODCALLTYPE mad_ecfb_list_OMSetBlendFactor(ID3D12GraphicsCommandList *This, const FLOAT f[4]);
void STDMETHODCALLTYPE mad_ecfb_list_Dispatch(ID3D12GraphicsCommandList *This, UINT x, UINT y, UINT z);
void STDMETHODCALLTYPE mad_ecfb_list_IASetIndexBuffer(ID3D12GraphicsCommandList *This, const D3D12_INDEX_BUFFER_VIEW *view);   /* 0.1.723 Phase C */
void STDMETHODCALLTYPE mad_ecfb_list_IASetVertexBuffers(ID3D12GraphicsCommandList *This, UINT start, UINT n, const D3D12_VERTEX_BUFFER_VIEW *views);
/* 0.1.728 Phase D */
UINT64 STDMETHODCALLTYPE mad_ecfb_fence_GetCompletedValue(ID3D12Fence *This);
HRESULT STDMETHODCALLTYPE mad_ecfb_alloc_Reset(ID3D12CommandAllocator *This);
HRESULT STDMETHODCALLTYPE mad_ecfb_list_Close(ID3D12GraphicsCommandList *This);
HRESULT STDMETHODCALLTYPE mad_ecfb_list_Reset(ID3D12GraphicsCommandList *This, ID3D12CommandAllocator *allocator, ID3D12PipelineState *pso);
void STDMETHODCALLTYPE mad_ecfb_list_SetDescriptorHeaps(ID3D12GraphicsCommandList *This, UINT n, ID3D12DescriptorHeap *const *heaps);
void STDMETHODCALLTYPE mad_ecfb_list_OMSetRenderTargets(ID3D12GraphicsCommandList *This, UINT n, const D3D12_CPU_DESCRIPTOR_HANDLE *rtvs, BOOL single, const D3D12_CPU_DESCRIPTOR_HANDLE *dsv);
void STDMETHODCALLTYPE mad_ecfb_list_CopyBufferRegion(ID3D12GraphicsCommandList *This, ID3D12Resource *dst, UINT64 dst_off, ID3D12Resource *src, UINT64 src_off, UINT64 len);
HRESULT STDMETHODCALLTYPE mad_ecfb_res_Map(ID3D12Resource *This, UINT sub, const D3D12_RANGE *read_range, void **data);
#endif

#endif /* MADEIRA_X64_LEAF_H */
