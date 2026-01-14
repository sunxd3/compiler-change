---
name: analyze-julia-compiler-pr
description: Analyze a Julia compiler PR for downstream impact, secondary effects, and changelog generation. Use when asked to analyze a PR number or when working with compiler_prs.json data.
metadata:
  short-description: Deep analysis of Julia compiler PRs
---

# Julia Compiler PR Analysis Skill

Analyze Julia compiler PRs to generate structured changelog entries for downstream package maintainers (Turing.jl, Enzyme.jl, GPUCompiler, JET, etc.).

## Data Location

- PR cache: `pr-archive/JuliaLang_julia/`
- Compiler PRs list: `pr-archive/JuliaLang_julia/compiler_prs.json`
- Analysis output: `analyses/pr_{number}.yaml` (per-PR file)
- Schema: `references/analysis-schema.json`

## Setup: Clone Julia Repository

**IMPORTANT:** Before analyzing PRs, clone the Julia repository to examine full code context (not just diffs):

```bash
# Clone Julia repo if not present
if [ ! -d "julia" ]; then
  git clone --depth 100 https://github.com/JuliaLang/julia.git julia
fi

# Checkout the merge commit for a specific PR
cd julia
git fetch origin pull/{PR_NUMBER}/merge:pr-{PR_NUMBER}
git checkout pr-{PR_NUMBER}
```

This enables:
- Reading full file context around changed lines
- Tracing function call sites and callers
- Understanding data structures being modified
- Finding secondary effects not visible in the diff alone

## Compiler Pipeline (how changes propagate)

```
JuliaSyntax parser/tokenizer
  -> AST shape & token kinds
  -> Macro expansion + hygiene
  -> JuliaLowering desugaring + scope analysis
  -> Linear IR / closure conversion
  -> CodeInfo / SSA IR
  -> Abstract interpretation + type inference
  -> Effects & escape analysis
  -> Inlining & optimization passes
  -> Codegen / runtime behavior
  -> Interpreter fallback + debugging tools
```

Changes early in the pipeline (JuliaSyntax/JuliaLowering) tend to amplify downstream.

## Analysis Framework

For each PR, investigate and document:

### A. PR Metadata & Intent
- Title, labels, linked issues, merge date
- Stated intent vs observed changes

### B. Pipeline Localization
Map touched files to stages:
- `JuliaSyntax/` -> Parsing, tokenization
- `JuliaLowering/` -> Lowering, scope analysis, closure conversion
- `Compiler/src/abstractinterpretation.jl` -> Type inference
- `Compiler/src/ssair/` -> SSA IR, inlining, optimization passes
- `Compiler/src/tfuncs.jl` -> Type functions
- `src/interpreter.c` -> Interpreter

### C. Change Taxonomy
- Semantic vs performance vs diagnostics vs refactor-only
- Compile-time vs runtime behavior
- Internal API changes vs implementation-only

### D. Direct Behavior Deltas
- New/changed AST or IR forms
- New invariants or removed passes
- Altered heuristics

### E. Secondary Propagation Analysis (CRITICAL)
Trace how changes ripple through:
- Inference <-> Inlining feedback loops
- Macro expansion <-> Lowering interactions
- Effects inference -> Optimization decisions
- Type lattice changes -> Specialization behavior

### F. Downstream Package Impact
Check for effects on:
- **OpaqueClosure** - creation, inference, optimization
- **Generated functions** - `@generated` execution
- **World age / invalidation** - method tables, caches
- **Internal API consumers** - IRTools, Cassette, JET, GPUCompiler, Enzyme
- **Effect flags** - `:consistent`, `:effect_free`, `:nothrow`, etc.

### G. Evidence & Confidence
- Test changes and assertions
- Risk level: low/medium/high

## Output Schema (YAML)

```yaml
schema_version: "1.0"
pr:
  number: int
  title: string
  url: uri
  author: string
  labels: [string]
  merged_at: datetime
scope:
  files_touched: [string]
  components: [JuliaSyntax|JuliaLowering|Compiler.*|Interpreter]
  pipeline_stages: [Parsing|Lowering|TypeInference|Inlining|...]
analysis:
  intent:
    summary: string
    issue_links: [string]
  direct_changes:
    - summary: string
      component: string
      evidence: [{source, path, loc, snippet}]
  secondary_effects:
    - effect: string
      mechanism: string
      downstream_surfaces: [string]
      likelihood: low|medium|high
      impact: low|medium|high
  compatibility:
    internal_api: [impact_item]
    behavioral: [impact_item]
  performance:
    compile_time: [impact_item]
    runtime: [impact_item]
  risk:
    level: low|medium|high
    rationale: [string]
  open_questions: [string]
  recommendations: [string]
```

## How to Use

1. **Analyze a specific PR:**
   ```
   Analyze PR 59413 from the compiler PRs
   ```

2. **Batch analysis:**
   ```
   Analyze all JuliaLowering PRs and summarize closure-related changes
   ```

3. **Impact search:**
   ```
   Which PRs might affect OpaqueClosure behavior?
   ```

## Analysis Workflow

For each PR analysis, follow these steps:

### Step 1: Setup Julia repo and checkout PR
```bash
# Clone if needed (shallow clone for speed)
[ ! -d "julia" ] && git clone --depth 100 https://github.com/JuliaLang/julia.git julia

# Fetch and checkout the specific PR
cd julia
git fetch origin pull/60567/merge:pr-60567
git checkout pr-60567
```

### Step 2: Read cached PR metadata
```bash
cat pr-archive/JuliaLang_julia/pr_60567.json
```

### Step 3: Examine FULL code context (not just diff)
This is critical for finding secondary effects:
```bash
# Read complete modified files
cat julia/JuliaLowering/src/closure_conversion.jl

# Find all callers of a modified function
rg "analyze_lambda_vars" julia/

# Trace struct usage across codebase
rg "MethodMatchTarget" julia/Compiler/

# Check test files for expected behavior
cat julia/JuliaLowering/test/closures.jl
```

### Step 4: Write analysis to per-PR output file
```bash
# Output path: analyses/pr_{number}.yaml
# Per-PR files allow parallel analysis without merge conflicts
mkdir -p analyses
# Write YAML analysis to analyses/pr_60567.yaml
```

## Key Questions Per PR

1. **Intent:** What does the PR claim to fix/improve?
2. **Stage:** Which compiler stage(s) are touched?
3. **Semantic change:** Could user code behave differently?
4. **Inference:** Does it change lattice operations, tfuncs, or heuristics?
5. **Optimization:** Does it change inlining thresholds, escape analysis, effect inference?
6. **OpaqueClosure / generated functions:** Any changes to closure representation or `@generated`?
7. **World age / invalidation:** Are method tables or caches affected?
8. **Compiler API surface:** Any struct/field changes that break Core.Compiler users?
9. **Non-obvious downstream:** Performance characteristics or allocation behavior changes?
10. **Tests:** What behavior do added tests lock in?
