# Julia Compiler Effects System Exploration

**Subsystem**: Effects System
**Primary File**: `Compiler/src/effects.jl` (~365 lines)
**Related Files**: `abstractinterpretation.jl`, `tfuncs.jl`, `optimize.jl`, `typeinfer.jl`
**Permalink Base**: https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/

---

## 1. Overview

The Effects system tracks computational properties of method calls during abstract interpretation. These properties enable critical optimizations like constant folding, dead code elimination, and determining whether expressions can be safely reordered or removed.

Effects are analyzed locally at each statement and merged into a global `Effects` object representing the entire method's behavior. The analysis is flow-insensitive, meaning effects detected at any statement conservatively taint the global conclusion.

---

## 2. The Effects Struct

**Location**: [effects.jl:119-150](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L119-L150)

```julia
struct Effects
    consistent::UInt8
    effect_free::UInt8
    nothrow::Bool
    terminates::Bool
    notaskstate::Bool
    inaccessiblememonly::UInt8
    noub::UInt8
    nonoverlayed::UInt8
    nortcall::Bool
end
```

### 2.1 Effect Fields Documentation

| Field | Type | Description |
|-------|------|-------------|
| `consistent` | `UInt8` | Method returns/terminates consistently (same inputs produce same outputs) |
| `effect_free` | `UInt8` | Method is free from externally semantically visible side effects |
| `nothrow` | `Bool` | Method is guaranteed not to throw an exception |
| `terminates` | `Bool` | Method is guaranteed to terminate |
| `notaskstate` | `Bool` | Method does not access state bound to the current task |
| `inaccessiblememonly` | `UInt8` | Method only accesses inaccessible memory (like stack allocations) |
| `noub` | `UInt8` | Method is guaranteed not to execute undefined behavior |
| `nonoverlayed` | `UInt8` | Method does not invoke overlayed methods from overlay method tables |
| `nortcall` | `Bool` | Method does not call `Core.Compiler.return_type` |

---

## 3. Effect Values

### 3.1 Binary Effects (Bool)

These effects have simple true/false values:
- `nothrow`: `true` = guaranteed no throw, `false` = may throw
- `terminates`: `true` = guaranteed termination, `false` = may not terminate
- `notaskstate`: `true` = no task state access, `false` = may access task state
- `nortcall`: `true` = no return_type calls, `false` = may call return_type

### 3.2 Multi-State Effects (UInt8)

**Location**: [effects.jl:152-176](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L152-L176)

#### Base Constants
```julia
const ALWAYS_TRUE  = 0x00
const ALWAYS_FALSE = 0x01
```

#### consistent (bits 0-2)
| Value | Constant | Meaning |
|-------|----------|---------|
| `0x00` | `ALWAYS_TRUE` | Guaranteed consistent |
| `0x01` | `ALWAYS_FALSE` | May be inconsistent |
| `0x02` | `CONSISTENT_IF_NOTRETURNED` | Consistent if return value doesn't escape newly allocated mutable objects |
| `0x04` | `CONSISTENT_IF_INACCESSIBLEMEMONLY` | Consistent if `:inaccessiblememonly` is proven |

#### effect_free (bits 0-1)
| Value | Constant | Meaning |
|-------|----------|---------|
| `0x00` | `ALWAYS_TRUE` | Completely effect-free |
| `0x01` | `ALWAYS_FALSE` | May have side effects |
| `0x02` | `EFFECT_FREE_IF_INACCESSIBLEMEMONLY` | Effect-free if `:inaccessiblememonly` is proven |
| `0x03` | `EFFECT_FREE_GLOBALLY` | Effect-free globally but not removable from function |

#### inaccessiblememonly (bits 0-1)
| Value | Constant | Meaning |
|-------|----------|---------|
| `0x00` | `ALWAYS_TRUE` | Only accesses inaccessible memory (corresponds to LLVM's `inaccessiblememonly`) |
| `0x01` | `ALWAYS_FALSE` | May access external memory |
| `0x02` | `INACCESSIBLEMEM_OR_ARGMEMONLY` | Only accesses inaccessible memory or argument memory (LLVM's `inaccessiblemem_or_argmemonly`) |

#### noub (bits 0-1)
| Value | Constant | Meaning |
|-------|----------|---------|
| `0x00` | `ALWAYS_TRUE` | No undefined behavior |
| `0x01` | `ALWAYS_FALSE` | May have undefined behavior |
| `0x02` | `NOUB_IF_NOINBOUNDS` | No UB assuming `@boundscheck` is not elided |

#### nonoverlayed (bits 0-1)
| Value | Constant | Meaning |
|-------|----------|---------|
| `0x00` | `ALWAYS_TRUE` | No overlayed methods invoked |
| `0x01` | `ALWAYS_FALSE` | May invoke overlayed methods |
| `0x02` | `CONSISTENT_OVERLAY` | May invoke overlays, but they are `:consistent` with originals |

---

## 4. Predefined Effect Constants

**Location**: [effects.jl:178-181](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L178-L181)

```julia
const EFFECTS_TOTAL   = Effects(ALWAYS_TRUE,  ALWAYS_TRUE,  true,  true,  true,  ALWAYS_TRUE,  ALWAYS_TRUE,  ALWAYS_TRUE, true)
const EFFECTS_THROWS  = Effects(ALWAYS_TRUE,  ALWAYS_TRUE,  false, true,  true,  ALWAYS_TRUE,  ALWAYS_TRUE,  ALWAYS_TRUE, true)
const EFFECTS_UNKNOWN = Effects(ALWAYS_FALSE, ALWAYS_FALSE, false, false, false, ALWAYS_FALSE, ALWAYS_FALSE, ALWAYS_TRUE, false)
```

| Constant | Description |
|----------|-------------|
| `EFFECTS_TOTAL` | Completely pure function (all effects are positive) |
| `EFFECTS_THROWS` | Pure except may throw |
| `EFFECTS_UNKNOWN` | Unknown effects (conservative default, but not overlayed) |

---

## 5. Effect Combination (Merging)

### 5.1 merge_effects Function

**Location**: [effects.jl:275-286](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L275-L286)

Effects are combined when composing code (e.g., merging callee effects into caller):

```julia
function merge_effects(old::Effects, new::Effects)
    return Effects(
        merge_effectbits(old.consistent, new.consistent),
        merge_effectbits(old.effect_free, new.effect_free),
        merge_effectbits(old.nothrow, new.nothrow),
        # ... etc for all fields
    )
end
```

### 5.2 merge_effectbits Logic

**Location**: [effects.jl:288-294](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L288-L294)

```julia
function merge_effectbits(old::UInt8, new::UInt8)
    if old === ALWAYS_FALSE || new === ALWAYS_FALSE
        return ALWAYS_FALSE  # Once tainted, always tainted
    end
    return old | new  # Accumulate conditional bits
end

merge_effectbits(old::Bool, new::Bool) = old & new  # AND for boolean effects
```

**Key insight**:
- `UInt8` effects: If either is `ALWAYS_FALSE`, result is `ALWAYS_FALSE`. Otherwise, OR the bits.
- `Bool` effects: Simple AND (both must be true for result to be true).

### 5.3 merge_effects! (Global Effect Accumulation)

**Location**: [inferencestate.jl:1060-1067](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/inferencestate.jl#L1060-L1067)

```julia
function merge_effects!(::AbstractInterpreter, caller::InferenceState, effects::Effects)
    if effects.effect_free === EFFECT_FREE_GLOBALLY
        effects = Effects(effects; effect_free=ALWAYS_TRUE)
    end
    caller.ipo_effects = merge_effects(caller.ipo_effects, effects)
    nothing
end
```

This function merges statement-level effects into the method's inter-procedural (IPO) effects.

---

## 6. Effect Inference During Compilation

### 6.1 Initialization

**Location**: [inferencestate.jl:375-397](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/inferencestate.jl#L375-L397)

Effects are initialized to `EFFECTS_TOTAL` (best case) and progressively tainted:

```julia
ipo_effects = EFFECTS_TOTAL
# Special cases taint immediately:
if method.isva
    ipo_effects = Effects(ipo_effects; effect_free = ALWAYS_FALSE)
end
```

### 6.2 Statement-Level Effect Analysis

During abstract interpretation, each statement's effects are computed and merged:

1. **Call statements**: Effects come from `abstract_call_known` or `abstract_call_unknown`
2. **Builtin operations**: Effects from `builtin_effects` ([tfuncs.jl:2631-2709](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/tfuncs.jl#L2631-L2709))
3. **Intrinsics**: Effects from `intrinsic_effects` ([tfuncs.jl:3060-3079](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/tfuncs.jl#L3060-L3079))

### 6.3 Effect Override System

**Location**: [abstractinterpretation.jl:3583-3605](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/abstractinterpretation.jl#L3583-L3605)

Effects can be overridden via `@assume_effects`:

```julia
function override_effects(effects::Effects, override::EffectsOverride)
    return Effects(effects;
        consistent = override.consistent ? ALWAYS_TRUE : effects.consistent,
        effect_free = override.effect_free ? ALWAYS_TRUE : effects.effect_free,
        nothrow = override.nothrow ? true : effects.nothrow,
        # ... etc
    )
end
```

### 6.4 Post-Inference Refinement

**Location**: [typeinfer.jl:567-611](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typeinfer.jl#L567-L611)

After inference, effects may be refined based on inferred types:

```julia
# Example: Refine consistency based on return type
if is_consistent_if_notreturned(ipo_effects) && is_identity_free_argtype(rt)
    consistent = ipo_effects.consistent & ~CONSISTENT_IF_NOTRETURNED
    ipo_effects = Effects(ipo_effects; consistent)
end
```

---

## 7. Important Functions

### 7.1 Core Effect Functions (effects.jl)

| Function | Line | Description |
|----------|------|-------------|
| `Effects` (constructor) | [129-150](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L129-L150) | Primary constructor |
| `Effects` (keyword) | [182-203](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L182-L203) | Keyword argument constructor for modification |
| `is_better_effects` | [205-273](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L205-L273) | Compare if one Effects is strictly better |
| `merge_effects` | [275-286](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L275-L286) | Combine two Effects |
| `merge_effectbits` | [288-294](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L288-L294) | Combine individual effect bits |

### 7.2 Effect Query Functions (effects.jl:296-336)

| Function | Line | Description |
|----------|------|-------------|
| `is_consistent` | [296](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L296) | Check if `consistent === ALWAYS_TRUE` |
| `is_effect_free` | [297](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L297) | Check if `effect_free === ALWAYS_TRUE` |
| `is_nothrow` | [298](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L298) | Check if `nothrow === true` |
| `is_terminates` | [299](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L299) | Check if `terminates === true` |
| `is_notaskstate` | [300](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L300) | Check if `notaskstate === true` |
| `is_inaccessiblememonly` | [301](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L301) | Check if `inaccessiblememonly === ALWAYS_TRUE` |
| `is_noub` | [302](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L302) | Check if `noub === ALWAYS_TRUE` |
| `is_nonoverlayed` | [304](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L304) | Check if `nonoverlayed === ALWAYS_TRUE` |
| `is_nortcall` | [305](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L305) | Check if `nortcall === true` |

### 7.3 Compound Effect Checks (effects.jl:308-327)

| Function | Line | Description |
|----------|------|-------------|
| `is_foldable` | [308-313](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L308-L313) | Can be constant-folded (consistent + no UB + effect_free + terminates) |
| `is_foldable_nothrow` | [315-317](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L315-L317) | Foldable and won't throw |
| `is_removable_if_unused` | [320-323](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L320-L323) | Can be DCE'd (effect_free + terminates + nothrow) |
| `is_finalizer_inlineable` | [325-327](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L325-L327) | Finalizer can be inlined (nothrow + notaskstate) |

### 7.4 Encoding/Decoding (effects.jl:339-365)

| Function | Line | Description |
|----------|------|-------------|
| `encode_effects` | [339-349](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L339-L349) | Pack Effects into UInt32 for storage |
| `decode_effects` | [351-362](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L351-L362) | Unpack UInt32 to Effects |

### 7.5 Effect Inference Functions (tfuncs.jl)

| Function | Line | Description |
|----------|------|-------------|
| `builtin_effects` | [2631-2709](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/tfuncs.jl#L2631-L2709) | Compute effects for builtin function calls |
| `getfield_effects` | [2520-2558](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/tfuncs.jl#L2520-L2558) | Effects for getfield operations |
| `isdefined_effects` | [2494-2518](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/tfuncs.jl#L2494-L2518) | Effects for isdefined checks |
| `intrinsic_effects` | [3060-3079](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/tfuncs.jl#L3060-L3079) | Effects for intrinsic functions |

---

## 8. Cross-References

### 8.1 Type Inference Integration

**InferenceState stores effects**: [inferencestate.jl:303](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/inferencestate.jl#L303)
```julia
ipo_effects::Effects  # Inter-procedural effects for the method
```

**InferenceResult stores final effects**: [types.jl:127](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/types.jl#L127)
```julia
ipo_effects::Effects  # Final inferred effects
```

**CallMeta carries effects through call analysis**: [abstractinterpretation.jl:96-104](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/abstractinterpretation.jl#L96-L104)

### 8.2 Optimization Integration

**IR Flags for Effects**: [optimize.jl:18-60](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L18-L60)

```julia
const IR_FLAG_CONSISTENT  = one(UInt32) << 3
const IR_FLAG_EFFECT_FREE = one(UInt32) << 4
const IR_FLAG_NOTHROW     = one(UInt32) << 5
const IR_FLAG_TERMINATES  = one(UInt32) << 6
const IR_FLAG_NOUB        = one(UInt32) << 10
const IR_FLAG_NORTCALL    = one(UInt32) << 13

const IR_FLAGS_EFFECTS = IR_FLAG_CONSISTENT | IR_FLAG_EFFECT_FREE | IR_FLAG_NOTHROW |
                         IR_FLAG_TERMINATES | IR_FLAG_NOUB | IR_FLAG_NORTCALL

const IR_FLAGS_REMOVABLE = IR_FLAG_EFFECT_FREE | IR_FLAG_NOTHROW | IR_FLAG_TERMINATES
```

**flags_for_effects conversion**: [optimize.jl:72-98](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/optimize.jl#L72-L98)

This function converts `Effects` to IR flags for per-statement optimization:

```julia
function flags_for_effects(effects::Effects)
    flags = zero(UInt32)
    if is_consistent(effects)
        flags |= IR_FLAG_CONSISTENT
    end
    if is_effect_free(effects)
        flags |= IR_FLAG_EFFECT_FREE
    elseif is_effect_free_if_inaccessiblememonly(effects)
        flags |= IR_FLAG_EFIIMO
    end
    # ... etc
    return flags
end
```

### 8.3 Optimizations Enabled by Effects

| Effect | Optimization Enabled |
|--------|---------------------|
| `effect_free + nothrow + terminates` | Dead code elimination (`is_removable_if_unused`) |
| `consistent + effect_free + terminates + noub` | Constant folding (`is_foldable`) |
| `nothrow + notaskstate` | Finalizer inlining (`is_finalizer_inlineable`) |
| `effect_free + inaccessiblememonly` | Escape analysis refinements |
| `consistent` | Common subexpression elimination |
| `nothrow` | Exception handler simplification |

### 8.4 Concrete Evaluation

**Location**: [abstractinterpretation.jl:938-948](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/abstractinterpretation.jl#L938-L948)

When effects permit, the compiler can evaluate calls at compile time:

```julia
if result.edge !== nothing && is_foldable(effects, #=check_rtcall=#true)
    if (is_nonoverlayed(interp) || is_nonoverlayed(effects) ||
        is_consistent_overlay(effects))
        # Can perform concrete evaluation
    end
end
```

---

## 9. Effect Display Format

**Location**: [effects.jl:1-38](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/effects.jl#L1-L38)

Effects are displayed as a compact string: `+c+e+n+t+s+m+u+o+r`

| Symbol | Effect | `+` (green) | `-` (red) | `?` (yellow) |
|--------|--------|-------------|-----------|--------------|
| `c` | consistent | `ALWAYS_TRUE` | `ALWAYS_FALSE` | conditional |
| `e` | effect_free | `ALWAYS_TRUE` | `ALWAYS_FALSE` | conditional |
| `n` | nothrow | `true` | `false` | - |
| `t` | terminates | `true` | `false` | - |
| `s` | notaskstate | `true` | `false` | - |
| `m` | inaccessiblememonly | `ALWAYS_TRUE` | `ALWAYS_FALSE` | `INACCESSIBLEMEM_OR_ARGMEMONLY` |
| `u` | noub | `ALWAYS_TRUE` | `ALWAYS_FALSE` | `NOUB_IF_NOINBOUNDS` |
| `o` | nonoverlayed | `ALWAYS_TRUE` | `ALWAYS_FALSE` | `CONSISTENT_OVERLAY` |
| `r` | nortcall | `true` | `false` | - |

---

## 10. Architecture Diagram

```
                    +------------------+
                    |  @assume_effects |
                    | (user overrides) |
                    +--------+---------+
                             |
                             v
+----------------+   +-------+--------+   +------------------+
| builtin_effects|-->|  merge_effects!|<--| intrinsic_effects|
| (tfuncs.jl)    |   | (per statement)|   | (tfuncs.jl)      |
+----------------+   +-------+--------+   +------------------+
                             |
                             v
                    +--------+---------+
                    | ipo_effects      |
                    | (InferenceState) |
                    +--------+---------+
                             |
                             v
                    +--------+---------+
                    | adjust_effects   |
                    | (typeinfer.jl)   |
                    +--------+---------+
                             |
            +----------------+----------------+
            v                                 v
    +-------+--------+               +--------+-------+
    | encode_effects |               | flags_for_     |
    | (CodeInstance) |               | effects (IR)   |
    +----------------+               +--------+-------+
                                              |
                                              v
                                     +--------+-------+
                                     | Optimizations  |
                                     | - DCE          |
                                     | - Const fold   |
                                     | - Inlining     |
                                     +----------------+
```

---

## 11. Key Insights

1. **Monotonic Tainting**: Effects start at the best state (`EFFECTS_TOTAL`) and can only get worse during analysis. Once an effect is tainted to `ALWAYS_FALSE`, it cannot be refined.

2. **Conditional Effects**: The `_IF_*` variants allow deferred decisions. For example, `CONSISTENT_IF_NOTRETURNED` means consistency depends on whether the return value escapes mutable allocations.

3. **Flow-Insensitive Analysis**: Effects are conservative across all paths. A single throwing statement taints `nothrow` for the entire method.

4. **Inter-Procedural**: Effects of called functions are merged into the caller's effects, enabling whole-program optimization.

5. **Encoding Efficiency**: Effects are packed into a `UInt32` for storage in `CodeInstance`, saving memory while preserving all information.

6. **Separation of Concerns**: `Effects` tracks properties, `IR_FLAG_*` enables per-statement optimization, and `EffectsOverride` allows user assertions.
