# MSK v0

Experimental project currently in development.

# Execution stacktrace:

```
demo.py
└── main()
    ├── load_dotenv()
    ├── os.getenv("ANTHROPIC_API_KEY")
    ├── anthropic.Anthropic(...) OR client=None
    ├── KNodeStore(":memory:")
    │   ├── __init__()
    │   ├── _create_schema()
    │   └── _create_collection()
    ├── SimulatedRepository(version=1)
    ├── MSKWorkflow(...)
    │   ├── __init__()
    │   ├── BPlane(...)
    │   ├── FormationModule(...)
    │   ├── ReactivationPlanner(...)
    │   ├── ConsolidationModule(...)
    │   └── _build_graph()
    │       ├── add_node(memory_controller)
    │       ├── add_node(planner)
    │       ├── add_node(executor)
    │       ├── add_node(evaluator)
    │       ├── add_node(memory_updater)
    │       └── compile()
    ├── seed_demo_knowledge(store)
    │   ├── KNode(...)
    │   ├── KNodeTriggers()
    │   ├── triggers.add(...)
    │   └── store.save(node)
    │       ├── _embed(...)
    │       ├── node.is_active()
    │       └── qdrant.upsert(...)
    │
    ├── run_phase(phase 1)
    │   └── wf.run(TASK, mode="msk")
    │       └── app.invoke(state)
    │           ├── _memory_controller(state)
    │           │   ├── bplane.classify(task)
    │           │   │   ├── _classify_heuristic(task)  # no_llm
    │           │   │   └── OR _classify_with_llm(task)
    │           │   └── reactivation.reactivate(...)
    │           │       ├── should_retrieve_memory(...)
    │           │       ├── _collect_candidates(...)
    │           │       │   ├── store.search(task, ...)
    │           │       │   ├── store.search(classification.scope, ...)
    │           │       │   └── store.by_level_band(...)
    │           │       ├── node.is_active()
    │           │       ├── _resolve_conflicts(...)
    │           │       ├── _score_candidates(...)
    │           │       │   ├── store._embed(task)
    │           │       │   ├── store._embed(node.content.text)
    │           │       │   └── bplane.compute_activation_score(...)
    │           │       └── _build_packet(...)
    │           │
    │           ├── _planner(state)
    │           │   ├── ActivationPacket.model_validate(...)
    │           │   ├── packet.for_agent("planner")
    │           │   └── _fallback_plan(...) OR _llm_plan(...)
    │           │
    │           ├── _executor(state)
    │           │   └── env.execute(command)
    │           │       ├── _ls()
    │           │       ├── _readme()
    │           │       ├── _make_test()
    │           │       └── _npm_test()
    │           │
    │           ├── _evaluator(state)
    │           │   ├── scan all execution_results
    │           │   ├── if successful test command found → success=True
    │           │   └── else continue / LLM evaluate
    │           │
    │           ├── _route(state)
    │           │   ├── executor again
    │           │   └── OR memory_updater
    │           │
    │           └── _memory_updater(state)
    │               ├── ActivationPacket.model_validate(...)
    │               ├── for each selected K-node:
    │               │   ├── store.get(nid)
    │               │   ├── check whether node.preferred_commands succeeded
    │               │   ├── node.record_use(cmd_succeeded)
    │               │   └── store.update(node)
    │               ├── formation.extract(events, task_id)
    │               │   ├── _extract_rule_based(...)
    │               │   └── OR _call_llm(...) → _build_k_node(...)
    │               ├── store.save(new_node)
    │               ├── consolidation.run()
    │               │   ├── store.all_active()
    │               │   ├── _deduplicate(...)
    │               │   ├── _detect_contradictions(...)
    │               │   ├── _abstract_episodes()
    │               │   └── _decay(...)
    │               └── store.stats()
    │
    ├── show_kplane(store)
    │   └── store.all_active()
    │
    ├── run_phase(phase 2)
    │   └── same wf.run(...) graph
    │
    ├── show_kplane(store)
    ├── env.migrate_to_v2()
    ├── run_phase(phase 3)
    │   └── same wf.run(...) graph
    ├── show_kplane(store)
    ├── run_phase(phase 4)
    │   └── same wf.run(...) graph
    ├── show_kplane(store)
    └── print demo complete
```
