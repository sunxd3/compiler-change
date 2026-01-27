# Mooncake -> Julia Compiler Dependency Map

This document maps Mooncake source files to the Julia compiler source files they depend on.

## src/Mooncake.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 3 | Core.Compiler | Compiler/src/Compiler.jl |
| 38 | Core.Compiler.IRCode | Compiler/src/ssair/ir.jl |
| 38 | Core.Compiler.NewInstruction | Compiler/src/ssair/ir.jl |

## src/developer_tools.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 8 | Core.Compiler.IRCode | Compiler/src/ssair/ir.jl |

## src/interpreter/abstract_interpretation.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 25 | Base.Experimental.@MethodTable | base/reflection.jl |
| 27 | CC.AbstractInterpreter | Compiler/src/types.jl |
| 30 | CC.InferenceParams | Compiler/src/types.jl |
| 31 | CC.OptimizationParams | Compiler/src/types.jl |
| 32 | CC.InferenceResult | Compiler/src/types.jl |
| 40 | CC.InferenceParams | Compiler/src/types.jl |
| 41 | CC.OptimizationParams | Compiler/src/types.jl |
| 55 | CC._methods_by_ftype | Compiler/src/Compiler.jl |
| 56 | CC.MethodMatch | Compiler/src/methodtable.jl, Compiler/src/stmtinfo.jl, Compiler/src/abstractinterpretation.jl |
| 59 | CC.unwraptv | Compiler/src/typeutils.jl |
| 61 | CC.typeinf_type | Compiler/src/typeinfer.jl |
| 83 | CC.InferenceParams | Compiler/src/types.jl |
| 84 | CC.OptimizationParams | Compiler/src/types.jl |
| 85 | CC.get_inference_cache | Compiler/src/types.jl |
| 86 | CC.code_cache | Compiler/src/types.jl, Compiler/src/optimize.jl |
| 87 | CC.WorldView | Compiler/src/cicache.jl |
| 87 | CC.WorldRange | Compiler/src/cicache.jl |
| 89 | CC.get | Compiler/src/cicache.jl |
| 89 | CC.WorldView | Compiler/src/cicache.jl |
| 92 | CC.getindex | Compiler/src/cicache.jl |
| 95 | CC.haskey | Compiler/src/cicache.jl |
| 98 | CC.setindex! | Compiler/src/cicache.jl |
| 103 | CC.method_table | Compiler/src/types.jl |
| 104 | CC.OverlayMethodTable | Compiler/src/methodtable.jl |
| 108 | CC.get_world_counter | Compiler/src/Compiler.jl, Compiler/src/types.jl |
| 109 | CC.get_inference_world | Compiler/src/types.jl |
| 112 | CC.cache_owner | Compiler/src/types.jl |
| 116 | CC.CallInfo | Compiler/src/types.jl |
| 121 | CC.nsplit_impl | Compiler/src/types.jl, Compiler/src/stmtinfo.jl |
| 121 | CC.nsplit | Compiler/src/stmtinfo.jl |
| 122 | CC.getsplit_impl | Compiler/src/types.jl, Compiler/src/stmtinfo.jl |
| 122 | CC.getsplit | Compiler/src/stmtinfo.jl |
| 123 | CC.getresult_impl | Compiler/src/types.jl, Compiler/src/stmtinfo.jl |
| 123 | CC.getresult | Compiler/src/stmtinfo.jl |
| 125 | CC.add_edges_impl | Compiler/src/stmtinfo.jl |
| 125 | CC.add_edges! | Compiler/src/types.jl, Compiler/src/stmtinfo.jl, Compiler/src/typeinfer.jl |
| 130 | Core.Compiler.abstract_call_gf_by_type | Compiler/src/abstractinterpretation.jl |
| 133 | CC.ArgInfo | Compiler/src/types.jl |
| 134 | CC.StmtInfo | Compiler/src/types.jl |
| 136 | CC.AbsIntState | Compiler/src/inferencestate.jl |
| 152 | CC.typeinf_lattice | Compiler/src/types.jl |
| 153 | Core.Compiler.find_matching_methods | Compiler/src/abstractinterpretation.jl |
| 157 | Core.Compiler.method_table | Compiler/src/types.jl |
| 158 | Core.Compiler.InferenceParams | Compiler/src/types.jl |
| 162 | Core.Compiler.find_method_matches | Compiler/src/abstractinterpretation.jl |
| 164 | Core.Compiler.FailedMethodMatch | Compiler/src/abstractinterpretation.jl |
| 170 | CC.CallMeta | Compiler/src/stmtinfo.jl |
| 174 | CC.Future | Compiler/src/inferencestate.jl |
| 209 | CC.inlining_policy | Compiler/src/ssair/inlining.jl |
| 249 | CC.src_inlining_policy | Compiler/src/optimize.jl |

## src/interpreter/bbcode.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 10 | Core.Compiler | Compiler/src/Compiler.jl |
| 20 | Core.Compiler | Compiler/src/Compiler.jl |
| 48 | CC.IR_FLAG_REFINED | Compiler/src/optimize.jl |
| 58 | CC.NoCallInfo | Compiler/src/stmtinfo.jl |
| 280 | CC.VarState | Compiler/src/types.jl |
| 282 | CC.DebugInfoStream | Compiler/src/ssair/ir.jl |
| 284 | CC.WorldRange | Compiler/src/cicache.jl |
| 338 | CC.copy | Compiler/src/ssair/ir.jl |
| 455 | Core.Compiler.CFG | Compiler/src/ssair/ir.jl |
| 489 | Core.Compiler.StmtRange | Compiler/src/ssair/basicblock.jl |
| 490 | Core.Compiler.BasicBlock | Compiler/src/ssair/basicblock.jl |
| 496 | CC.CFG | Compiler/src/ssair/ir.jl |
| 521 | CC.block_for_inst | Compiler/src/ssair/ir.jl |
| 662 | CC.IRCode | Compiler/src/ssair/ir.jl |
| 679 | CC.InstructionStream | Compiler/src/ssair/ir.jl |

## src/interpreter/forward_mode.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 183 | CC.copy | Compiler/src/ssair/ir.jl |
| 189 | CC.widenconst | Compiler/src/typelattice.jl |
| 208 | CC.compact! | Compiler/src/ssair/ir.jl |
| 210 | CC.verify_ir | Compiler/src/ssair/verify.jl |
| 262 | CC.insert_node! | Compiler/src/ssair/ir.jl |
| 414 | CC.NewInstruction | Compiler/src/ssair/ir.jl |
| 444 | CC.IRCode | Compiler/src/ssair/ir.jl |
| 489 | CC.MethodInstance | Compiler/src/Compiler.jl |

## src/interpreter/ir_normalisation.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 25 | CC.VarState | Compiler/src/types.jl |
| 45 | CC.verify_ir | Compiler/src/ssair/verify.jl |
| 125 | CC.widenconst | Compiler/src/typelattice.jl |
| 127 | CC.return_type | Compiler/src/typeinfer.jl |
| 134 | CC.get_ci_mi | Compiler/src/Compiler.jl |
| 255 | CC.scan_leaf_partitions | Compiler/src/abstractinterpretation.jl |
| 258 | CC.WorldWithRange | Compiler/src/inferencestate.jl |
| 258 | CC.min_world | Compiler/src/cicache.jl |
| 260 | CC.is_defined_const_binding | Compiler/src/Compiler.jl |
| 260 | CC.binding_kind | Compiler/src/Compiler.jl |
| 263 | CC.max_world | Compiler/src/cicache.jl |

## src/interpreter/ir_utils.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 4 | CC.InstructionStream | Compiler/src/ssair/ir.jl |
| 9 | CC.getfield | Compiler/src/ssair/ir.jl |
| 12 | CC.Instruction | Compiler/src/ssair/ir.jl |
| 16 | CC.getindex | Compiler/src/ssair/ir.jl |
| 27 | CC.setindex! | Compiler/src/ssair/ir.jl |
| 33 | CC.NoCallInfo | Compiler/src/stmtinfo.jl |
| 34 | CC.IR_FLAG_REFINED | Compiler/src/optimize.jl |
| 42 | CC.VarState | Compiler/src/types.jl |
| 59 | CC.compute_basic_blocks | Compiler/src/ssair/ir.jl |
| 63 | CC.DebugInfoStream | Compiler/src/ssair/ir.jl |
| 63 | CC.DebugInfo | Compiler/src/ssair/ir.jl |
| 65 | CC.LineInfoNode | Compiler/src/ssair/show.jl |
| 68 | CC.IRCode | Compiler/src/ssair/ir.jl |
| 94 | CC.InstructionStream | Compiler/src/ssair/ir.jl |
| 97 | CC.CallInfo | Compiler/src/types.jl |
| 115 | CC.NativeInterpreter | Compiler/src/types.jl |
| 123 | CC.widenconst | Compiler/src/typelattice.jl |
| 130 | CC.AbstractInterpreter | Compiler/src/types.jl |
| 130 | CC.MethodInstance | Compiler/src/Compiler.jl |
| 138 | CC.SpecInfo | Compiler/src/types.jl |
| 140 | CC.IRInterpretationState | Compiler/src/inferencestate.jl |
| 143 | CC.ir_abstract_constant_propagation | Compiler/src/ssair/irinterp.jl |
| 145 | CC.MethodInfo | Compiler/src/inferencestate.jl |
| 151 | CC._ir_abstract_constant_propagation | Compiler/src/ssair/irinterp.jl |
| 180 | CC.verify_ir | Compiler/src/ssair/verify.jl |
| 182 | CC.compact! | Compiler/src/ssair/ir.jl |
| 192 | CC.InliningState | Compiler/src/optimize.jl |
| 195 | CC.ssa_inlining_pass! | Compiler/src/ssair/inlining.jl |
| 199 | CC.sroa_pass! | Compiler/src/ssair/passes.jl |
| 202 | CC.adce_pass! | Compiler/src/ssair/passes.jl |
| 210 | CC.verify_linetable | Compiler/src/ssair/verify.jl |
| 223 | CC.MethodLookupResult | Compiler/src/methodtable.jl |
| 240 | CC.findall | Compiler/src/methodtable.jl |
| 246 | CC.typeinf_ircode | Compiler/src/typeinfer.jl |
| 250 | Core.Compiler.typeinf_ircode | Compiler/src/typeinfer.jl |
| 384 | CC.userefs | Compiler/src/ssair/ir.jl |
| 385 | CC.iterate | Compiler/src/ssair/ir.jl |

## src/interpreter/patch_for_319.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 20 | CC.AbstractInterpreter | Compiler/src/types.jl |
| 21 | CC.NativeInterpreter | Compiler/src/types.jl |
| 70 | CC.TwoPhaseDefUseMap | Compiler/src/inferencestate.jl |
| 70 | CC.BBScanner | Compiler/src/ssair/irinterp.jl |
| 72 | CC.scan! | Compiler/src/ssair/irinterp.jl |
| 76 | CC.push! | Compiler/src/ssair/irinterp.jl |
| 86 | CC.IRInterpretationState | Compiler/src/inferencestate.jl |
| 91 | CC.isempty | Compiler/src/ssair/ir.jl |
| 111 | CC.has_flag | Compiler/src/optimize.jl |
| 113 | CC.sub_flag! | Compiler/src/ssair/ir.jl |
| 114 | CC.is_all_const_call | Compiler/src/ssair/irinterp.jl |
| 124 | CC.count! | Compiler/src/inferencestate.jl |
| 127 | CC.PhiNode | Compiler/src/ssair/ir.jl |
| 127 | CC.in | Compiler/src/ssair/ir.jl |
| 129 | CC.delete! | Compiler/src/ssair/ir.jl |
| 134 | CC.isterminator | Compiler/src/ssair/ir.jl |
| 139 | CC.Bottom | Compiler/src/typelattice.jl |
| 143 | CC.reprocess_instruction! | Compiler/src/ssair/irinterp.jl |
| 150 | CC.kill_terminator_edges! | Compiler/src/ssair/irinterp.jl |
| 164 | CC.BitSetBoundedMinPrioritySet | Compiler/src/inferencestate.jl |
| 191 | CC.complete! | Compiler/src/inferencestate.jl |
| 207 | CC.popfirst! | Compiler/src/inferencestate.jl |
| 211 | CC.append! | Compiler/src/inferencestate.jl |
| 224 | CC.argextype | Compiler/src/optimize.jl |
| 225 | CC.tmerge | Compiler/src/abstractlattice.jl |
| 225 | CC.typeinf_lattice | Compiler/src/types.jl |
| 236 | CC.IR_FLAG_NOTHROW | Compiler/src/optimize.jl |
| 237 | CC.IR_FLAG_NOUB | Compiler/src/optimize.jl |
| 243 | CC.AbsIntState | Compiler/src/inferencestate.jl |
| 248 | CC.last | Compiler/src/ssair/ir.jl |
| 251 | CC.store_backedges | Compiler/src/typeinfer.jl |
| 251 | CC.frame_instance | Compiler/src/inferencestate.jl |
| 256 | CC.maybe_singleton_const | Compiler/src/utilities.jl |
| 271 | CC.PostOptAnalysisState | Compiler/src/optimize.jl |
| 278 | CC.EnterNode | Compiler/src/inferencestate.jl, Compiler/src/validation.jl |
| 280 | CC.give_up_refinements! | Compiler/src/optimize.jl |
| 284 | CC.scan_non_dataflow_flags! | Compiler/src/optimize.jl |
| 304 | CC.visit_conditional_successors | Compiler/src/optimize.jl |
| 307 | CC.any_stmt_may_throw | Compiler/src/optimize.jl |
| 312 | CC.get! | Compiler/src/optimize.jl |
| 313 | CC.iterated_dominance_frontier | Compiler/src/ssair/slot2ssa.jl |
| 315 | CC.BlockLiveness | Compiler/src/ssair/slot2ssa.jl |
| 318 | CC.length | Compiler/src/ssair/ir.jl |
| 323 | CC.visit_bb_phis! | Compiler/src/optimize.jl |
| 345 | CC.IR_FLAG_CONSISTENT | Compiler/src/optimize.jl |
| 349 | CC.iscall_with_boundscheck | Compiler/src/optimize.jl |
| 371 | CC.ipo_dataflow_analysis! | Compiler/src/optimize.jl |
| 374 | CC.is_ipo_dataflow_analysis_profitable | Compiler/src/optimize.jl |
| 393 | CC.any_refinable | Compiler/src/optimize.jl |
| 401 | CC.refine_effects! | Compiler/src/optimize.jl |
| 424 | CC.LazyDomtree | Compiler/src/inferencestate.jl |

## src/interpreter/reverse_mode.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 182 | CC.widenconst | Compiler/src/typelattice.jl |
| 920 | Core.Compiler.return_type | Compiler/src/typeinfer.jl |
| 1027 | CC.widenconst | Compiler/src/typelattice.jl |
| 1034 | CC.widenconst | Compiler/src/typelattice.jl |
| 1381 | CC.widenconst | Compiler/src/typelattice.jl |
| 1913 | CC.widenconst | Compiler/src/typelattice.jl |

## src/rules/foreigncall.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 100 | CC.return_type | Compiler/src/typeinfer.jl |
| 369 | Core.Compiler.return_type | Compiler/src/typeinfer.jl |

## src/rules/misc.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 16 | Core.Compiler.sizeof_nothrow | Compiler/src/tfuncs.jl |

## src/tangents/tangents.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 384 | Core.Compiler.InferenceState | Compiler/src/inferencestate.jl |
| 386 | Core.Compiler.Timings.Timing | Compiler/src/typeinfer.jl |
| 388 | Core.Compiler.InferenceResult | Compiler/src/types.jl |
| 391 | Core.Compiler.AnalysisResults | Compiler/src/types.jl |
| 1405 | CC.datatype_min_ninitialized | Compiler/src/Compiler.jl, Compiler/src/tfuncs.jl |

## src/test_resources.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 655 | CC.PartialTypeVar | Compiler/src/typelattice.jl |

## src/test_utils.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 1110 | CC.ALWAYS_TRUE | Compiler/src/effects.jl |

## src/utils.jl

| Line | Symbol | Julia Source |
|------|--------|--------------|
| 220 | CC.datatype_min_ninitialized | Compiler/src/Compiler.jl, Compiler/src/tfuncs.jl |
| 333 | CC.copy | Compiler/src/ssair/ir.jl |
| 338 | CC.CodeInfo | Compiler/src/Compiler.jl |
| 350 | CC.ir_to_codeinf! | Compiler/src/optimize.jl |
| 352 | Base.Experimental.generate_opaque_closure | base/opaque_closure.jl |
| 381 | CC.compute_ir_rettype | Compiler/src/opaque_closure.jl |
| 382 | CC.compute_oc_signature | Compiler/src/opaque_closure.jl |
| 384 | Base.Experimental.compute_ir_rettype | base/opaque_closure.jl |
| 385 | Base.Experimental.compute_oc_signature | base/opaque_closure.jl |

---

## Summary: Julia Compiler Files Used by Mooncake

### Core Compiler Files

| Julia Source File | Usage Count |
|-------------------|-------------|
| Compiler/src/types.jl | 31 |
| Compiler/src/ssair/ir.jl | 30 |
| Compiler/src/optimize.jl | 22 |
| Compiler/src/inferencestate.jl | 14 |
| Compiler/src/ssair/irinterp.jl | 8 |
| Compiler/src/typelattice.jl | 8 |
| Compiler/src/stmtinfo.jl | 8 |
| Compiler/src/typeinfer.jl | 8 |
| Compiler/src/Compiler.jl | 8 |
| Compiler/src/abstractinterpretation.jl | 6 |
| Compiler/src/methodtable.jl | 5 |
| Compiler/src/cicache.jl | 5 |
| Compiler/src/ssair/verify.jl | 4 |
| Compiler/src/ssair/inlining.jl | 2 |
| Compiler/src/ssair/passes.jl | 2 |
| Compiler/src/ssair/basicblock.jl | 2 |
| Compiler/src/ssair/slot2ssa.jl | 2 |
| Compiler/src/ssair/show.jl | 1 |
| Compiler/src/tfuncs.jl | 2 |
| Compiler/src/typeutils.jl | 1 |
| Compiler/src/utilities.jl | 1 |
| Compiler/src/abstractlattice.jl | 1 |
| Compiler/src/effects.jl | 1 |
| Compiler/src/opaque_closure.jl | 2 |
| Compiler/src/validation.jl | 1 |

### Base Files

| Julia Source File | Usage Count |
|-------------------|-------------|
| base/opaque_closure.jl | 3 |
| base/reflection.jl | 1 |
