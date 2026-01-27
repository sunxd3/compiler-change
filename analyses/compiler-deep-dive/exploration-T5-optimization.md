# Julia Compiler Optimization Passes - Deep Dive Exploration

This document provides a comprehensive exploration of the Julia compiler's optimization pass subsystem, covering the pass ordering, inlining mechanics, SROA (Scalar Replacement of Aggregates), and other key optimization passes.

**Files analyzed:**
- `Compiler/src/optimize.jl` (~1612 lines) - Optimization driver
- `Compiler/src/ssair/passes.jl` (~2715 lines) - Optimization passes
- `Compiler/src/ssair/inlining.jl` (~1800 lines) - Inlining pass

**Permalink base:** https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/

---

## 1. Pass Ordering

### 1.1 The `run_passes_ipo_safe` Function

The core optimization pipeline is defined in [`run_passes_ipo_safe`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L1044-L1076) (lines 1044-1076):

```julia
function run_passes_ipo_safe(
    ci::CodeInfo,
    sv::OptimizationState,
    optimize_until::Union{Nothing, Int, String} = nothing)

    __stage__ = 0  # used by @pass
    @pass "CC: CONVERT"   ir = convert_to_ircode(ci, sv)
    @pass "CC: SLOT2REG"  ir = slot2reg(ir, ci, sv)
    @pass "CC: COMPACT_1" ir = compact!(ir)
    @pass "CC: INLINING"  ir = ssa_inlining_pass!(ir, sv.inlining, ci.propagate_inbounds)
    @pass "CC: COMPACT_2" ir = compact!(ir)
    @pass "CC: SROA"      ir = sroa_pass!(ir, sv.inlining)
    @pass "CC: ADCE"      (ir, made_changes) = adce_pass!(ir, sv.inlining)
    if made_changes
        @pass "CC: COMPACT_3" ir = compact!(ir, true)
    end
    # ... verification ...
    return ir
end
```

### 1.2 Pass Execution Order

| Order | Pass Name | Function | Description |
|-------|-----------|----------|-------------|
| 1 | `CC: CONVERT` | `convert_to_ircode` | Convert `CodeInfo` to `IRCode` |
| 2 | `CC: SLOT2REG` | `slot2reg` | Convert slots to SSA registers |
| 3 | `CC: COMPACT_1` | `compact!` | First IR compaction |
| 4 | `CC: INLINING` | `ssa_inlining_pass!` | Inline function calls |
| 5 | `CC: COMPACT_2` | `compact!` | Second IR compaction |
| 6 | `CC: SROA` | `sroa_pass!` | Scalar Replacement of Aggregates |
| 7 | `CC: ADCE` | `adce_pass!` | Aggressive Dead Code Elimination |
| 8 | `CC: COMPACT_3` | `compact!` | Final compaction (conditional) |

### 1.3 The `@pass` Macro

The [`@pass`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L1028-L1038) macro (lines 1028-1038) provides:
- Execution time tracking via `@zone`
- Early exit support via `optimize_until` parameter
- Pass name registration in `ALL_PASS_NAMES`

---

## 2. Inlining Pass (ssair/inlining.jl)

### 2.1 Entry Point: `ssa_inlining_pass!`

[`ssa_inlining_pass!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L73-L81) (lines 73-81):

```julia
function ssa_inlining_pass!(ir::IRCode, state::InliningState, propagate_inbounds::Bool)
    # Phase 1: Analysis - identify inlining candidates
    @zone "CC: ANALYSIS" todo = assemble_inline_todo!(ir, state)
    isempty(todo) && return ir
    # Phase 2: Execution - perform actual inlining
    @zone "CC: EXECUTION" ir = batch_inline!(ir, todo, propagate_inbounds, state.interp)
    return ir
end
```

### 2.2 Inlining Decision Logic (Cost Model)

#### Cost Constants (types.jl, lines 11-13)

```julia
const InlineCostType = UInt16
const MAX_INLINE_COST = typemax(InlineCostType)  # 65535 - don't inline
const MIN_INLINE_COST = InlineCostType(10)       # always inline
```

#### Key Cost Parameters (types.jl)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `inline_nonleaf_penalty` | 1000 | Cost for non-inlineable function calls |
| `max_tuple_splat` | 32 | Maximum tuple size for splatting |

#### Cost Calculation Functions

1. **[`statement_cost`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L1347-L1452)** (optimize.jl:1347-1452):
   - Intrinsics: Uses `T_IFUNC_COST` lookup table
   - Builtins: Uses `T_FFUNC_COST` lookup table
   - `getfield`/`tuple`/`getglobal`: Cost 0 (cheap)
   - `memoryrefget`/`memoryref_isassigned`: 1 if known type, else `inline_nonleaf_penalty`
   - `:foreigncall`: Fixed cost of 20
   - `:invoke`: `UNKNOWN_CALL_COST` (20) unless Union{} return type

2. **[`statement_or_branch_cost`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L1454-L1475)** (optimize.jl:1454-1475):
   - Backward `GotoNode`: 40 (loop penalty)
   - Backward `GotoIfNot`: 40 (conditional loop penalty)
   - `EnterNode` (try/catch): `typemax(Int)` (never inline)

3. **[`inline_cost_model`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L1477-L1488)** (optimize.jl:1477-1488):
   - Sums statement costs with saturation
   - Returns `MAX_INLINE_COST` if threshold exceeded

#### Inlining Decision Functions

1. **[`src_inlining_policy`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L131-L152)** (optimize.jl:131-152):
   - Checks `@inline` annotation (`IR_FLAG_INLINE`)
   - Checks if source is inlineable via `is_inlineable`
   - Handles generators via `may_invoke_generator`

2. **[`analyze_method!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L870-L905)** (inlining.jl:870-905):
   - Validates argument count
   - Checks `match.fully_covers` for union split
   - Validates static parameters
   - Returns `InliningTodo` or `InvokeCase`

### 2.3 Inlining Execution

#### Data Structures

```julia
struct InliningTodo  # Line 10-27
    mi::MethodInstance
    ir::IRCode
    spec_info::SpecInfo
    di::DebugInfo
    linear_inline_eligible::Bool  # Single BB optimization
    effects::Effects
end

struct UnionSplit  # Line 55-63
    handled_all_cases::Bool
    fully_covered::Bool
    atype::DataType
    cases::Vector{InliningCase}
    bbs::Vector{Int}
end
```

#### Core Inlining Functions

1. **[`batch_inline!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L619-L688)** (inlining.jl:619-688):
   - Computes new CFG for multi-block inlinees
   - Handles union splits via `cfg_inline_unionsplit!`
   - Uses `IncrementalCompact` for IR modification

2. **[`ir_inline_item!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L360-L450)** (inlining.jl:360-450):
   - **Linear case** (single BB): Direct statement insertion
   - **Multi-BB case**: Uses PhiNode for return value merging
   - Handles boundscheck propagation via `adjust_boundscheck!`

3. **[`ssa_substitute_op!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L1740-L1800)** (inlining.jl:1740-1800):
   - Substitutes `Argument` nodes with actual arguments
   - Handles `:static_parameter` expansion
   - Processes `:foreigncall` type instantiation

4. **[`ir_inline_unionsplit!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L526-L617)** (inlining.jl:526-617):
   - Generates `isa` checks for union dispatch
   - Creates conditional branches for each case
   - Joins results via PhiNode

### 2.4 CFG Management

[`CFGInliningState`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/inlining.jl#L83-L105) (inlining.jl:83-105) tracks:
- `new_cfg_blocks`: New basic blocks being constructed
- `bb_rename`: Mapping from old to new block numbers
- `dead_blocks`: Blocks to be removed
- `split_targets`: Blocks that are split points

---

## 3. SROA Pass (Scalar Replacement of Aggregates)

### 3.1 Entry Point: `sroa_pass!`

[`sroa_pass!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L1264-L1579) (passes.jl:1264-1579):

```julia
function sroa_pass!(ir::IRCode, inlining::Union{Nothing,InliningState}=nothing)
    # Pass docstring (lines 1247-1263):
    # "getfield elimination pass, a.k.a. Scalar Replacements of Aggregates optimization.
    #  This pass is based on a local field analysis by def-use chain walking."
```

### 3.2 How Structs are Broken into Scalars

#### Def-Use Tracking

[`SSADefUse`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L28-L47) (passes.jl:28-47):

```julia
struct SSADefUse
    uses::Vector{SSAUse}  # getfield, isdefined, preserve, finalizer
    defs::Vector{Int}     # setfield! locations
end
```

Use kinds tracked:
- `GetfieldUse`: Field reads
- `IsdefinedUse`: Field existence checks
- `PreserveUse`: GC preservation in foreigncalls
- `FinalizerUse`: Finalizer registrations

#### Lifting Mechanism

1. **[`collect_leaves`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L187-L193)** (passes.jl:187-193):
   - Walks use-def chains through PhiNodes
   - Collects all allocation sites ("leaves")

2. **[`lift_leaves`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L409-L500)** (passes.jl:409-500):
   - For each leaf, computes the lifted value for a field
   - Handles `:new` expressions, `tuple` calls, and constants
   - Returns `LiftedLeaves` mapping

3. **[`perform_lifting!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L782-L880)** (passes.jl:782-880):
   - Creates new PhiNodes for lifted values
   - Handles the "all same value" optimization
   - Returns lifted value and phi nest for fixup

#### Mutable Struct Handling

[`sroa_mutables!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L1760-L1994) (passes.jl:1760-1994):
- Partitions uses by field
- Uses iterated dominance frontier for phi placement
- Replaces `getfield` with computed values
- Eliminates `setfield!` when all uses are resolved

### 3.3 Connection to Escape Analysis

SROA integrates with escape analysis for mutable struct optimization:

1. **[`validate_mutable_arg_escapes!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L776-L788)** (optimize.jl:776-788):
   - Validates that mutable arguments don't escape
   - Uses `EscapeAnalysis.analyze_escapes`

2. **Escape-based finalizer resolution** (passes.jl:1800-1817):
   ```julia
   estate = EscapeAnalysis.analyze_escapes(ir, nargs, ...)
   hasaliases = EscapeAnalysis.getaliases(SSAValue(defidx), estate) !== nothing
   einfo = estate[SSAValue(defidx)]
   if !hasaliases && EscapeAnalysis.has_no_escape(einfo)
       # Can inline finalizer
   end
   ```

---

## 4. Other Optimization Passes

### 4.1 Aggressive Dead Code Elimination (ADCE)

[`adce_pass!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L2099-L2253) (passes.jl:2099-2253):

**Key features:**
1. **Phi node simplification** (`reprocess_phi_node!`): Single-predecessor phi elimination
2. **Union phi narrowing**: Removes unused branches from union-typed phis
3. **Dead code removal**: Uses use-count tracking
4. **Phi cycle elimination**: Removes self-referential phi cycles
5. **Typeassert nullification**: Removes provably-true typeasserts

```julia
# Typeassert elimination (lines 2146-2152)
if is_known_call(stmt, typeassert, compact) && length(stmt.args) == 3
    ty, isexact = instanceof_tfunc(argextype(stmt.args[3], compact), true)
    if isexact && argextype(stmt.args[2], compact) <: ty
        delete_inst_here!(compact)
    end
end
```

### 4.2 Constant Propagation (via SROA)

The SROA pass performs constant propagation through:

1. **[`lift_comparison!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L547-L598)** (passes.jl:547-598):
   - Lifts `===`, `isa`, `isdefined` through PhiNodes
   - Replaces comparisons with constant booleans when possible

2. **[`fold_ifelse!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L1194-L1211)** (passes.jl:1194-1211):
   - Folds `Core.ifelse` with constant conditions
   - Handles `ifelse(cond, x, x)` -> `x`

### 4.3 getfield/setfield! Lowering

Within SROA (passes.jl:1322-1484):

```julia
# getfield handling
if is_known_call(stmt, getfield, compact)
    # ... field ordering checks ...
    field = try_compute_fieldidx_stmt(compact, stmt, struct_typ)
    leaves, visited_philikes = collect_leaves(...)
    lifted_result = lift_leaves(compact, field, leaves, ...)
    # Replace getfield with lifted value

# setfield! handling (mutable structs)
if is_known_call(stmt, setfield!, compact)
    # Track in defuses for later sroa_mutables!
    push!(defuse.defs, idx)
```

### 4.4 CFG Simplification

[`cfg_simplify!`](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/passes.jl#L2364-L2715) (passes.jl:2364-2715):

- Merges consecutive basic blocks with single successor/predecessor
- Drops empty basic blocks
- Renumbers blocks in DFS order
- Fixes up phi node edges

---

## 5. Important Functions (Key Function Reference)

### optimize.jl

| Line | Function | Description |
|------|----------|-------------|
| 102-104 | `inlining_cost`, `is_inlineable` | Query inlining cost |
| 131-152 | `src_inlining_policy` | Decide if source should be inlined |
| 334-367 | `new_expr_effect_flags` | Compute effect flags for `:new` |
| 370-446 | `stmt_effect_flags` | Compute statement effect flags |
| 472-526 | `argextype` | Get type of IR argument |
| 543-546 | `finishopt!` | Store optimization result |
| 686-706 | `refine_effects!` | Refine IPO effects post-optimization |
| 1020-1025 | `optimize` | Main optimization entry point |
| 1044-1076 | `run_passes_ipo_safe` | Pass ordering/execution |
| 1139-1317 | `convert_to_ircode` | CodeInfo to IRCode conversion |
| 1327-1337 | `slot2reg` | Slot to SSA conversion |
| 1347-1452 | `statement_cost` | Compute statement inline cost |
| 1477-1488 | `inline_cost_model` | Full function cost model |

### ssair/inlining.jl

| Line | Function | Description |
|------|----------|-------------|
| 73-81 | `ssa_inlining_pass!` | Main inlining pass entry |
| 109-119 | `inline_into_block!` | CFG management for inlining |
| 121-213 | `cfg_inline_item!` | Inline single call site CFG |
| 215-258 | `cfg_inline_unionsplit!` | Union split CFG construction |
| 321-349 | `ir_prepare_inlining!` | Prepare IR for inlining |
| 360-450 | `ir_inline_item!` | Inline single call |
| 526-617 | `ir_inline_unionsplit!` | Inline union split |
| 619-688 | `batch_inline!` | Batch process all inlining |
| 691-768 | `rewrite_apply_exprargs!` | Rewrite `_apply_iterate` calls |
| 825-853 | `resolve_todo` | Resolve inlining decision |
| 870-905 | `analyze_method!` | Analyze method for inlining |
| 1297-1361 | `compute_inlining_cases` | Compute union split cases |
| 1363-1372 | `handle_call!` | Handle generic call inlining |
| 1573-1618 | `assemble_inline_todo!` | Build inlining todo list |
| 1620-1626 | `linear_inline_eligible` | Check single-BB inlineability |
| 1740-1800 | `ssa_substitute_op!` | Substitute SSA values in inlined code |

### ssair/passes.jl

| Line | Function | Description |
|------|----------|-------------|
| 49-56 | `compute_live_ins` | Compute live-in blocks |
| 100-125 | `compute_value_for_use` | Find value at use site |
| 164-185 | `find_def_for_use` | Find dominating definition |
| 187-193 | `collect_leaves` | Collect allocation leaves |
| 276-348 | `walk_to_defs` | Walk def-use chains |
| 409-500 | `lift_leaves` | Lift field values |
| 547-640 | `lift_comparison!` | Lift comparisons through phis |
| 782-880 | `perform_lifting!` | Execute value lifting |
| 1264-1579 | `sroa_pass!` | SROA pass entry |
| 1760-1994 | `sroa_mutables!` | Handle mutable struct SROA |
| 2017-2035 | `canonicalize_typeassert!` | Canonicalize typeassert to PiNode |
| 2099-2253 | `adce_pass!` | ADCE pass entry |
| 2364-2715 | `cfg_simplify!` | CFG simplification |

---

## 6. Cross-References

### 6.1 SSA IR (ssair/ir.jl)

The optimization passes heavily use the SSA IR infrastructure:

- **`IRCode`**: Main IR representation (used throughout)
- **`IncrementalCompact`**: Incremental IR modification (optimize.jl:334, 481; passes.jl extensively)
- **`types(compact)`**: Type information access
- **`insert_node!`**: Node insertion
- **`compact!(ir)`**: IR compaction

### 6.2 Escape Analysis (ssair/EscapeAnalysis.jl)

Referenced in:
- optimize.jl:270 - Include statement
- optimize.jl:686-694 - Effect refinement with EA
- optimize.jl:776-788 - Mutable argument escape validation
- passes.jl:1800-1817 - Finalizer resolution with EA

Key functions:
- `EscapeAnalysis.analyze_escapes`
- `EscapeAnalysis.getaliases`
- `EscapeAnalysis.has_no_escape`
- `EscapeAnalysis.ArgEscapeCache`

### 6.3 Type Inference Results

The optimizer accesses inference results via:
- `InferenceResult.ipo_effects`: IPO effect information
- `InferenceResult.result`: Inferred return type
- `OptimizationState.stmt_info`: Per-statement call info
- `CallInfo` hierarchy: Method match information

---

## 7. IR Flags Reference

Defined in optimize.jl (lines 18-62):

| Flag | Value | Description |
|------|-------|-------------|
| `IR_FLAG_INBOUNDS` | 1 << 0 | `@inbounds` annotation |
| `IR_FLAG_INLINE` | 1 << 1 | `@inline` annotation |
| `IR_FLAG_NOINLINE` | 1 << 2 | `@noinline` annotation |
| `IR_FLAG_CONSISTENT` | 1 << 3 | `:consistent` effect |
| `IR_FLAG_EFFECT_FREE` | 1 << 4 | `:effect_free` effect |
| `IR_FLAG_NOTHROW` | 1 << 5 | `:nothrow` effect |
| `IR_FLAG_TERMINATES` | 1 << 6 | `:terminates` effect |
| `IR_FLAG_NOUB` | 1 << 10 | `:noub` effect |
| `IR_FLAG_NORTCALL` | 1 << 13 | `:nortcall` effect |
| `IR_FLAG_REFINED` | 1 << 16 | Type refined by optimization |
| `IR_FLAG_UNUSED` | 1 << 17 | No users, candidate for DCE |
| `IR_FLAG_EFIIMO` | 1 << 18 | Effect free if inaccessible mem only |

Combined flags:
- `IR_FLAGS_EFFECTS`: All effect flags combined
- `IR_FLAGS_REMOVABLE`: `EFFECT_FREE | NOTHROW | TERMINATES`
- `IR_FLAGS_NEEDS_EA`: Requires escape analysis

---

## Summary

The Julia compiler optimization subsystem implements a sophisticated multi-pass optimization pipeline:

1. **Conversion Phase**: CodeInfo to SSA IRCode with slot elimination
2. **Inlining Phase**: Cost-based inlining with union split support
3. **SROA Phase**: Aggregate decomposition with escape analysis integration
4. **DCE Phase**: Dead code elimination and phi simplification

The passes communicate through:
- IR flags for effect information
- Use-def chains for data flow
- CFG for control flow
- Escape analysis for memory safety

Key design principles:
- Incremental compaction for efficient IR modification
- Lazy dominator tree computation for performance
- Two-phase inlining (analysis then execution)
- Field-level tracking for mutable struct optimization
