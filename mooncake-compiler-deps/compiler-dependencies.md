# Mooncake.jl Compiler Dependencies

Mooncake performs source-to-source automatic differentiation by deeply integrating with Julia's compiler infrastructure. This document maps the specific dependencies.

## Overview

| Capability | Fragility | Julia Files | Mooncake Files |
|------------|-----------|-------------|----------------|
| OpaqueClosure | Critical | 3 | 5 |
| AbstractInterpreter | High | 14 | 2 |
| IRCode/CFG | High | 6 | 5 |
| Optimization | Medium | 3 | 2 |

---

## 1. OpaqueClosure Generation (Critical)

Mooncake generates differentiated functions as OpaqueClosures from transformed IR.

### Julia Source
```
Compiler/src/opaque_closure.jl    # compute_ir_rettype, compute_oc_signature
base/opaque_closure.jl            # generate_opaque_closure
```

### Mooncake Usage
```julia
# src/utils.jl:352
Base.Experimental.generate_opaque_closure(...)

# src/utils.jl:381-385
CC.compute_ir_rettype(ir)
CC.compute_oc_signature(...)
```

### Known Breakage Patterns
- **World-age mismatch**: Methods defined between IR generation and OC creation
- **Signature validation**: Changed in Julia 1.12
- **DebugInfo format**: LineInfoNode → DebugInfoStream in Julia 1.12

---

## 2. AbstractInterpreter (High)

`MooncakeInterpreter` extends `CC.AbstractInterpreter` for custom type inference.

### Julia Source
```
Compiler/src/types.jl                    # AbstractInterpreter, InferenceParams, OptimizationParams
Compiler/src/abstractinterpretation.jl   # abstract_call_gf_by_type, find_method_matches
Compiler/src/inferencestate.jl           # InferenceState, AbsIntState
Compiler/src/typeinfer.jl                # typeinf_type, typeinf_ircode
Compiler/src/methodtable.jl              # OverlayMethodTable, MethodLookupResult
Compiler/src/stmtinfo.jl                 # CallInfo, add_edges_impl
Compiler/src/cicache.jl                  # WorldView, WorldRange
```

### Mooncake Usage
```julia
# src/interpreter/abstract_interpretation.jl:27
struct MooncakeInterpreter <: CC.AbstractInterpreter
    ...
end

# Key overloads:
CC.InferenceParams(interp::MooncakeInterpreter)
CC.OptimizationParams(interp::MooncakeInterpreter)
CC.method_table(interp::MooncakeInterpreter)
CC.inlining_policy(interp::MooncakeInterpreter)
```

### Known Breakage Patterns
- `get_world_counter` → `get_inference_world` in Julia 1.11
- `add_edges_impl` new API in Julia 1.12
- `find_matching_methods` signature change in Julia 1.12

---

## 3. IRCode/CFG Manipulation (High)

Mooncake transforms IR through basic block operations (BBCode).

### Julia Source
```
Compiler/src/ssair/ir.jl           # IRCode, InstructionStream, NewInstruction, compact!
Compiler/src/ssair/basicblock.jl   # BasicBlock, StmtRange, CFG
Compiler/src/ssair/verify.jl       # verify_ir
```

### Mooncake Usage
```julia
# src/interpreter/ir_utils.jl
CC.IRCode(...)              # Create IR
CC.compact!(ir)             # Compact after transformations
CC.verify_ir(ir)            # Validate IR structure
CC.compute_basic_blocks(stmts)

# src/interpreter/bbcode.jl
CC.CFG(...)                 # Control flow graph
CC.BasicBlock(...)          # Basic blocks
```

### Known Breakage Patterns
- `InstructionStream` field: `.inst` → `.stmt` in Julia 1.11
- `DebugInfoStream` introduced in Julia 1.12
- `valid_worlds` field added to IRCode in Julia 1.12

---

## 4. Optimization Passes (Medium)

Mooncake applies compiler optimization passes to transformed IR.

### Julia Source
```
Compiler/src/optimize.jl         # InliningState, ir_to_codeinf!
Compiler/src/ssair/inlining.jl   # ssa_inlining_pass!
Compiler/src/ssair/passes.jl     # sroa_pass!, adce_pass!
```

### Mooncake Usage
```julia
# src/interpreter/ir_utils.jl:192-202
CC.InliningState(interp, ...)
CC.ssa_inlining_pass!(ir, state)
CC.sroa_pass!(ir, state)
CC.adce_pass!(ir, state)
```

### Known Breakage Patterns
- `adce_pass!` return value changed in Julia 1.11

---

## Dependency Matrix

| Mooncake File | Lines | Primary Julia Dependencies |
|---------------|-------|---------------------------|
| `src/interpreter/abstract_interpretation.jl` | 45 | types.jl, methodtable.jl, typeinfer.jl |
| `src/interpreter/patch_for_319.jl` | 54 | optimize.jl, inferencestate.jl, ssair/irinterp.jl |
| `src/interpreter/ir_utils.jl` | 35 | ssair/ir.jl, types.jl, optimize.jl |
| `src/interpreter/bbcode.jl` | 15 | ssair/ir.jl, ssair/basicblock.jl |
| `src/utils.jl` | 9 | opaque_closure.jl, optimize.jl |
| `src/interpreter/ir_normalisation.jl` | 11 | ssair/ir.jl, typelattice.jl |
| `src/interpreter/forward_mode.jl` | 8 | ssair/ir.jl, typelattice.jl |
| `src/interpreter/reverse_mode.jl` | 6 | typelattice.jl, typeinfer.jl |

---

## Julia Files by Usage

| Julia Source | References | Capability |
|--------------|------------|------------|
| `Compiler/src/types.jl` | 31 | AbstractInterpreter |
| `Compiler/src/ssair/ir.jl` | 30 | IRCode/CFG |
| `Compiler/src/optimize.jl` | 22 | Optimization |
| `Compiler/src/inferencestate.jl` | 14 | AbstractInterpreter |
| `Compiler/src/typelattice.jl` | 8 | AbstractInterpreter |
| `Compiler/src/stmtinfo.jl` | 8 | AbstractInterpreter |
| `Compiler/src/typeinfer.jl` | 8 | AbstractInterpreter |
| `Compiler/src/ssair/irinterp.jl` | 8 | AbstractInterpreter |
| `Compiler/src/abstractinterpretation.jl` | 6 | AbstractInterpreter |
| `Compiler/src/cicache.jl` | 5 | AbstractInterpreter |
| `base/opaque_closure.jl` | 3 | OpaqueClosure |
| `Compiler/src/opaque_closure.jl` | 2 | OpaqueClosure |

---

## Version Guards in Mooncake

Mooncake uses `@static if VERSION` guards to handle API changes:

| File | Guards | APIs Guarded |
|------|--------|--------------|
| `abstract_interpretation.jl` | 8 | inlining_policy, add_edges_impl |
| `ir_utils.jl` | 7 | InstructionStream fields, DebugInfoStream |
| `bbcode.jl` | 6 | IRCode constructor, valid_worlds |
| `reverse_mode.jl` | 5 | BBCode, valid_worlds |
| `patch_for_319.jl` | 5 | IR interpretation internals |
