## works
- models.py: full schema, graph-based triggers/relations, all data classes
- storage.py: sqlite + qdrant dual write, semantic search via sentence-transformers cos_sim
- bplane.py: LLM classify + heuristic fallback, level-band selection, composite score
- formation.py: LLM extraction + rule-based fallback, trivial commands filter
- reactivation.py: multi-channel search (semantic + type + level), activation packet builder, conflict resolution
- workflow.py: full langgraph graph, no_llm flag, seed works, evaluator fixed (mostly)
- demo.py: 4-phase lifecycle, no_llm mode, rich output
- evaluate.py: 3-condition comparison, metrics table
- sim/environment.py: v1 (make works) / v2 (npm only), migrate_to_v2()

## partially working
- consolidation.py: dedup (jaccard) works, abstraction works IF llm available, graph linking broken (old syntax), decay uses wrong datetime
- evaluator: fixed for test_keywords scan but verify the no_llm fallback path doesnt short-circuit too early
- memory_updater: per-node strengthening/weakening works, but only if preferred_commands field is populated in knode content.structured

## broken / risky
- consolidation._detect_contradictions: calls node.relations.contradicts.append() — old API, KNodeRelations is now graph-based
- consolidation._make_strategy_node: constructs KNodeRelations(specializes=[...]) — old API, will fail
- graph traversal in reactivation: coactivates_with edges never followed
- dual-write atomicity: save() writes to sqlite then qdrant, no rollback if qdrant fails

## module map
models.py — data layer, all pydantic models  
storage.py — persistence, KNodeStore class  
bplane.py — BPlane class, classify(), compute_activation_score()  
formation.py — FormationModule, extract(), _extract_rule_based()  
reactivation.py — ReactivationPlanner, reactivate(), retrieve_repository_style()  
consolidation.py — ConsolidationModule, run() calls all 6 ops  
workflow.py — MSKWorkflow, LangGraph graph, all 5 node methods  
demo.py — main(), seed_demo_knowledge(), run_phase()  
evaluate.py — run_condition(), _record(), main()  
sim/environment.py — SimulatedRepository, execute(), migrate_to_v2()

## data flow (msk mode)
user task string  
→ memory_controller: BPlane.classify() → level_band  
→ ReactivationPlanner.reactivate() → ActivationPacket  
→ planner: reads packet.for_agent("planner") → builds plan  
→ executor: runs each step against SimulatedRepository  
→ evaluator: scans all results for test_keywords success  
→ memory_updater: record_use() per knode, FormationModule.extract(), ConsolidationModule.run()

## external dependencies
- ANTHROPIC_API_KEY: needed for LLM mode, optional for no_llm
- sentence-transformers: downloads all-MiniLM-L6-v2 on first run
- qdrant: local file-backed, no server needed
- sqlite: stdlib, no config

## important runtime notes
- KNodeStore(":memory:") = fresh qdrant collection each run (intentional for demo)
- KNodeStore("path/to/file.db") = persistent (use for evaluation)
- MSKWorkflow(client=None, no_llm=True) = fully offline mode
- seed_demo_knowledge(store) must be called AFTER store created, BEFORE first run_phase

