# Julia Compiler SSA IR Representation - Deep Exploration

## Executive Summary

The SSA IR subsystem is the **foundational data structure** for all optimization passes in the Julia compiler. It provides a clean, well-structured intermediate representation that enables efficient analysis and transformation of code. The subsystem converts lowered code (with mutable slot variables) into Static Single Assignment (SSA) form, where each variable is assigned exactly once, making dataflow analysis and optimization significantly easier.

**Key Files Analyzed:**
- `ssair/ir.jl` (~2181 lines) - Main IR structures (IRCode, CFG, IncrementalCompact)
- `ssair/basicblock.jl` (~31 lines) - BasicBlock and StmtRange definitions
- `ssair/domtree.jl` (~728 lines) - Dominator tree construction (SNCA algorithm)
- `ssair/slot2ssa.jl` (~896 lines) - Slot-to-SSA conversion (IDF algorithm)
- `ssair/legacy.jl` (~113 lines) - IRCode to/from CodeInfo conversion
- `ssair/show.jl` (~1227 lines) - Pretty printing infrastructure
- `types.jl` - VarState and related type definitions

**Permalink Base:** https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/

---

## 1. Core Data Structures

### 1.1 IRCode - The Primary IR Container

**Location:** [ssair/ir.jl:427-455](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/ir.jl#L427-L455)

```julia
struct IRCode
    stmts::InstructionStream      # Main statement array
    argtypes::Vector{Any}         # Types of function arguments
    sptypes::Vector{VarState}     # Static parameter types
    debuginfo::DebugInfoStream    # Debug/source location info
    cfg::CFG                      # Control Flow Graph
    new_nodes::NewNodeStream      # Pending inserted nodes
    meta::Vector{Expr}            # Metadata expressions
    valid_worlds::WorldRange      # World age validity range
end
```

**Purpose:** IRCode is the central data structure that holds the entire optimized intermediate representation of a function.

### 1.2 CFG - Control Flow Graph

**Location:** [ssair/ir.jl:6-10](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/ir.jl#L6-L10)

```julia
struct CFG
    blocks::Vector{BasicBlock}
    index::Vector{Int}  # map from instruction => basic-block number
end
```

### 1.3 BasicBlock

**Location:** [ssair/basicblock.jl:18-22](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/basicblock.jl#L18-L22)

```julia
struct BasicBlock
    stmts::StmtRange      # Range of statement indices
    preds::Vector{Int}    # Predecessor block indices
    succs::Vector{Int}    # Successor block indices
end
```

### 1.4 SSA Value Types

- **SSAValue** (Core): References a specific SSA statement by its index
- **Argument** (Core): References a function argument by position
- **OldSSAValue** [ir.jl:226-228]: Used during compaction to reference pre-compaction SSA values
- **NewSSAValue** [ir.jl:248-250]: Used during IncrementalCompact to reference newly inserted nodes

### 1.5 InstructionStream

**Location:** [ssair/ir.jl:255-274](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/ir.jl#L255-L274)

```julia
struct InstructionStream
    stmt::Vector{Any}        # The actual statements
    type::Vector{Any}        # Inferred types
    info::Vector{CallInfo}   # Call site information
    line::Vector{Int32}      # Line number info (3 per stmt)
    flag::Vector{UInt32}     # IR flags (effects, removability, etc.)
end
```

### 1.6 VarState

**Location:** [types.jl:85-90](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/types.jl#L85-L90)

```julia
struct VarState
    typ        # Inferred type
    ssadef::Int  # Reaching definition (-n for virtual phi, 0 for arg)
    undef::Bool  # May be undefined?
end
```

---

## 2. CFG Operations

### 2.1 Computing Basic Blocks

**Location:** [ssair/ir.jl:94-150](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/ir.jl#L94-L150)

The `compute_basic_blocks` function:
1. Finds jump destinations (entry, GotoNode targets, branch fall-throughs, EnterNode catch)
2. Creates BasicBlock objects with statement ranges
3. Computes predecessors/successors including virtual edges for entry and exception handling

### 2.2 Edge Manipulation

- **cfg_insert_edge!** [ir.jl:14-18]: Add CFG edge
- **cfg_delete_edge!** [ir.jl:21-28]: Remove CFG edge
- **block_for_inst** [ir.jl:36-44]: O(log n) lookup of block for instruction

---

## 3. Dominator Tree

### 3.1 Overview

**Location:** [ssair/domtree.jl](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/domtree.jl)

Uses the **Semi-NCA (SNCA) algorithm** from Georgiadis' PhD thesis (same as LLVM). Also supports **Dynamic SNCA** for incremental updates.

### 3.2 Key Structures

- **DFSTree** [domtree.jl:74-87]: Preorder/postorder numbering and parent relationships
- **SNCAData** [domtree.jl:207-210]: Per-block semidominator and label for path compression
- **DomTreeNode** [domtree.jl:213-218]: Level and children in the dominator tree
- **GenericDomTree** [domtree.jl:223-235]: Complete dominator tree with DFS tree, immediate dominators, and nodes

### 3.3 Key Functions

| Function | Line | Purpose |
|----------|------|---------|
| `construct_domtree` | 241-243 | Build dominator tree from basic blocks |
| `DFS!` | 123-198 | Depth-first search for preorder/postorder |
| `SNCA!` | 307-405 | Main Semi-NCA algorithm |
| `dominates` | 605-606 | Check if bb1 dominates bb2 |
| `nearest_common_dominator` | 659-679 | Find NCA of two blocks |
| `domtree_insert_edge!` | 450-473 | Dynamic update for edge insertion |
| `domtree_delete_edge!` | 476-501 | Dynamic update for edge deletion |

---

## 4. Slot to SSA Conversion

### 4.1 Overview

**Location:** [ssair/slot2ssa.jl](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/slot2ssa.jl)

Converts lowered code with mutable `SlotNumber` variables into proper SSA form.

### 4.2 Key Structures

- **SlotInfo** [slot2ssa.jl:3-8]: Tracks definitions, uses, and NewvarNode presence for each slot
- **BlockLiveness** [slot2ssa.jl:184-187]: Definition and live-in blocks for a slot

### 4.3 Conversion Process (construct_ssa!, lines 552-896)

1. **Scan slot defs/uses** (`scan_slot_def_use`, lines 36-48)
2. **Compute liveness** (`compute_live_ins`, lines 496-532)
3. **Place phi nodes via IDF** (`iterated_dominance_frontier`, lines 231-287)
4. **SSA renaming** (lines 661-835) - Walk domtree order, track incoming values, replace slots
5. **Sort by domtree order** (`domsort_ssa!`, lines 337-492)

---

## 5. IncrementalCompact

### 5.1 Overview

**Location:** [ssair/ir.jl:745-804](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/ir.jl#L745-L804)

A mutable iterator that processes IR statements one at a time, enabling on-the-fly modifications during optimization passes. Tracks SSA use counts for automatic dead code elimination.

### 5.2 Key Operations

| Function | Line | Purpose |
|----------|------|---------|
| `iterate_compact` | 1877-1963 | Core compaction logic |
| `process_node!` | 1459-1698 | Process single instruction |
| `insert_node!` | 975-1032 | Insert new instruction |
| `insert_node_here!` | 1050-1067 | Insert at current position |
| `finish` | 2117-2121 | Complete compaction with DCE |
| `simple_dce!` | 2088-2100 | Dead code elimination |
| `kill_edge!` | 1367-1452 | Remove CFG edge during compact |

---

## 6. Legacy Conversion

**Location:** [ssair/legacy.jl](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/legacy.jl)

- **inflate_ir!** (lines 11-48): CodeInfo to IRCode
- **replace_code_newstyle!** (lines 71-106): IRCode back to CodeInfo

---

## 7. Important Functions Summary (20 Key Functions)

| # | Function | File | Line | Purpose |
|---|----------|------|------|---------|
| 1 | `compute_basic_blocks` | ir.jl | 94-150 | Build CFG from statements |
| 2 | `construct_domtree` | domtree.jl | 241-243 | Build dominator tree |
| 3 | `dominates` | domtree.jl | 605-606 | Check dominance relation |
| 4 | `construct_ssa!` | slot2ssa.jl | 552-896 | Convert to SSA form |
| 5 | `iterated_dominance_frontier` | slot2ssa.jl | 231-287 | IDF for phi placement |
| 6 | `domsort_ssa!` | slot2ssa.jl | 337-492 | Order blocks by domtree |
| 7 | `IncrementalCompact` (constructor) | ir.jl | 769-787 | Create compaction iterator |
| 8 | `process_node!` | ir.jl | 1459-1698 | Process single IR node |
| 9 | `insert_node!` | ir.jl | 673-691 | Insert new IR node |
| 10 | `compact!` | ir.jl | 2145-2150 | Run full compaction |
| 11 | `block_for_inst` | ir.jl | 36-44 | Find block for instruction |
| 12 | `cfg_insert_edge!` | ir.jl | 14-18 | Add CFG edge |
| 13 | `cfg_delete_edge!` | ir.jl | 21-28 | Remove CFG edge |
| 14 | `kill_edge!` | ir.jl | 1367-1452 | Remove edge during compact |
| 15 | `inflate_ir!` | legacy.jl | 11-48 | CodeInfo to IRCode |
| 16 | `replace_code_newstyle!` | legacy.jl | 71-106 | IRCode to CodeInfo |
| 17 | `SNCA!` | domtree.jl | 307-405 | Compute dominators |
| 18 | `DFS!` | domtree.jl | 123-198 | DFS tree construction |
| 19 | `simple_dce!` | ir.jl | 2088-2100 | Dead code elimination |
| 20 | `nearest_common_dominator` | domtree.jl | 659-679 | Find NCA in domtree |

---

## 8. Cross-References to Optimization Passes

The SSA IR is used by virtually all optimization passes:

- **SROA**: Uses IncrementalCompact, dominator tree for insertion points
- **Inlining**: Creates child IncrementalCompact, splices inlined IR
- **DCE**: Built into IncrementalCompact via used_ssas tracking
- **Constant Propagation**: Uses ssa_rename for value replacement, branch folding
- **Type Inference**: Types flow through SSA definitions via `types(ir)[ssa]`

---

## 9. Architecture Diagram

```
                    CodeInfo (Lowered IR)
                           |
                           v
                    inflate_ir!()
                           |
                           v
    +------------------IRCode------------------+
    |  stmts: InstructionStream                |
    |  cfg: CFG (blocks, index)                |
    |  argtypes, sptypes, debuginfo, meta      |
    +------------------------------------------+
                           |
              construct_domtree(cfg)
                           |
                           v
                     DomTree
                           |
              construct_ssa!(ci, ir, ...)
                           |
                           v
              IncrementalCompact
                    (Optimization Passes)
                           |
                  finish(compact)
                           |
                           v
                 Optimized IRCode
                           |
            replace_code_newstyle!()
                           |
                           v
               CodeInfo (for codegen)
```

---

## 10. Key Design Principles

1. **Single Static Assignment**: Each SSA value defined exactly once
2. **Incremental Compaction**: On-the-fly modification during iteration
3. **Use Counting**: Track SSA usage for DCE without separate analysis
4. **Lazy Insertion**: new_nodes stream allows inserting without reindexing
5. **CFG Abstraction**: Explicit edges enable local and global optimizations
6. **Dominator-Based SSA**: Industry-standard IDF algorithm for minimal phi nodes
7. **Dynamic Dominator Updates**: DSNCA for incremental edge changes
8. **Type Preservation**: Every SSA value has an associated inferred type

---

This comprehensive analysis covers the foundational SSA IR subsystem that enables Julia's powerful optimization capabilities. The IRCode structure, CFG, dominator tree, and IncrementalCompact work together to provide an efficient and flexible intermediate representation for all compiler optimizations.
