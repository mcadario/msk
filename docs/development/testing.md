## what exists
nothing formal. no pytest, no unit tests, no fixtures.
testing is entirely manual via demo.py and evaluate.py.

## manual test checklist

### after any change to models.py
```python
from msk.models import KNode, KNodeType, KNodeContent, Event, ActivationPacket, AgentBias
n = KNode(type=KNodeType.tool_pattern, content=KNode.KNodeContent(text="test"))
print(n.id)
print(n.is_active())

t = KNode.KNodeTriggers()
t.add("npm", "tool")
print(t.tool_names)  # should print ["npm"]

r = KNode.KNodeRelations()
r.add("other-id", "contradicts")
print(r.contradicts)  # should print ["other-id"]
```

### after any change to storage.py
```python
from msk.storage import KNodeStore
from msk.models import KNode, KNodeType, KNodeContent
store = KNodeStore(":memory:")
n = KNode(type=KNodeType.tool_pattern, content=KNode.KNodeContent(text="run npm test"))
store.save(n)
results = store.search("npm test integration")
print(len(results), results[0].content.text if results else "no results")
print(store.stats())
```

### after any change to workflow.py
```python
from msk.storage import KNodeStore
from sim.environment import SimulatedRepository
from workflow import MSKWorkflow

store = KNodeStore(":memory:")
env = SimulatedRepository(1)
wf = MSKWorkflow(client=None, store=store, env=env, no_llm=True)
state = wf.run("integration tests failing", mode="msk")

assert "success" in state
print("success:", state["success"])
print("steps:", len(state["execution_results"]))
for line in state["memory_log"]:
    print(line)
```

### full demo test
```bash
python demo.py
```
expected output markers:
- phase 1: "reactivated 1 K-node(s)" (seeded node)
- phase 1: "Executor [✓] make test-integration" — make should succeed on v1
- phase 1: "Evaluator: ✓ task succeeded via `make test-integration`"
- phase 3: "Executor [✗] make test-integration" — make fails on v2
- phase 3: "Executor [✓] npm run test:integration" — npm succeeds
- phase 3: "weakened 1 K-node(s)" — make node weakened
- phase 3: new npm knode formed
- phase 4: "Executor [✓] npm run test:integration" as early step — memory guided it

if any of these are wrong, something is broken.

## what should be written (but isnt)

unit tests for:
- KNodeStore.search() returns correct level_band filtered results
- BPlane._classify_heuristic() maps task strings to correct scopes
- ReactivationPlanner.reactivate() builds correct activation packet
- FormationModule._extract_rule_based() skips trivial commands, extracts tool patterns
- ConsolidationModule._deduplicate() merges near-duplicate knodes
- MSKWorkflow._route() returns correct next node

integration tests for:
- full task run, no_llm, v1 repo: assert npm knode not formed
- full task run, no_llm, v2 repo after learning on v1: assert npm knode reactivated
- memory_updater correctly weakens make knode on v2 task

## regression tests worth adding immediately

the ls-triggers-success bug came back twice. add this:
```python
def test_evaluator_does_not_succeed_on_ls():
    results = [
        {"step": 1, "command": "ls", "success": True, "returncode": 0, "stdout": "files...", "description": ""},
        {"step": 2, "command": "cat README.md", "success": True, "returncode": 0, "stdout": "readme", "description": ""},
    ]
    state = {
        "execution_results": results,
        "task": "fix integration tests",
        "memory_log": [],
        "success": False,
        "outcome": "",
        # ... other required MSKState fields
    }
    # evaluator should return success=False since no test command ran
```

the make-knode-strengthened-when-make-failed bug is also worth a regression test.