## run the demo first
```bash
mamba activate msk
cd msk_v0
python demo.py   # no API key needed
```
expected: 4 phases, phase 3 shows make failing, phase 4 uses npm

## symptom checklist

### "Evaluator:  success" after step 1 (ls)
evaluator bug is back. check workflow.py _evaluator():
- must have `test_keywords = ("test-integration", "test:integration", "pytest", "jest", "spec")`
- must scan ALL results with next(...) not just check last["success"]
- no_llm path must NOT do `success = last["success"]` directly

### make knode strength going UP in phase 3
memory_updater not doing per-node check. look for this pattern in _memory_updater:
```python
preferred = node.content.structured.get("preferred_commands", [])
if preferred:
    cmd_succeeded = any(
        r["success"] and any(cmd in r["command"] for cmd in preferred)
        for r in state["execution_results"]
    )
```
if this block is missing, it falls back to overall task success

### ls knode being formed
TRIVIAL_COMMANDS filter not applied. check formation.py:
```python
if event.tool_input and event.tool_input.strip() in TRIVIAL_COMMANDS:
    continue
```
must be BEFORE the success/failure check in _extract_rule_based

### consolidation crash ("object has no attribute 'append'" or similar)
old KNodeRelations API. grep consolidation.py for:
- `.contradicts.append` → replace with `.relations.add(id, "contradicts")`
- `KNodeRelations(specializes=` → replace with loop using .add()

### qdrant search returns nothing
either:
- knode was never saved to qdrant (check save() wrote both stores)
- qdrant ":memory:" was used and process restarted (fresh collection each time)
- embedding dimension mismatch (collection was created with wrong size)
  → delete qdrant data dir and recreate

### "no K-nodes reactivated" in phase 1
seed_demo_knowledge() was not called, or was called before store was created.
check demo.py main() — seed must come after KNodeStore() and before first run_phase()

### bplane always returns diagnostic
heuristic fallback keywords may not match your task string. check bplane.py _classify_heuristic():
- diagnostic: "debug", "fix", "error", "fail", "broken", "crash"
- procedural: "run", "execute", "test", "deploy", "install"
- strategic: "design", "plan", "architect", "decide"
- high_risk: "delete", "drop", "remove", "security", "credential"
if task string doesnt contain these, falls through to diagnostic default

### preferred_commands not extracted in _fallback_plan
_fallback_plan uses regex to find backtick-wrapped commands in agent_guidance string.
if planner_bias.instructions contain "Use npm run test:integration" without backticks, it wont be found.
check workflow.py _planner():
```python
cmds = "  ".join(f"`{c}`" for c in planner_bias.preferred_commands)
```
the backtick wrapping happens here. preferred_commands (not instructions) are backtick-wrapped.
_fallback_plan looks for these with:
```python
cmds = re.findall(r"`([^`]+)`", line)
```

## useful one-liners

check kplane state:
```python
from msk.storage import KNodeStore
store = KNodeStore("your.db")
for n in store.all_active():
    print(n.type.value, n.lifecycle.strength, n.content.text[:60])
```

check qdrant collection:
```python
from qdrant_client import QdrantClient
q = QdrantClient(path="./qdrant_data")
print(q.get_collection("k_nodes"))
print(q.count("k_nodes"))
```

run single workflow manually:
```python
from msk.storage import KNodeStore
from sim.environment import SimulatedRepository
from workflow import MSKWorkflow

store = KNodeStore(":memory:")
env = SimulatedRepository(1)
wf = MSKWorkflow(client=None, store=store, env=env, no_llm=True)
state = wf.run("integration tests failing, fix them", mode="msk")
print(state["memory_log"])
print(state["success"])
```

## logging
memory_log in state is the main debug surface. every node appends to it.
look for these prefixes:
- `B-plane [msk]` — classification and reactivation
- `Planner` — plan built
- `Executor [✓/✗]` — command result
- `Evaluator` — success check
- `Memory updater` — knode writes

rich output in demo.py color-codes these. in evaluate.py they are not printed by default (only summary table). to debug evaluate.py add print(state["memory_log"]) inside run_condition().