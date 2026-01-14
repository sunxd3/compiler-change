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
- Analysis output: `analyses/`
- Schema: `analysis-schema.json`

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

## Fetching PR Diffs

To get full diff content:
```bash
# Using gh CLI
gh pr view 59413 --repo JuliaLang/julia --json files,body,title

# Or fetch diff directly
curl -L https://github.com/JuliaLang/julia/pull/59413.diff
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
