# Exploration T8: Julia Compiler Caching and Invalidation Subsystem

## Overview

This exploration examines Julia's compiler caching and invalidation mechanism, which is fundamental to Julia's just-in-time compilation strategy. The system maintains compiled code across method redefinitions while ensuring correctness through careful tracking of dependencies and world ages.

**Permalink base**: https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/

**Files Analyzed**:
- `Compiler/src/cicache.jl` (~71 lines) - CodeInstance cache abstraction
- `Compiler/src/reinfer.jl` (~658 lines) - Re-inference and validation utilities
- `Compiler/src/bindinginvalidations.jl` (~202 lines) - Binding invalidation
- `Compiler/src/methodtable.jl` (~159 lines) - Method table queries

---

## 1. CodeInstance Lifecycle

### What is a CodeInstance?

A `CodeInstance` (defined in `Core`) represents compiled code for a specific `MethodInstance`. It contains:

- **Inferred type information**: Return type, exception type, and constant results
- **Compiled code**: Native code pointer or intermediate representation
- **World age bounds**: `min_world` and `max_world` defining validity range
- **Edges**: Dependencies on other methods, bindings, and method tables
- **Effects**: Information about purity, termination, and other properties

The relationship between key structures:
```
Method (generic function definition)
   |
   +-- MethodInstance (specialized for specific type signature)
          |
          +-- CodeInstance (compiled code with world age validity)
                 |
                 +-- CodeInstance.next (linked list for different world ranges)
```

### Creation and Caching

CodeInstance creation occurs during type inference completion in `typeinfer.jl:102-198`. The `finish!` function fills the CodeInstance with inferred information via `ccall(:jl_fill_codeinst, ...)` and `ccall(:jl_update_codeinst, ...)`.

Cache insertion is handled by the `InternalCodeCache` abstraction in [cicache.jl:44-52](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/cicache.jl#L44-L52):

```julia
function setindex!(cache::InternalCodeCache, ci::CodeInstance, mi::MethodInstance)
    @assert ci.owner === cache.owner
    m = mi.def
    if isa(m, Method)
        ccall(:jl_push_newly_inferred, Cvoid, (Any,), ci)
    end
    ccall(:jl_mi_cache_insert, Cvoid, (Any, Any), mi, ci)
    return cache
end
```

### Cache Lookup

Cache lookup via `get()` in [cicache.jl:58-70](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/cicache.jl#L58-L70) uses `ccall(:jl_rettype_inferred, ...)` to find a CodeInstance valid for the requested world range.

---

## 2. World Age System

### WorldRange Structure

From [cicache.jl:3-28](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/cicache.jl#L3-L28):

```julia
struct WorldRange
    min_world::UInt
    max_world::UInt
end
```

Key operations: `in(world, wr)`, `intersect(a, b)`, `union(a, b)`

### How World Age Affects Caching

Each `CodeInstance` has `(min_world, max_world)`:
- **min_world**: First world where this compiled code is valid
- **max_world**: Last world where valid; `typemax(UInt)` means valid "forever"

### World Age Increment Triggers

1. Method definition/redefinition
2. Type definition
3. Global binding changes

The sentinel `WORLD_AGE_REVALIDATION_SENTINEL = 1` marks CodeInstances needing revalidation.

---

## 3. Invalidation Mechanisms

### Method-Based Invalidation

Dispatch status flags from [reinfer.jl:617-621](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/reinfer.jl#L617-L621):
- `METHOD_SIG_LATEST_WHICH = 0x1` - Method returned by `which` for its signature
- `METHOD_SIG_LATEST_ONLY = 0x2` - Method is the only result from `methods`

The `verify_call()` function in [reinfer.jl:467-615](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/reinfer.jl#L467-L615) validates dispatch edges using fast-path checks when possible, falling back to full method lookup comparison.

### Binding Invalidation

The `invalidate_code_for_globalref!` function in [bindinginvalidations.jl:90-163](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/bindinginvalidations.jl#L90-L163):
1. Checks if binding change affects inference results via `abstract_eval_partition_load`
2. Invalidates methods using the GlobalRef
3. Invalidates CodeInstances with explicit binding edges
4. Propagates to modules that `using` the binding

### Invalidation Propagation via Backedges

The backedge system in `typeinfer.jl:786-813` enables reverse dependency tracking:
- Method Instance Backedges: `jl_method_instance_add_backedge`
- Binding Backedges: `maybe_add_binding_backedge!`
- Method Table Backedges: `jl_method_table_add_backedge`

---

## 4. Re-inference and Validation

### When Re-inference is Needed

1. Loading precompiled code requiring validation
2. Invalidation with partial recovery
3. Code instrumentation (coverage/malloc logging)

### The Verification System

Main entry `insert_backedges()` in [reinfer.jl:71-79](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/reinfer.jl#L71-L79) scans new methods and validates CodeInstances.

The `verify_method()` function in [reinfer.jl:160-389](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/reinfer.jl#L160-L389) implements Tarjan's SCC algorithm with stages:
- `:init_and_process_callees` - Initialize and validate non-CodeInstance edges
- `:recursive_phase` - Recursively verify CodeInstance edges
- `:cleanup` - Handle cycle completion
- `:return_to_parent` - Propagate results upward

---

## 5. Method Table Queries

### MethodTableView Hierarchy

From [methodtable.jl:19-59](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/methodtable.jl#L19-L59):
- `InternalMethodTable` - World-stamped method table view
- `OverlayMethodTable` - Method table with overlay support
- `CachedMethodTable` - Cached wrapper for method tables

### Query Functions

- `findall()` - Find all matching methods, returns `MethodLookupResult`
- `findsup()` - Find most specific method (used for `invoke`)

---

## 6. Important Functions Reference

### cicache.jl
| Function | Line | Description |
|----------|------|-------------|
| `WorldRange` | 3-28 | World age range representation |
| `InternalCodeCache` | 30-42 | Cache abstraction with owner and world range |
| `setindex!` | 44-52 | Insert CodeInstance into cache |
| `get` | 58-64 | Retrieve CodeInstance from cache |

### reinfer.jl
| Function | Line | Description |
|----------|------|-------------|
| `insert_backedges` | 71-79 | Main entry for backedge restoration |
| `verify_method_graph` | 95-109 | Top-level graph verification |
| `verify_method` | 160-389 | Iterative Tarjan-based verification |
| `verify_call` | 467-615 | Validate dispatch edge |
| `verify_invokesig` | 623-652 | Validate invoke edge |

### bindinginvalidations.jl
| Function | Line | Description |
|----------|------|-------------|
| `invalidate_method_for_globalref!` | 56-83 | Invalidate method's CodeInstances |
| `invalidate_code_for_globalref!` | 90-163 | Main binding invalidation logic |
| `scan_new_method!` | 171-189 | Scan method source for GlobalRefs |

### methodtable.jl
| Function | Line | Description |
|----------|------|-------------|
| `findall` | 60-113 | Find all matching methods |
| `findsup` | 115-155 | Find most specific method |

---

## 7. Cross-References

### Type Inference Integration
- `finish!` in `typeinfer.jl` fills CodeInstance with inference results
- `promotecache!` inserts into global cache
- `store_backedges` registers dependencies for invalidation

### Core Runtime Structures (C Functions)
- `jl_rettype_inferred` - Lookup CodeInstance
- `jl_mi_cache_insert` - Insert CodeInstance
- `jl_invalidate_code_instance` - Mark as invalid
- `jl_promote_ci_to_current` - Finalize world age
- `jl_method_instance_add_backedge` - Add method backedge
- `jl_maybe_add_binding_backedge` - Add binding backedge

---

## 8. Summary

Julia's caching and invalidation system balances correctness with performance through:

1. **World Age Stratification**: Every CodeInstance valid only within a specific world range
2. **Backedge-Based Invalidation**: Reverse dependencies tracked for correct propagation
3. **Lazy Revalidation**: Precompiled code validated on-demand using Tarjan's SCC algorithm
4. **Binding Awareness**: Global variable changes trigger appropriate invalidations
5. **Method Table Integration**: Dispatch queries return world-valid results

This system enables Julia's unique combination of dynamic semantics with static compilation performance.
