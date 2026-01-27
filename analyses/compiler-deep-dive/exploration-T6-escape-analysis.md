# Julia Compiler Escape Analysis Subsystem - Exploration Report

## Overview

**File**: `Compiler/src/ssair/EscapeAnalysis.jl` (~1379 lines)

**Supporting File**: `Compiler/src/ssair/disjoint_set.jl` (~140 lines) - Provides the `IntDisjointSet` data structure for alias tracking

**Permalink base**: https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/ssair/EscapeAnalysis.jl

The escape analysis module is a self-contained `baremodule` that analyzes where values might "escape" during program execution. This information enables critical optimizations like allocation elimination and stack allocation.

---

## 1. Purpose: Why Escape Analysis?

### Connection to Allocation Elimination

Escape analysis answers a fundamental question: **Can an allocated object be replaced with stack allocation or eliminated entirely?**

An object can only be optimized away if it does not "escape" beyond certain boundaries:
- **No return escape**: The object is not returned to the caller
- **No thrown escape**: The object is not thrown as an exception
- **No arg escape**: The object is not visible to the caller as an argument

### Optimization Enablement

The analysis results are used in two main places:

1. **Effect Refinement** (`optimize.jl:690`): Determines if mutable allocations escape, enabling effect-free marking
2. **SROA Pass** (`passes.jl:1802`): Enables finalizer inlining and field-level optimization when allocations don't escape

---

## 2. Escape States

### The EscapeInfo Lattice (Lines 45-123)

`EscapeInfo` is the core lattice type with five properties:

| Property | Type | Description |
|----------|------|-------------|
| `Analyzed` | `Bool` | Whether this value has been analyzed (not formally part of lattice) |
| `ReturnEscape` | `Bool` | Whether value can escape via return statement |
| `ThrownEscape` | `BitSet` | SSA statement numbers where value can be thrown |
| `AliasInfo` | `Union{Bool, IndexableFields, Unindexable}` | Field/element alias information |
| `Liveness` | `BitSet` | SSA statement numbers where value must be live |

### Convenience Constructors (Lines 139-145)

| Constructor | Meaning |
|-------------|---------|
| `NotAnalyzed()` | Special bottom element indicating not yet analyzed |
| `NoEscape()` | Value does not escape anywhere (bottom-like) |
| `ArgEscape()` | Value is a function argument (visible to caller) |
| `ReturnEscape(pc)` | Value escapes via return at statement `pc` |
| `AllReturnEscape()` | Value may escape via return at any point |
| `ThrownEscape(pc)` | Value may be thrown at statement `pc` |
| `AllEscape()` | Value escapes everywhere (top element) |

### Lattice Constants

```julia
const BOT_THROWN_ESCAPE = BitSet()      # Never thrown
const TOP_THROWN_ESCAPE = BitSet(-1)    # May be thrown anywhere

const BOT_LIVENESS = BitSet()           # Never live
const TOP_LIVENESS = BitSet(-1:0)       # Live everywhere
const ARG_LIVENESS = BitSet(0)          # Live as argument (0 = argument marker)
```

### Predicate Functions (Lines 150-156)

| Function | Description |
|----------|-------------|
| `has_no_escape(x)` | No return, thrown, or arg escape |
| `has_arg_escape(x)` | `0 in x.Liveness` (argument visibility) |
| `has_return_escape(x)` | `x.ReturnEscape == true` |
| `has_thrown_escape(x)` | `!isempty(x.ThrownEscape)` |
| `has_all_escape(x)` | Top element (escapes everywhere) |

---

## 3. Analysis Algorithm

### Main Entry Point: `analyze_escapes` (Lines 560-652)

The analysis uses a **backward dataflow iteration** over the IR. Key steps:

1. Initialize `EscapeState` with arguments marked as `ArgEscape()` and other values as `NotAnalyzed()`
2. Compute try-catch regions for exception handling via `compute_frameinfo`
3. Iterate backward through statements until no changes occur
4. Handle exception escapes via `escape_exception!`

### Statement Handling (Lines 577-631)

| Statement Type | Handler | Escape Effect |
|----------------|---------|---------------|
| `:call` | `escape_call!` | Depends on callee |
| `:invoke` | `escape_invoke!` | Uses cached escape info |
| `:new`, `:splatnew` | `escape_new!` | Initializes field tracking |
| `:foreigncall` | `escape_foreigncall!` | Conservative escape |
| `ReturnNode` | Direct | `ReturnEscape(pc)` |
| `PhiNode` | `escape_edges!` | Creates aliases |
| `PiNode` | `escape_val_ifdefined!` | Propagates aliases |
| `GlobalRef` | Direct | `AllEscape` (top) |

### IR Constructs That Cause Escapes

| Construct | Escape Type | Reason |
|-----------|-------------|--------|
| Return statement | `ReturnEscape` | Value visible to caller |
| Exception throw | `ThrownEscape` | Value may be caught externally |
| Unknown function call | `AllEscape` | Conservative assumption |
| `GlobalRef` load | `AllEscape` | Global values escape everywhere |
| `foreigncall` with `Any` arg | `AllEscape` | C code may capture pointer |
| Function argument | `ArgEscape` | Visible to caller by definition |

### Alias Tracking (Lines 384, 450-477)

Aliases are tracked using a **disjoint-set (union-find)** data structure (`IntDisjointSet`). When escape info is updated, it propagates to all aliases in the same set.

Alias creation happens in:
- `PhiNode`: All incoming edges alias with the result
- `PiNode`/`UpsilonNode`: Value aliases with result
- `ifelse` builtin: Both branches may alias result
- Return value of call that may return an argument

---

## 4. Key Data Structures

### EscapeInfo (Lines 85-123)

```julia
struct EscapeInfo
    Analyzed::Bool
    ReturnEscape::Bool
    ThrownEscape::BitSet
    AliasInfo  # Union{IndexableFields, Unindexable, Bool}
    Liveness::BitSet
end
```

### AliasInfo Variants (Lines 164-172)

| Type | Description |
|------|-------------|
| `false` | Not yet analyzed |
| `true` | Cannot be analyzed (unknown type) |
| `IndexableFields` | Field aliases with known indices |
| `Unindexable` | Field aliases without index information |

### EscapeState (Lines 392-402)

```julia
struct EscapeState
    escapes::Vector{EscapeInfo}  # One per arg + SSA value
    aliasset::AliasSet           # Union-find for aliases
    nargs::Int                   # Number of arguments
end
```

### ArgEscapeCache (Lines 504-523)

Interprocedural escape information cached for callees:
```julia
struct ArgEscapeCache
    argescapes::Vector{ArgEscapeInfo}
    argaliases::Vector{ArgAliasing}
end
```

---

## 5. Important Functions (with Line Numbers)

### Core Analysis Functions

| Function | Lines | Description |
|----------|-------|-------------|
| `analyze_escapes` | 560-652 | Main entry point for escape analysis |
| `propagate_changes!` | 681-694 | Propagates escape/alias changes until convergence |
| `propagate_escape_change!` | 696-723 | Updates escape info and propagates to aliases |
| `propagate_alias_change!` | 745-756 | Merges alias sets using union-find |
| `propagate_liveness_change!` | 726-743 | Adds liveness at specific PC |

### Statement Handlers

| Function | Lines | Description |
|----------|-------|-------------|
| `escape_call!` | 1073-1099 | Handles generic `:call` expressions |
| `escape_invoke!` | 947-1004 | Handles `:invoke` with cached callee info |
| `escape_new!` | 1140-1205 | Handles `:new`/`:splatnew` allocations |
| `escape_foreigncall!` | 1027-1060 | Handles `:foreigncall` expressions |
| `escape_exception!` | 922-944 | Propagates escapes through try-catch regions |
| `compute_frameinfo` | 661-678 | Finds try-catch regions in IR |

### Builtin Handlers

| Function | Lines | Description |
|----------|-------|-------------|
| `escape_builtin!(::typeof(getfield), ...)` | 1254-1300 | Tracks field reads |
| `escape_builtin!(::typeof(setfield!), ...)` | 1302-1369 | Tracks field writes |
| `escape_builtin!(::typeof(tuple), ...)` | 1207-1210 | Treats as allocation |
| `escape_builtin!(::typeof(ifelse), ...)` | 1114-1130 | Handles conditional aliasing |
| `escape_builtin!(::typeof(typeassert), ...)` | 1132-1138 | Propagates alias through assertion |

### Utility Functions

| Function | Lines | Description |
|----------|-------|-------------|
| `iridx` | 425-435 | Converts IR element to analysis index |
| `irval` | 446-448 | Converts analysis index to IR element |
| `getaliases` | 450-472 | Retrieves all aliases for a value |
| `isaliased` | 474-477 | Checks if two values are aliased |
| `from_interprocedural` | 1012-1023 | Converts callee escape info to caller context |

---

## 6. Cross-References

### SSA IR Integration

- Uses `IRCode`, `SSAValue`, `Argument`, `PhiNode`, `PiNode`, etc. from `Core.IR`
- Imports type utilities from `Compiler`: `argextype`, `widenconst`, `singleton_type`
- Accesses IR flags: `IR_FLAG_NOTHROW` via `has_flag`

### Optimization Passes Usage

**Effect Refinement** (`optimize.jl:686-694`):
- Analyzes escapes to determine if mutable allocations can be considered effect-free
- Creates `ArgEscapeCache` for interprocedural analysis

**SROA/Finalizer Inlining** (`passes.jl:1800-1817`):
- Uses escape analysis to enable finalizer inlining when allocations don't escape
- Checks `has_no_escape` and absence of aliases before optimization

### Interprocedural Analysis

The `get_escape_cache` callback retrieves `ArgEscapeCache` for called methods, enabling escape information to flow across function boundaries. The `from_interprocedural` function (line 1012) translates callee escape info to the caller's context.

---

## 7. Design Characteristics

- **Backward Analysis**: Iterates from last statement to first, natural for escape analysis
- **Monotonic Lattice**: States only move from bottom (`NoEscape`) toward top (`AllEscape`), ensuring termination
- **Conservative Defaults**: Unknown situations default to `AllEscape` for soundness
- **Field-Sensitive**: The `AliasInfo` component tracks field-level aliasing for precise analysis

---

## 8. Exported API

```julia
export
    analyze_escapes,   # Main analysis function
    getaliases,        # Get all aliases of a value
    isaliased,         # Check if two values alias
    has_no_escape,     # Predicate: no escape at all
    has_arg_escape,    # Predicate: escapes as argument
    has_return_escape, # Predicate: escapes via return
    has_thrown_escape, # Predicate: escapes via throw
    has_all_escape     # Predicate: escapes everywhere
```
