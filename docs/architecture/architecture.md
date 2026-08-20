## planes

B-plane: BPlane class (bplane.py)

- classify(task) → TaskClassification (scope, level_band, uncertainty, risk)
- compute_activation_score(...) → float

K-plane: KNodeStore (storage.py) + KNode schema (models.py) (note on links to splane:you can't reach inside a LLM and re-engage specific internal circuits.)

- sqlite: structured queries, full knode json
- qdrant: vector search, payload filters

S-plane: MSKWorkflow nodes (workflow.py)

- memory_controller, planner, executor, evaluator, memory_updater

## execution flow (one task)
MSKWorkflow.run(task, mode="msk")  
→ MSKState initialized → LangGraph: **start** → memory_controller  
BPlane.classify(task) → classification ReactivationPlanner.reactivate(task, task_id, classification) → ActivationPacket → planner reads packet.for_agent("planner") → AgentBias builds plan (LLM or _fallback_plan) → executor [loops via _route until success or max_iterations]  SimulatedRepository.execute(command) → result dict  
appends Event to state["events"]  → evaluator  scans all execution_results for test_keywords + success returns success=True/False → memory_updater  
record_use() per selected knode (per-node, not overall)  formationModule.extract(events) → new knodes → store.save() ConsolidationModule.run() → dedup, contradiction, abstraction, decay  
→ **end**

## key classes
| class | file | instantiated in |
|---|---|---|
| KNodeStore | storage.py | demo.py / evaluate.py main() |
| BPlane | bplane.py | MSKWorkflow.__init__ |
| FormationModule | formation.py | MSKWorkflow.__init__ |
| ReactivationPlanner | reactivation.py | MSKWorkflow.__init__ |
| ConsolidationModule | consolidation.py | MSKWorkflow.__init__ |
| MSKWorkflow | workflow.py | demo.py / evaluate.py |
| SimulatedRepository | sim/environment.py | demo.py / evaluate.py |

## state lives in
- short term: MSKState TypedDict passed through LangGraph nodes
- long term: KNodeStore (sqlite + qdrant files or :memory:)
- activation context: ActivationPacket stored in state["activation_packet"] as dict

## interfaces between modules
- BPlane → ReactivationPlanner: TaskClassification (level_band)
- ReactivationPlanner → KNodeStore: search(task, level_band), get(id)
- ReactivationPlanner → BPlane: compute_activation_score()
- memory_updater → KNodeStore: get(), update(), save()
- memory_updater → FormationModule: extract(events, task_id)
- memory_updater → ConsolidationModule: run()
- ConsolidationModule → KNodeStore: all_active(), update()

## env vars
- ANTHROPIC_API_KEY: optional. if missing, no_llm mode activates automatically
## config buried in code (not env vars)
- SIMILARITY_THRESHOLD = 0.65 (consolidation.py) — jaccard dedup threshold
- DECAY_RATE = 0.02 (consolidation.py) — strength lost per day unused
- MIN_EPISODES_FOR_ABSTRACTION = 3 (consolidation.py)
- TRIVIAL_COMMANDS = {"ls", ...} (formation.py)
- model = "all-MiniLM-L6-v2" (storage.py __init__)
- collection_name = "k_nodes" (storage.py)
- vector size = 384 (storage.py _create_collection)

## where to look when things break
| symptom                    | look in                                               |
| -------------------------- | ----------------------------------------------------- |
| demo stops at ls           | workflow.py _evaluator, test_keywords                 |
| wrong knode formed         | formation.py _extract_rule_based, TRIVIAL_COMMANDS    |
| make knode not weakening   | workflow.py _memory_updater, preferred_commands check |
| consolidation crash        | consolidation.py, old KNodeRelations syntax           |
| qdrant empty               | storage.py save(), check both writes succeed          |
| no reactivation in phase 1 | demo.py, seed_demo_knowledge() called?                |