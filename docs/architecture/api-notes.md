## anthropic SDK usage

direct SDK, no langchain wrapper. pattern used everywhere:
```python
msg = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=256,
    messages=[{"role": "user", "content": prompt}],
)
block = msg.content[0]
if not isinstance(block, TextBlock):
    raise ValueError(f"unexpected block type: {type(block)}")
raw = block.text.strip()
```
**always check isinstance(block, TextBlock) before accessing .text. anthropic can return ToolUseBlock etc.**

used in:
- bplane.py _classify_with_llm() — max_tokens=256
- formation.py _call_llm() — max_tokens=1024
- consolidation.py _build_strategy_with_llm() — max_tokens=128
- workflow.py _llm_plan() — max_tokens=512
- workflow.py _evaluator() LLM path — max_tokens=128

## json parsing from LLM responses

all LLM calls expect JSON back. pattern:
```python
raw = re.sub(r"^```[a-z]*\n?", "", raw)
raw = re.sub(r"\n?```$", "", raw)
data = json.loads(raw)
```
strips markdown code fences before parsing. if LLM wraps in ```json ... ``` this handles it.

## qdrant client

local file-backed:
```python
QdrantClient(path="./qdrant_data")  # persistent
QdrantClient(":memory:")            # in-memory, fresh each run
```
**qdrant ":memory:" string is different from sqlite ":memory:". both happen to use same string but different behavior.**

upsert pattern (save() in storage.py):
```python
self._qdrant.upsert(
    collection_name="k_nodes",
    points=[PointStruct(
        id=node.id,        # UUID string
        vector=embedding,  # list[float], len=384
        payload={
            "level": int,
            "type": str,
            "strength": float,
            "active": bool,
        },
    )],
)
```
**qdrant point id must be UUID string or unsigned int. KNode.id is UUID string — fine.**

query pattern (search() in storage.py):
```python
hits = self._qdrant.query_points(
    collection_name="k_nodes",
    query=task_embedding,         # list[float]
    query_filter=qdrant_filter,   # Filter object
    limit=top_k,
).points                          # .points needed, returns ScoredPoint list
```
**use query_points not search — search is deprecated in newer qdrant-client.**
**hit.id is str|int union type, cast with str(hit.id) when passing to store.get().**

filter construction:
```python
from qdrant_client.models import Filter, FieldCondition, Condition, Range, MatchValue

must_conditions: list[Condition] = [
    FieldCondition(key="active", match=MatchValue(value=True)),
]
if level_band:
    lo, hi = level_band
    must_conditions.append(
        FieldCondition(key="level", range=Range(gte=lo, lte=hi))
    )
qdrant_filter = Filter(must=must_conditions)
```
**must annotate as list[Condition] not list[FieldCondition] — pydantic type invariance.**
**use MatchValue(value=True) not {"value": True} — old dict syntax removed in newer versions.**

## sentence-transformers

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding = model.encode(text).tolist()  # numpy array → python list for json/qdrant
```
**model.encode() returns numpy array. .tolist() needed before storing in qdrant or json.**
**vector dimension is 384 for all-MiniLM-L6-v2. hardcoded in _create_collection(size=384). if you change model you must recreate the qdrant collection.**

similarity:
```python
from sentence_transformers import util
score = float(util.cos_sim(embedding_a, embedding_b))
```
**util.cos_sim returns tensor, float() needed.**
**already normalized 0-1 for semantically related texts. no manual normalization needed.**

## langgraph

StateGraph with TypedDict state. all nodes receive full state dict, return partial update:
```python
def _my_node(self, state: MSKState) -> MSKState:
    # read
    task = state["task"]
    log = list(state["memory_log"])  # copy lists before mutating
    # compute
    log.append("something")
    # return full state with updates
    return {**state, "memory_log": log}
```
**always copy mutable fields (lists) before modifying. {**state} is shallow copy.**

conditional edges:
```python
g.add_conditional_edges(
    "evaluator",
    self._route,           # function: state → str (node name)
    {"executor": "executor", "memory_updater": "memory_updater"},
)
```
_route() returns one of the string keys in the dict.

compile and invoke:
```python
app = g.compile()
result = app.invoke(initial_state)  # returns final state dict
```