# Julia Compiler PR Index by Version

This index tracks compiler-related PRs organized by the Julia version they target.

## Version Timeline

```
Julia 1.12 (release-1.12 branch)
     |
     | (development)
     v
Julia 1.13 (release-1.13 branch)     <-- Branch point: 2025-10-27
     |
     | (development continues on master)
     v
Julia 1.14 (future, not yet branched)
```

**Branch point for 1.13**: `abd8457ca85370eefe3788cfa13a6233773ea16f` (2025-10-27)

---

## Julia 1.13 PRs (67)

PRs merged before the 1.13 branch point. See `analyses/v1.13/` for detailed analyses.

Key changes:

| PR | Title | Merged |
|----|-------|--------|
| [#56201](https://github.com/JuliaLang/julia/pull/56201) | Use stmt instead of `Instruction` in `populate_def_use_map!` | 2025-10-14 |
| [#59165](https://github.com/JuliaLang/julia/pull/59165) | ccall: make distinction of pointer vs name a syntactic distinction | 2025-10-09 |
| [#59766](https://github.com/JuliaLang/julia/pull/59766) | Align interpreter and codegen error behavior of setglobal! and friends | 2025-10-08 |
| [#59772](https://github.com/JuliaLang/julia/pull/59772) | Avoid method instance normalization for opaque closure methods | 2025-10-07 |
| [#59784](https://github.com/JuliaLang/julia/pull/59784) | Make `=` and `const` toplevel-preserving syntax | 2025-10-17 |
| [#59785](https://github.com/JuliaLang/julia/pull/59785) | Fix missing GC root | 2025-10-08 |
| [#59888](https://github.com/JuliaLang/julia/pull/59888) | Type-assert `isfinite(::AbstractFloat)` | 2025-10-20 |
| [#59908](https://github.com/JuliaLang/julia/pull/59908) | absint: allow ad-hoc cancellation of concrete evaluation | 2025-10-20 |
| [#59921](https://github.com/JuliaLang/julia/pull/59921) | Set types of boxed variables in `abstract_eval_nonlinearized_foreigncall_name` | 2025-10-24 |

---

## Julia 1.14 PRs (174)

PRs merged after the 1.13 branch point (on master, targeting 1.14). See `analyses/v1.14/` for detailed analyses.

Key changes:

| PR | Title | Merged |
|----|-------|--------|
| [#55601](https://github.com/JuliaLang/julia/pull/55601) | inference: track reaching defs for slots | 2025-12-30 |
| [#59413](https://github.com/JuliaLang/julia/pull/59413) | inference: reinfer and track missing code for inlining | 2025-11-10 |
| [#59870](https://github.com/JuliaLang/julia/pull/59870) | Move JuliaSyntax + JuliaLowering into the main tree | 2025-11-14 |
| [#59974](https://github.com/JuliaLang/julia/pull/59974) | inference: revisit all methods in cycle | 2025-11-01 |
| [#60011](https://github.com/JuliaLang/julia/pull/60011) | fix `pointerarith_tfunc` for Const ptr | 2025-11-01 |
| [#60018](https://github.com/JuliaLang/julia/pull/60018) | Provide mechanism for Julia syntax evolution | 2025-11-25 |
| [#60079](https://github.com/JuliaLang/julia/pull/60079) | disable compiling for typeinf world during incremental compile | 2025-11-09 |
| [#60093](https://github.com/JuliaLang/julia/pull/60093) | aotcompile: implement build healing | 2025-11-13 |
| [#60105](https://github.com/JuliaLang/julia/pull/60105) | Add JLJITLinkMemoryManager (ports memory manager to JITLink) | 2025-11-13 |
| [#60140](https://github.com/JuliaLang/julia/pull/60140) | [JuliaLowering] Fix placeholders in parameters and decls | 2025-11-18 |
| [#60214](https://github.com/JuliaLang/julia/pull/60214) | inference: fix the ptrfree field check | 2025-11-24 |
| [#60257](https://github.com/JuliaLang/julia/pull/60257) | [JuliaLowering] `ccall((lib,sym)...)` and `cfunction` fixes | 2025-12-01 |
| [#60311](https://github.com/JuliaLang/julia/pull/60311) | threads: Implement asymmetric atomic fences | 2025-12-15 |
| [#60316](https://github.com/JuliaLang/julia/pull/60316) | [JuliaLowering] Refactor scope resolution pass | 2025-12-11 |
| [#60353](https://github.com/JuliaLang/julia/pull/60353) | codegen load/store/union cleanup and fix | 2025-12-11 |
| [#60388](https://github.com/JuliaLang/julia/pull/60388) | codegen: improve size layout for on-stack pointer-ful types | 2025-12-17 |
| [#60410](https://github.com/JuliaLang/julia/pull/60410) | [JuliaLowering] Add support for `Expr(:loopinfo, ...)` | 2025-12-18 |
| [#60416](https://github.com/JuliaLang/julia/pull/60416) | lowering: Fix `@nospecialize` on unnamed arguments | 2026-01-07 |
| [#60517](https://github.com/JuliaLang/julia/pull/60517) | Remove `jl_gc_external_obj_hdr_size` | 2026-01-03 |
| [#60551](https://github.com/JuliaLang/julia/pull/60551) | [JuliaLowering] Add remap for assigned-to arguments | 2026-01-07 |
| [#60567](https://github.com/JuliaLang/julia/pull/60567) | [JuliaLowering] Implement flisp-compatible Box optimization | 2026-01-10 |
| [#60576](https://github.com/JuliaLang/julia/pull/60576) | Enable JITLink everywhere | 2026-01-12 |
| [#60577](https://github.com/JuliaLang/julia/pull/60577) | [JuliaLowering] Enrich closure tests and fix static parameter capture | 2026-01-12 |
| [#60597](https://github.com/JuliaLang/julia/pull/60597) | flisp: Port closure box optimization fixes from JuliaLowering.jl | 2026-01-09 |
| [#60619](https://github.com/JuliaLang/julia/pull/60619) | [JuliaLowering] Fix-up handling of `stmt_offset` in `K"enter"` | 2026-01-09 |
| [#60646](https://github.com/JuliaLang/julia/pull/60646) | [JuliaLowering] Avoid analyzing variables 'owned' by outer closures | 2026-01-12 |

---

## Key API Changes by Version

### Julia 1.13

- **ccall lowering**: Syntactic distinction between pointer and name in ccall (PR #59165)
- **def-use correctness**: Fixed IR interpreter def-use map population (PR #56201)
- **GC safety**: Fixed missing GC root in `jl_type_error_global` (PR #59785)

### Julia 1.14

- **JuliaSyntax/JuliaLowering integration**: Opt-in Julia-based parser and lowering (PR #59870)
- **Reaching definitions**: Inference tracks `ssadef` for slots (PR #55601)
- **JITLink everywhere**: Default memory manager on all platforms (PR #60576)
- **Asymmetric fences**: New `Threads.atomic_fence_light/heavy()` APIs (PR #60311)
- **Box optimization**: Single-assigned captured variables avoid Box allocation (PR #60567)
- **GC API removal**: `jl_gc_external_obj_hdr_size()` removed (PR #60517)

---

*See changelogs for detailed impact analysis:*
- [`changelogs/v1.13-compiler-changelog.md`](changelogs/v1.13-compiler-changelog.md)
- [`changelogs/v1.14-compiler-changelog.md`](changelogs/v1.14-compiler-changelog.md)
