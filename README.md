# MSK v0

Minimal implementation of the MSK architecture from  
*"MSK: K-S System for Multi-Agent Architectures — Reconsidering Minsky's Society of Mind"*.

## Architecture

```
B-plane (memory_controller)
   ↓  classification + activation packet
S-plane: planner → executor → evaluator
                                  ↓
                          memory_updater
                         (formation + consolidation)
```

**K-plane**: SQLite + BM25 search. Each K-node stores content, activation metadata,
provenance, lifecycle (strength, use/success/failure counts), and relations.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python demo.py                # four-phase lifecycle demo
python evaluate.py            # none vs repository vs msk comparison
```

## Files

| File | Purpose |
|------|---------|
| `msk/models.py` | K-node, Event, ActivationPacket schemas |
| `msk/storage.py` | SQLite store + BM25 retrieval |
| `msk/bplane.py` | Task classification + level-band policy (Eq. 2) |
| `msk/formation.py` | Events → K-nodes via Claude |
| `msk/reactivation.py` | Multi-channel search → ActivationPacket |
| `msk/consolidation.py` | Dedup, contradiction, abstraction, decay |
| `sim/environment.py` | Simulated repository (v1: make, v2: npm) |
| `workflow.py` | LangGraph S-plane (5 nodes) |
| `demo.py` | The paper's make→npm lifecycle example |
| `evaluate.py` | Three-condition evaluation |

## Demo scenario

The demo runs the paper's central example:

1. **Learning** — first run, no K-nodes; agent discovers `make test-integration`
2. **Reactivation** — K-node reactivated; planner pre-configured with correct command
3. **Migration** — repo switches to npm; old K-node fails, gets superseded
4. **Recovery** — new K-node active; agent uses `npm run test:integration` directly

## Persistent storage

Pass a file path to use persistent K-nodes across runs:

```python
store = KNodeStore("msk_memory.db")
```
