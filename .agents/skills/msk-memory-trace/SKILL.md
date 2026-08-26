---
name: msk-memory-trace
description: Trace one memory, K-node, task, or activation path end-to-end through MSK. Use for debugging whether stored memory actually affects behavior, locating broken handoffs, or proving where formation, retrieval, reactivation, lifecycle updates, and consolidation do or do not connect.
---

# MSK Memory Trace

Trace a concrete memory path through the repository and distinguish representation from actual behavioral effect.

## Start from a concrete anchor

Accept one of:

- a K-node id;
- a task string;
- a memory text fragment;
- a command/tool pattern;
- a relation target;
- a failing behavior the user wants explained.

If no explicit anchor is given, choose the smallest representative path relevant to the question and state the choice.

## Read order

Read `AGENTS.md`, then follow the runtime path rather than scanning files independently.

Typical path:

`workflow.py` -> B-plane classification -> `ReactivationPlanner` -> `KNodeStore` -> `ActivationPacket` -> planner/executor/evaluator -> memory updater -> formation/consolidation -> later retrieval.

Also inspect `demo.py`, `evaluate.py`, and `sim/` when the trace depends on their setup or observable outcome.

## Trace dimensions

For the target, record:

1. **Creation** — what event/input creates it, by which function, and with which fields.
2. **Persistence** — where it is written and whether all representations are updated.
3. **Eligibility** — `is_active`, governance, level-band, filters, and any other gates.
4. **Candidate collection** — which retrieval channels can discover it.
5. **Scoring/selection** — what determines whether it survives to the selected set.
6. **Packet translation** — how node type, activation mode, target agents, structured content, triggers, and relations are translated into `ActivationPacket` / `AgentBias`.
7. **Consumption** — the exact downstream branch that reads the packet or bias.
8. **Observable effect** — what plan, command, check, constraint, or outcome changes because of it.
9. **Feedback** — how success/failure updates strength, counts, relations, or newly formed nodes.
10. **Consolidation/evolution** — whether deduplication, contradiction, abstraction, decay, or supersession changes it.
11. **Next-task consequence** — how the updated memory can affect a later task.

## Use explicit status labels

For each stage, classify the target as:

- **PRESENT** — data exists at this stage;
- **READ** — code consumes it;
- **DECISION_RELEVANT** — it changes a branch, ranking, prompt, command, constraint, or other action;
- **NO_EFFECT** — it survives structurally but no downstream behavior uses it;
- **BROKEN** — intended handoff fails in current code;
- **UNPROVEN** — static inspection cannot establish the effect.

Do not equate `PRESENT` with `DECISION_RELEVANT`.

## Relations and graph checks

When relations are involved, trace both directions explicitly:

- where the edge is created;
- where it is persisted;
- which accessor exposes it;
- whether reactivation traverses it;
- whether its weight/provenance is consumed;
- whether conflict resolution uses it;
- whether it changes the final packet.

If an edge exists but is never followed, report it as represented-only rather than graph propagation.

## Compare modes when relevant

If behavior may differ, compare:

- `mode="msk"`;
- repository-style retrieval baseline;
- no-memory behavior;
- LLM versus `no_llm` fallback.

Only compare modes that are relevant to the requested trace.

## Output

Return:

1. a compact stage-by-stage trace;
2. the first point where the memory becomes decision-relevant;
3. any stage where intended information is dropped or transformed incorrectly;
4. file + symbol evidence for each material step;
5. the minimal reproduction or test that would confirm any unproven runtime claim.

Keep the output diagnostic. Do not propose broad redesigns unless the trace reveals a structural problem that cannot be fixed locally.