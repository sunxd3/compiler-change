---
name: analyze-julia-compiler-pr
description: Analyze a Julia compiler PR and generate a human-readable changelog entry. Use when asked to analyze a PR number.
metadata:
  short-description: Changelog entry for Julia compiler PRs
---

# Julia Compiler PR Analysis Skill

Generate **human-readable changelog entries** for Julia compiler PRs. The goal is a quick summary that helps downstream maintainers understand what changed and why it matters - not a comprehensive audit document.

## Philosophy

- **Readable first** - Write for humans skimming a changelog, not auditors
- **Actionable** - Focus on "what does this mean for me?"
- **Concise** - If they want full details, they read the PR
- **Scannable** - Headers, bullets, short paragraphs

## Output Location

- Output: `analyses/pr_{number}.yaml`
- PR cache: `pr-archive/JuliaLang_julia/`

## Setup

Clone Julia repo to understand context:
```bash
[ ! -d "julia" ] && git clone --depth 100 https://github.com/JuliaLang/julia.git julia
cd julia && git fetch origin pull/{PR}/merge:pr-{PR} && git checkout pr-{PR}
```

## Output Format

Write a YAML file with this structure:

```yaml
pr:
  number: 60567
  title: "[JuliaLowering] Implement flisp-compatible Box optimization"
  url: "https://github.com/JuliaLang/julia/pull/60567"
  author: "aviatesk"
  merged_at: "2026-01-10"

# One paragraph explaining what this PR does and why
summary: |
  Adds a new binding analysis pass to avoid Core.Box allocations for captured
  variables that are single-assigned before any closure captures them. This
  makes closure-heavy code faster by reducing heap allocations.

# What compiler areas are affected
areas:
  - JuliaLowering (closure conversion, scope analysis)

# Who should care about this change
affects:
  - Packages using closures heavily (less boxing overhead)
  - Tools inspecting IR for boxed captures (JET, IRTools)
  - OpaqueClosure users (captured fields may change layout)

# Specific changes that might break or affect downstream code
breaking_or_notable:
  - "BindingInfo.is_always_defined semantics changed for captured locals"
  - "Closure IR shape differs: some captures now unboxed"

# Concrete example of the behavior change (optional but helpful)
example: |
  # Before: y was boxed
  function f(cond)
      if cond; println("hi"); end
      y = 1
      () -> y  # Core.Box allocated
  end

  # After: y is not boxed (single-assign dominates capture)
  function f(cond)
      if cond; println("hi"); end
      y = 1
      () -> y  # Direct capture, no Box
  end

# Risk assessment
risk: medium  # low / medium / high

# What downstream maintainers should do
action_items:
  - "If you pattern-match Core.Box in IR, also handle unboxed captures"
  - "Run your closure-heavy benchmarks to verify improvements"
```

## Guidelines

### Summary (1-3 sentences)
- What does this PR do?
- Why was it done?
- What's the practical impact?

### Affects (who should care)
- Which types of packages/tools are impacted?
- Be specific: "packages using closures heavily" not "all packages"

### Breaking or Notable
- What might break or behave differently?
- Name specific fields/APIs that changed semantics
- Keep it brief - just flag the issues

### Example (optional)
- Show a before/after code snippet if it helps understanding
- Keep it minimal - 5-10 lines max

### Action Items
- What should downstream maintainers actually do?
- Be concrete: "check X", "update Y", "run Z"

## What NOT to Do

- Don't include full function bodies (link to PR instead)
- Don't list every file touched (just the areas)
- Don't write audit-style evidence blocks
- Don't be exhaustive - be useful

## Quality Check

Before writing, ask:
- Can someone understand this in 30 seconds?
- Is it clear what they should do?
- Would I find this useful as a changelog entry?
