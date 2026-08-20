## priority fixes

**fix consolidation.py** (both bugs)
- _detect_contradictions: replace `a.relations.contradicts.append(b.id)` with `a.relations.add(b.id, "contradicts")`
- _make_strategy_node: replace KNodeRelations(specializes=[...]) with:
```python
  relations = KNode.KNodeRelations()
  for ep in episodes: relations.add(ep.id, "specializes")
```
- also fix datetime.utcnow() → datetime.now(timezone.utc) in _decay
- file: msk/consolidation.py

**verify evaluator**
- run demo.py, check that phases 3 and 4 show make failing and npm succeeding
- if you still see "Executor [✓] ls → Evaluator: success" the bug is back
- file: workflow.py, _evaluator()

**verify bplane sim_score rename**
- check if compute_activation_score() parameter is still called bm25_score or was renamed to sim_score
- file: msk/bplane.py

## soon

**run actual evaluation**
- evaluate.py currently works but has never been run to completion cleanly
- need qdrant file path not :memory: for persistence across conditions
- 3 conditions × 6 tasks × ~3 runs minimum for any meaningful numbers
- metrics: success rate, correct command rate v2, steps to solution

**add missing paper citations**
- Quillian 1968: "Semantic Memory" in Minsky ed., Semantic Information Processing, MIT Press
- Collins & Loftus 1975: Psychological Review
- Anderson ACT-R 1983: The Architecture of Cognition
- Tulving 1972/1983: episodic/semantic distinction
- Greshake et al 2023: indirect prompt injection (for security section)
- all currently mentioned in text but missing from references.bib

**second task domain**
- bainsa proposal says single domain may not be enough for workshop
- customer support ticket resolution is natural fit (same memory types: tool patterns, user facts, superseded policies)
- needs a second SimulatedEnvironment class

## later

**implement graph traversal in reactivation**
- reactivation._collect_candidates() should follow coactivates_with edges from already-found nodes
- this is the K-recursion principle operationalized
- file: msk/reactivation.py, _collect_candidates()

**replace jaccard with semantic dedup in consolidation**
- currently uses word overlap (jaccard, threshold 0.65)
- could use store._embed() + cosine_sim for better duplicate detection
- file: msk/consolidation.py, _deduplicate()

**atomic dual-write in storage**
- save() writes sqlite then qdrant, no rollback
- if qdrant fails after sqlite write, stores go out of sync
- fix: wrap in try/except, rollback sqlite if qdrant fails
- file: msk/storage.py, save()

**expand TRIVIAL_COMMANDS**
- currently only catches exact strings, misses "ls -l", "cat readme.MD" etc
- could use prefix matching or a small regex
- file: msk/formation.py

**let agents' langgraph dynamically expand**
- understand how formation of new agents could work
- v0 S-plane is hardcoded — always planner, executor, evaluator, memory_controller regardless of task or domain
- `target_agents` field on KNodeActivation exists but is just a routing hint, not actual agent instantiation
- natural next step: parameterize `_build_graph()` to accept an agent list at construction time
- further: B-plane reads `target_agents` from activated K-nodes and spins up missing agents on demand
- even further: different domains (software debugging, customer support) carry different S-plane compositions stored as frame K-nodes — B-plane instantiates the right society for the current task
- file: `workflow.py` `_build_graph()`, `MSKWorkflow.__init__()`, `msk/bplane.py`


## optional

- B-plane learning from traces (currently rule-based only)
- skill distillation in consolidation (stub exists, not wired)
- parametric memory (out of scope for v0)
- spacy NER in formation for entity extraction into graph_entities
- persistent KNodeGraph class for in-memory adjacency list (discussed but not built)