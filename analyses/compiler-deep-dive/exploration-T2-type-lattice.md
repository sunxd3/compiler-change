# Julia Compiler Type Lattice Subsystem - Deep Exploration

**Status**: FOUNDATIONAL - Other compiler subsystems depend on this

**Permalink Base**: https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/

## Overview

The Type Lattice is the mathematical foundation for Julia's type inference system. It defines a partial order over "lattice elements" that extend Julia's native type system with additional compile-time information. This enables the compiler to track more precise information about values than can be expressed with types alone.

The lattice is structured as a **tower of lattice layers**, each adding new lattice elements on top of the previous layer:

```
InferenceLattice (adds LimitedAccuracy)
        |
MustAliasesLattice / ConditionalsLattice (adds MustAlias / Conditional)
        |
PartialsLattice (adds PartialStruct, PartialOpaque)
        |
ConstsLattice (adds Const, PartialTypeVar)
        |
JLTypeLattice (native Julia types)
```

---

## 1. Lattice Types (Extended Lattice Elements)

### 1.1 Core Types (Defined in `Core` - boot.jl)

These types are defined in Core so they can be stored in the global code cache.

#### `Const` (boot.jl:520-523)
```julia
struct Const
    val
    Const(@nospecialize(v)) = new(v)
end
```
Represents a compile-time constant value. The actual value is stored in `val`.

**Permalink**: [boot.jl#L520-L523](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/base/boot.jl#L520-L523)

#### `PartialStruct` (boot.jl:525-533)
```julia
struct PartialStruct
    typ        # The object's type
    undefs::Array{Union{Nothing,Bool}, 1}  # Field definedness
    fields::Array{Any, 1}  # Lattice elements for each field
end
```
Tracks field-level information beyond the object type. Used when some fields are known to be constants or have more precise types than the declared field type.

**Field Definedness (`undefs`)**:
- `nothing` - field may be undefined
- `false` - field is definitely defined
- `true` - field is definitely undefined (only valid when field type is `Union{}`)

**Permalink**: [boot.jl#L525-L533](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/base/boot.jl#L525-L533)

#### `InterConditional` (boot.jl:535-540)
```julia
struct InterConditional
    slot::Int
    thentype
    elsetype
end
```
Inter-procedural version of `Conditional`. Conveys constraints on call arguments that can refine types in calling contexts.

**Permalink**: [boot.jl#L535-L540](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/base/boot.jl#L535-L540)

#### `PartialOpaque` (boot.jl:542-548)
```julia
struct PartialOpaque
    typ::Type
    env           # Captured environment
    parent::MethodInstance
    source
end
```
Represents an opaque closure with partial information about its captured environment.

**Permalink**: [boot.jl#L542-L548](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/base/boot.jl#L542-L548)

---

### 1.2 Local Inference Types (typelattice.jl)

#### `Conditional` (typelattice.jl:44-61)
```julia
struct Conditional
    slot::Int      # Which slot this condition relates to
    ssadef::Int    # SSA definition point for validity tracking
    thentype       # Type refinement in true branch
    elsetype       # Type refinement in false branch
    isdefined::Bool # Whether from @isdefined check
end
```
Enables **branch refinement**: when a boolean value is the result of a type test (like `isa`), this tracks which slot it tests and what types to assume in each branch.

**Example**:
```julia
x::Union{Int, Float64}
if isa(x, Int)  # Returns Conditional(x, _, Int, Float64)
    # x refined to Int
else
    # x refined to Float64
end
```

**Permalink**: [typelattice.jl#L44-L61](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelattice.jl#L44-L61)

#### `MustAlias` (typelattice.jl:94-111)
```julia
struct MustAlias
    slot::Int      # Slot containing the parent object
    ssadef::Int    # SSA definition for validity
    vartyp::Any    # Type of the parent object
    fldidx::Int    # Field index being tracked
    fldtyp::Any    # Type of the tracked field
end
```
Tracks **field aliasing** for refined field type tracking. When accessing a field of an object, this allows type refinements on that field to propagate to other accesses of the same field.

**Key Invariant**: Assumes the field never changes (must be a const field or the object is not mutated).

**Example**:
```julia
x::Some{Union{Nothing,String}}
alias = x.value  # MustAlias(x, Some{...}, 1, Union{Nothing,String})
if alias === nothing
    # x.value refined to Nothing
else
    # x.value refined to String
end
```

**Permalink**: [typelattice.jl#L94-L111](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelattice.jl#L94-L111)

#### `InterMustAlias` (typelattice.jl:118-134)
```julia
struct InterMustAlias
    slot::Int
    vartyp::Any
    fldidx::Int
    fldtyp::Any
end
```
Inter-procedural version of `MustAlias` (without `ssadef` since it's for cross-function use).

**Permalink**: [typelattice.jl#L118-L134](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelattice.jl#L118-L134)

#### `PartialTypeVar` (typelattice.jl:142-149)
```julia
struct PartialTypeVar
    tv::TypeVar
    lb_certain::Bool  # Is lower bound known exactly?
    ub_certain::Bool  # Is upper bound known exactly?
end
```
Represents a TypeVar with partial certainty about its bounds.

**Permalink**: [typelattice.jl#L142-L149](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelattice.jl#L142-L149)

#### `LimitedAccuracy` (typelattice.jl:208-216)
```julia
struct LimitedAccuracy
    typ           # The wrapped lattice element
    causes::IdSet{InferenceState}  # What caused the limitation
end
```
Indicates that inference was **approximated due to recursion limiting**. The wrapped type is an upper bound, but may not be precise. Tracking `causes` allows different call stacks to potentially get more precise results.

**Key Insight**: `LimitedAccuracy(T)` is considered epsilon-smaller than `T` in the lattice, ensuring that unlimited results are preferred when available.

**Permalink**: [typelattice.jl#L208-L216](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelattice.jl#L208-L216)

#### `NotFound` (typelattice.jl:227-229)
```julia
struct NotFound end
const NOT_FOUND = NotFound()
```
Sentinel value indicating a variable has not been analyzed yet. Used for SSA value initialization.

**Permalink**: [typelattice.jl#L227-L229](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelattice.jl#L227-L229)

---

### 1.3 State Tracking Types (typelattice.jl)

#### `StateUpdate` (typelattice.jl:151-154)
```julia
struct StateUpdate
    var::SlotNumber
    vtype::VarState
end
```
Represents an update to a slot's type state.

#### `StateRefinement` (typelattice.jl:160-168)
```julia
struct StateRefinement
    slot::Int
    newtyp
    undef::Bool
end
```
A refinement that preserves object identity (the slot still refers to the same object, but we know more about it).

---

## 2. Lattice Layers (abstractlattice.jl)

The lattice is organized as composable layers, each adding new lattice elements.

### 2.1 Layer Types

| Layer | Line | Adds | Purpose |
|-------|------|------|---------|
| `JLTypeLattice` | L11 | Native types | Base layer - Julia's type system |
| `ConstsLattice` | L20 | `Const`, `PartialTypeVar` | Compile-time constants |
| `PartialsLattice{L}` | L29-31 | `PartialStruct`, `PartialOpaque` | Field-level precision |
| `ConditionalsLattice{L}` | L40-42 | `Conditional` | Local branch refinement |
| `InterConditionalsLattice{L}` | L51-53 | `InterConditional` | Inter-procedural conditions |
| `MustAliasesLattice{L}` | L62-64 | `MustAlias` | Local field aliasing |
| `InterMustAliasesLattice{L}` | L73-75 | `InterMustAlias` | Inter-procedural aliasing |
| `InferenceLattice{L}` | L92-94 | `LimitedAccuracy` | Recursion-limited results |

### 2.2 Standard Lattice Compositions

```julia
# Simple inference without conditionals
const SimpleInferenceLattice = PartialsLattice(ConstsLattice())

# Local inference with conditionals
const BaseInferenceLattice = ConditionalsLattice(SimpleInferenceLattice.instance)

# Inter-procedural result lattice
const IPOResultLattice = InterConditionalsLattice(SimpleInferenceLattice.instance)

# Full inference lattice (with LimitedAccuracy)
const fallback_lattice = InferenceLattice(BaseInferenceLattice.instance)
```

**Permalink**: [abstractlattice.jl#L82-L84](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/abstractlattice.jl#L82-L84)

---

## 3. Lattice Operations

### 3.1 Partial Order: `⊑` (subtype/less-than)

**Definition** (abstractlattice.jl:144-154):
```julia
function ⊑ end
⊑(::JLTypeLattice, a::Type, b::Type) = a <: b
```

Each lattice layer extends `⊑` for its elements:

| Layer | Implementation | Location |
|-------|---------------|----------|
| `JLTypeLattice` | `a <: b` | abstractlattice.jl:153 |
| `ConstsLattice` | `Const` comparison by value identity | typelattice.jl:532-552 |
| `PartialsLattice` | Field-wise comparison | typelattice.jl:454-530 |
| `ConditionalsLattice` | `issubconditional` | typelattice.jl:414-439 |
| `MustAliasesLattice` | `issubalias` | typelattice.jl:441-452 |
| `InferenceLattice` | Handle `LimitedAccuracy` wrapping | typelattice.jl:395-412 |

**Key Rule for `LimitedAccuracy`**: `LimitedAccuracy(T)` is epsilon-smaller than `T`, but all elements strictly below `T` are also below `LimitedAccuracy(T)`.

### 3.2 Strict Order: `⊏` and `⋤`

```julia
# Strict partial order (irreflexive kernel of ⊑)
⊏(𝕃, a, b) = ⊑(𝕃, a, b) && !⊑(𝕃, b, a)

# Assuming a ⊑ b, check if strictly less
⋤(𝕃, a, b) = !⊑(𝕃, b, a)
```

**Permalink**: [abstractlattice.jl#L156-L169](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/abstractlattice.jl#L156-L169)

### 3.3 Join: `tmerge` (lattice union/join)

**Definition** (abstractlattice.jl:117-125):
```julia
function tmerge end
```

Computes a **lattice join** of two elements. Note: The result is not necessarily the least upper bound - complexity limits are applied.

**Layer Implementations**:

| Layer | Location | Key Logic |
|-------|----------|-----------|
| `JLTypeLattice` | typelimits.jl:736-750 | Type union with complexity limits |
| `ConstsLattice` | typelimits.jl:724-734 | Widen if different constants |
| `PartialsLattice` | typelimits.jl:678-722 | `tmerge_partial_struct` for field merge |
| `ConditionalsLattice` | typelimits.jl:499-537 | Merge if same slot, else widen |
| `MustAliasesLattice` | typelimits.jl:579-589 | Widen to field type |
| `InferenceLattice` | typelimits.jl:491-497 | `tmerge_limited` for cause tracking |

### 3.4 Meet: `tmeet` (lattice intersection)

**Definition** (abstractlattice.jl:99-114):
```julia
function tmeet end
tmeet(::JLTypeLattice, a::Type, b::Type) =
    (ti = typeintersect(a, b); valid_as_lattice(ti, true) ? ti : Bottom)
```

Computes lattice meet, dropping results with no concrete subtypes.

**Layer Implementations** (typelattice.jl:624-706):
- `PartialsLattice`: Intersect field types element-wise
- `ConstsLattice`: Check if constant value matches type
- `ConditionalsLattice`: Require `Bool <: t`
- `MustAliasesLattice`: Widen to field type first

### 3.5 Widening Operations

#### `widenconst` (typelattice.jl:708-722)
```julia
widenconst(x) -> Type
```
Converts extended lattice elements to native Julia types:
- `Const(v)` -> `typeof(v)` or `Type{v}`
- `PartialStruct` -> its `typ` field
- `Conditional` -> `Bool`
- `MustAlias` -> widenconst of field type

#### `widenlattice` (abstractlattice.jl:312-316)
```julia
widenlattice(𝕃::AbstractLattice) -> parent lattice
widenlattice(𝕃, t) -> widen t to parent lattice element
```
Moves up one level in the lattice tower.

---

## 4. Widening Rules (typelimits.jl)

Julia prevents infinite type growth through **widening heuristics**.

### 4.1 Complexity Parameters

```julia
const MAX_TYPEUNION_COMPLEXITY = 3
const MAX_TYPEUNION_LENGTH = 3
```
**Permalink**: [typelimits.jl#L7-L8](https://github.com/JuliaLang/julia/blob/4d04bb6b3b1b879f4dbb918d194c5c939a1e7f3c/Compiler/src/typelimits.jl#L7-L8)

### 4.2 Core Widening Function: `limit_type_size`

**Location**: typelimits.jl:17-33

```julia
function limit_type_size(t, compare, source, allowed_tupledepth, allowed_tuplelen)
```

**Purpose**: Limit type `t` to be no more complex than `compare`, drawing parameter values only from `source`.

**Algorithm**:
1. Check if `t` is more complex than `compare` via `type_more_complex`
2. If so, apply `_limit_type_size` to simplify
3. Ensure `t <: result` (widen more aggressively if needed)

### 4.3 Complexity Detection: `type_more_complex`

**Location**: typelimits.jl:223-307

Determines if type `t` is more complex than comparison `c` by checking:
- Union nesting depth
- Tuple nesting depth
- Whether type parameters are derived from known sources
- TypeVar complexity

### 4.4 Type Derivation Check: `is_derived_type`

**Location**: typelimits.jl:37-75

Checks if type `t` appears somewhere in `c` at minimum nesting depth. Types not derived from known sources are considered "new" and may trigger widening.

### 4.5 Simplicity Checks

```julia
function issimpleenoughtype(t)
    max(unionlen(t), union_count_abstract(t) + 1) <= MAX_TYPEUNION_LENGTH &&
    unioncomplexity(t) <= MAX_TYPEUNION_COMPLEXITY
end
```
**Location**: typelimits.jl:312-317

### 4.6 Tuple Merging: `tuplemerge`

**Location**: typelimits.jl:896-975

Special handling for tuple type widening:
- Merge element-wise for same-length tuples
- Collapse to `Vararg` for different lengths
- Simplify complex elements to `Any`

### 4.7 LimitedAccuracy Merging

**Location**: typelimits.jl:440-489

When merging `LimitedAccuracy` elements:
- Track which inference states caused the limitation
- Allow discarding causes when one type strictly contains the other
- Union causes when both types contribute to the result

---

## 5. Key Functions Reference

### typelattice.jl

| Function | Lines | Purpose |
|----------|-------|---------|
| `Conditional` constructor | 53-61 | Creates conditional with validity checks |
| `MustAlias` constructor | 100-108 | Creates must-alias with invariant checks |
| `widenconditional` | 258-271 | Widen Conditional to Bool or Const |
| `widenmustalias` | 314-321 | Widen MustAlias to field type |
| `issubconditional` | 281-296 | Check if one Conditional is subtype of another |
| `issubalias` | 381-384 | Check if one MustAlias is subtype of another |
| `form_mustalias_conditional` | 346-379 | Create Conditional from MustAlias comparison |
| `maybe_extract_const_bool` | 303-309 | Extract constant bool from Conditional |
| `smerge` | 728-733 | Merge variable states at join points |
| `stupdate!` | 738-754 | Update variable table with path convergence |

### typelimits.jl

| Function | Lines | Purpose |
|----------|-------|---------|
| `limit_type_size` | 17-33 | Main type complexity limiter |
| `type_more_complex` | 223-307 | Complexity comparison |
| `is_derived_type` | 37-75 | Check type derivation |
| `_limit_type_size` | 86-189 | Internal type limiter |
| `tmerge_fast_path` | 403-415 | Fast path for lattice join |
| `tmerge_limited` | 440-489 | Join with LimitedAccuracy |
| `tmerge_partial_struct` | 593-676 | Join PartialStruct elements |
| `tmerge_types_slow` | 779-893 | Complex type union merging |
| `tuplemerge` | 896-975 | Specialized tuple joining |
| `issimpleenoughtype` | 312-317 | Check type simplicity |
| `issimplertype` | 336-401 | Check if type is simpler |
| `n_initialized` | 324-332 | Count initialized fields |

### abstractlattice.jl

| Function | Lines | Purpose |
|----------|-------|---------|
| `widenlattice` | 3, 12, 21, etc. | Get parent lattice |
| `is_valid_lattice_norec` | 4, 13, 22, etc. | Check element validity |
| `tmeet` | 99-114 | Lattice meet operation |
| `tmerge` | 117-125 | Lattice join operation |
| `⊑` | 144-154 | Partial order |
| `⊏` | 156-161 | Strict partial order |
| `⋤` | 163-169 | Strict order assuming subtype |
| `is_lattice_equal` | 172-181 | Equality check |
| `has_nontrivial_extended_info` | 184-204 | Check for extra lattice info |
| `is_const_prop_profitable_arg` | 207-238 | Check if const prop useful |
| `has_conditional` | 276-278 | Check for conditional support |
| `has_mustalias` | 280-282 | Check for mustalias support |

### typeutils.jl

| Function | Lines | Purpose |
|----------|-------|---------|
| `isconstType` | 9 | Check if Type{T} is constant |
| `hasuniquerep` | 12-24 | Check type has unique representation |
| `isTypeDataType` | 34-41 | Check if guaranteed DataType |
| `valid_as_lattice` | 70-90 | Validate lattice element |
| `argtypes_to_type` | 51-56 | Convert argtypes to Tuple type |
| `typesubtract` | 126-171 | Subtract type from union |
| `unionsplitcost` | 201-218 | Cost of union splitting |
| `switchtupleunion` | 223-258 | Convert tuple-of-unions to union-of-tuples |
| `unioncomplexity` | 262-280 | Compute union complexity |
| `is_identity_free_argtype` | 315-316 | Check identity-free type |
| `is_immutable_argtype` | 327-334 | Check immutability |
| `is_mutation_free_argtype` | 346-348 | Check mutation freedom |

---

## 6. Cross-References to Core Types

The type lattice imports and uses several types defined in `Core`:

### Imported from Core (typelattice.jl:9)
```julia
import Core: Const, InterConditional, PartialStruct
```

### Core Type Definitions
- `Core.Const` - boot.jl:520-523
- `Core.PartialStruct` - boot.jl:525-533, coreir.jl:50-66
- `Core.InterConditional` - boot.jl:535-540, coreir.jl:102-116
- `Core.PartialOpaque` - boot.jl:542-548

### Related Core Types Used
- `Core.SlotNumber` - For slot references in Conditional/MustAlias
- `Core.TypeVar` - Wrapped by PartialTypeVar
- `Core.InferenceState` - Referenced by LimitedAccuracy causes

### Helper Functions from Core (via coreir.jl)
- `partialstruct_init_undefs` - coreir.jl:75-93
- `fieldcount_noerror` - Used for PartialStruct validation
- `datatype_min_ninitialized` - Minimum required initialized fields

---

## 7. Design Patterns and Invariants

### 7.1 Slot Wrapper Invariant
No nesting of slot wrappers is allowed:
```julia
assert_nested_slotwrapper(t)  # typelattice.jl:238-244
```
Conditional/MustAlias elements cannot contain other Conditional/MustAlias elements.

### 7.2 Local vs Inter-procedural Separation
- `Conditional` and `MustAlias` - local inference only
- `InterConditional` and `InterMustAlias` - cross-function boundaries
- These are **never** compared or merged with each other

### 7.3 SSA Definition Tracking
`Conditional` and `MustAlias` include `ssadef` to track when they become invalid:
```julia
conditional_valid(cnd::Conditional, state::VarTable) =
    state[cnd.slot].ssadef == cnd.ssadef
```
When a slot is reassigned, its ssadef changes, invalidating old conditionals.

### 7.4 Widening Guarantees
All widening operations must preserve:
- `original ⊑ widened` (original is below or equal to widened)
- `original <: widenconst(widened)` (subtype relationship preserved)

### 7.5 Join Non-Associativity
The `tmerge` operation is **intentionally not associative** due to complexity limits. This means `tmerge(a, tmerge(b, c))` may differ from `tmerge(tmerge(a, b), c)`.

---

## 8. Usage Context

### 8.1 Abstract Interpretation
The lattice provides the semantic domain for abstract interpretation in `abstractinterpretation.jl`. Each statement transforms the abstract state (a mapping from slots/SSA values to lattice elements).

### 8.2 Type Inference
`typeinfer.jl` uses the lattice to:
- Initialize slots/SSAs to `NOT_FOUND`
- Merge types at control flow join points via `smerge`/`tmerge`
- Widen types when detecting cycles via `LimitedAccuracy`

### 8.3 Return Type Computation
Return types are widened from local inference types to inter-procedural types:
- `Conditional` -> `InterConditional`
- `MustAlias` -> `InterMustAlias`

### 8.4 Constant Propagation
`is_const_prop_profitable_arg` determines which lattice elements justify re-analyzing a function with more precise argument information.

---

## 9. Summary

The Type Lattice is a carefully designed system that:

1. **Extends** Julia's type system with compile-time information (constants, field types, branch conditions)

2. **Layers** multiple refinements in a composable tower structure

3. **Controls complexity** through widening heuristics that prevent infinite type growth

4. **Separates concerns** between local inference (Conditional/MustAlias) and inter-procedural analysis (InterConditional/InterMustAlias)

5. **Tracks precision** through LimitedAccuracy to avoid poisoning unrelated call stacks with approximate results

This forms the mathematical foundation that enables Julia's advanced type inference capabilities while ensuring termination and reasonable compile times.

---

**Files Analyzed**:
- `Compiler/src/typelattice.jl` (798 lines)
- `Compiler/src/typelimits.jl` (976 lines)
- `Compiler/src/abstractlattice.jl` (317 lines)
- `Compiler/src/typeutils.jl` (349 lines)
- `base/boot.jl` (Core type definitions)
- `base/coreir.jl` (PartialStruct helpers)
