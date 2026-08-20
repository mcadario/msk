# MSK Architecture Report

## Executive conclusion

MSK v0 is currently best described as a **metadata-enriched semantic retrieval system with task classification, planner prompt configuration, and post-task memory updates**.

It is not yet a spreading-activation architecture or a society of mutually reactivating KNodes. “Activation” presently means:

1. retrieve and rank independent KNodes;
2. select the top few;
3. translate their metadata into an `ActivationPacket`;
4. inject context and planner guidance.

That is a useful step beyond plain RAG, but the runtime is substantially narrower than both the schema and the proposal suggest. The proposal itself recognizes activation packets as an approximation of reactivation rather than full state reconstruction. MSK-proposal_v2.pdf

No repository files were modified. The pre-existing uncommitted comment in `demo.py` remains untouched.

---

## 1. Concise architecture map

```
Task
  │
  ▼
BPlane.classify()
  ├─ task scope
  ├─ uncertainty
  └─ nominal level band
  │
  ▼
ReactivationPlanner
  ├─ semantic search(task)
  ├─ semantic search(scope)
  ├─ all active nodes in band
  ├─ rudimentary contradiction filtering
  └─ independent-node scoring
  │
  ▼
ActivationPacket
  ├─ context text
  ├─ planner/executor/evaluator AgentBias records
  ├─ constraints
  └─ selected KNode IDs
  │
  ▼
LangGraph workflow
  memory_controller → planner → executor ⇄ evaluator → memory_updater
                                                        │
                                                        ├─ reinforce/weaken selected nodes
                                                        ├─ form nodes from events
                                                        └─ consolidate
```

The orchestration is implemented as five LangGraph functions in one `MSKWorkflow`; it is not a collection of independently operating agents. Only the planner consumes most of the activation packet. [workflow.py (line 101)](/home/mic/Projects/msk/msk_v0/workflow.py:101), [workflow.py (line 154)](/home/mic/Projects/msk/msk_v0/workflow.py:154), [workflow.py (line 224)](/home/mic/Projects/msk/msk_v0/workflow.py:224)

The system’s durable path is:

```
KNode JSON + indexed scalar fields → SQLite
KNode text embedding             → Qdrant
```

SQLite is authoritative for reconstruction; Qdrant only returns IDs that are resolved back through SQLite. [storage.py (line 22)](/home/mic/Projects/msk/msk_v0/msk/storage.py:22), [storage.py (line 65)](/home/mic/Projects/msk/msk_v0/msk/storage.py:65), [storage.py (line 133)](/home/mic/Projects/msk/msk_v0/msk/storage.py:133)

---

## 2. What a KNode actually represents

A `KNode` is currently a **self-contained memory record combining four conceptually different things**:

- a claim or recollection;
- retrieval metadata;
- instructions for how it should affect agents;
- lifecycle/governance bookkeeping.

Its schema is in [models.py (line 43)](/home/mic/Projects/msk/msk_v0/msk/models.py:43).

### Content

`content.text` is the only part embedded and semantically searched. `structured` is an untyped dictionary, currently used primarily for `preferred_commands`. `artifact_refs` is represented but has no runtime consumer. [models.py (line 45)](/home/mic/Projects/msk/msk_v0/msk/models.py:45), [storage.py (line 65)](/home/mic/Projects/msk/msk_v0/msk/storage.py:65), [reactivation.py (line 159)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:159)

### Triggers

Triggers are weighted, typed entities such as keywords, task types, tools, and graph entities. In practice:

- keyword and task-type triggers do not trigger retrieval;
- trigger weights are never read;
- graph entities are never traversed;
- tool-name triggers can populate `enable_tools`, but the workflow does not consume `enable_tools`.

[models.py (line 51)](/home/mic/Projects/msk/msk_v0/msk/models.py:51), [formation.py (line 111)](/home/mic/Projects/msk/msk_v0/msk/formation.py:111), [reactivation.py (line 157)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:157)

### Activation

`KNodeActivation` is not transient activation state. It is a proposed **effect descriptor**: target agents, abstraction level, intensity, and mode. Of those:

- `level` filters retrieval;
- `mode` affects packet construction;
- `target_agents` routes bias records;
- `intensity` has no effect;
- the KNode’s own `level_band` has no effect.

There is no session-specific activation value, activation timestamp, propagation depth, accumulated energy, or activation trace. [models.py (line 89)](/home/mic/Projects/msk/msk_v0/msk/models.py:89), [reactivation.py (line 131)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:131)

### Relations

Relations are typed, weighted embedded edges with optional provenance. There is no graph store, referential integrity, inverse-edge maintenance, or general traversal. Only `contradicts` is consulted during retrieval. Edge weights and provenance are unused. [models.py (line 123)](/home/mic/Projects/msk/msk_v0/msk/models.py:123), [reactivation.py (line 85)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:85)

There is also a concrete mutation defect: properties such as `contradicts` and `specializes` return newly constructed lists of IDs. Calls such as `a.relations.contradicts.append(...)` therefore modify a temporary list, not `edges`. Contradiction and episode-to-strategy link updates silently disappear. [models.py (line 136)](/home/mic/Projects/msk/msk_v0/msk/models.py:136), [consolidation.py (line 103)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:103), [consolidation.py (line 147)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:147)

### Provenance and artifacts

LLM-formed nodes preserve source event IDs, creator, and confidence. Rule-formed nodes accept defaults and do not link to their generating events. Consolidated strategies put KNode IDs into `source_events`, even though that field otherwise denotes event IDs. Evidence and artifact references are not dereferenced or validated. [formation.py (line 120)](/home/mic/Projects/msk/msk_v0/msk/formation.py:120), [formation.py (line 156)](/home/mic/Projects/msk/msk_v0/msk/formation.py:156), [consolidation.py (line 208)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:208)

### Lifecycle and “active” state

`is_active()` means **eligible for retrieval**, not presently activated. Eligibility requires:

- not superseded;
- not expired;
- strength greater than `0.05`.

`record_use()` adds `0.05` on success or subtracts `0.15` on failure. [models.py (line 105)](/home/mic/Projects/msk/msk_v0/msk/models.py:105), [models.py (line 177)](/home/mic/Projects/msk/msk_v0/msk/models.py:177)

This distinction matters: persistent eligibility, historical utility, confidence, and momentary activation are currently conflated in nearby fields and terminology.

---

## 3. KNode lifecycle: creation to reactivation

### 1. Event capture

The workflow records a plan event and one event per tool execution. The original user request is not recorded as its own event. [workflow.py (line 275)](/home/mic/Projects/msk/msk_v0/workflow.py:275), [workflow.py (line 374)](/home/mic/Projects/msk/msk_v0/workflow.py:374)

### 2. Formation

At task completion, all events are passed to `FormationModule.extract()`:

- with Claude, an LLM generates typed KNode descriptions and activation metadata;
- without Claude, successful nontrivial shell commands become `tool_pattern` nodes and failures become `episode` nodes.

[workflow.py (line 504)](/home/mic/Projects/msk/msk_v0/workflow.py:504), [formation.py (line 191)](/home/mic/Projects/msk/msk_v0/msk/formation.py:191)

The advertised immediate/staged/discard modes exist only in the class documentation. The actual policy is a single LLM confidence cutoff of `0.4`; the rule path writes everything matching its rules immediately. [formation.py (line 65)](/home/mic/Projects/msk/msk_v0/msk/formation.py:65), [formation.py (line 106)](/home/mic/Projects/msk/msk_v0/msk/formation.py:106)

### 3. Storage

Saving embeds only `content.text`, serializes the complete node into SQLite, and duplicates level, type, strength, and active status into indexes and Qdrant payloads. [storage.py (line 42)](/home/mic/Projects/msk/msk_v0/msk/storage.py:42), [storage.py (line 65)](/home/mic/Projects/msk/msk_v0/msk/storage.py:65)

Deletion removes only the SQLite row, leaving the Qdrant point behind. It becomes an ignored ghost because search cannot resolve it back to a KNode. [storage.py (line 95)](/home/mic/Projects/msk/msk_v0/msk/storage.py:95), [storage.py (line 158)](/home/mic/Projects/msk/msk_v0/msk/storage.py:158)

### 4. Retrieval

The B-plane classifies the task. The reactivation planner unions:

- up to eight semantic matches for the task;
- up to four semantic matches for the textual scope label;
- every active node in the selected level band.

Because all in-band nodes are added, Qdrant generally influences candidate order and cost, not membership. The candidates are then re-embedded and rescored independently. [bplane.py (line 65)](/home/mic/Projects/msk/msk_v0/msk/bplane.py:65), [reactivation.py (line 60)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:60), [reactivation.py (line 97)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:97)

### 5. Packet construction

Every selected node becomes context regardless of mode or target. Modes additionally produce planner instructions, command preferences, constraints, or strategy bias. Policy nodes generate governance flags. [reactivation.py (line 131)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:131)

### 6. Behavioral influence

The planner reads context, constraints, and its own `AgentBias`. The executor does not read executor bias or tool enablement. The evaluator does not read evaluator checks. Governance flags are not consumed. [workflow.py (line 233)](/home/mic/Projects/msk/msk_v0/workflow.py:233), [workflow.py (line 351)](/home/mic/Projects/msk/msk_v0/workflow.py:351), [workflow.py (line 394)](/home/mic/Projects/msk/msk_v0/workflow.py:394)

### 7. Feedback and evolution

Every selected node is counted as used. Tool nodes are rewarded if a preferred command succeeded; otherwise they are penalized, including when the command was never attempted. Non-tool nodes receive the overall task outcome. New nodes are then formed and consolidation runs. [workflow.py (line 462)](/home/mic/Projects/msk/msk_v0/workflow.py:462)

This is selection-level credit assignment, not evidence that a memory causally affected behavior.

---

## 4. What currently works

- A rich, serializable KNode schema exists.
- SQLite/Qdrant hybrid storage and semantic retrieval are implemented in code.
- LLM and heuristic task classification exist.
- KNodes can create differentiated planner instructions, command preferences, context, and constraints.
- The workflow can reinforce or weaken previously selected memories.
- LLM and deterministic formation paths exist.
- Deduplication, abstraction, contradiction, and decay routines are present.
- The simulated environment demonstrates environmental change from `make` to `npm`.
- The evaluation harness measures success, step count, command choice, and KNode hits.

Relevant implementations: [reactivation.py (line 23)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:23), [workflow.py (line 187)](/home/mic/Projects/msk/msk_v0/workflow.py:187), [consolidation.py (line 45)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:45), [evaluate.py (line 46)](/home/mic/Projects/msk/msk_v0/evaluate.py:46)

There are, however, no automated test files. The environment also cannot currently import `KNodeStore` from the declared requirements because `qdrant-client` and `sentence-transformers` are imported but absent from `requirements.txt`; `rank-bm25` is listed but unused. [requirements.txt (line 1)](/home/mic/Projects/msk/msk_v0/requirements.txt:1), [storage.py (line 11)](/home/mic/Projects/msk/msk_v0/msk/storage.py:11)

---

## 5. Incomplete or disconnected mechanisms

|Mechanism|Present in representation|Behavioral status|
|---|---|---|
|Trigger weights|Yes|Never read|
|Keyword/task triggers|Yes|Not used to retrieve or score|
|Graph entities|Yes|Never queried|
|Relation weights/provenance|Yes|Never read|
|Supports/coactivation/generalization|Yes|No activation effect|
|Contradiction|Yes|Mutation is broken; filtering semantics are unsafe|
|Activation intensity|Yes|Never applied|
|Per-node level band|Yes|Never applied|
|AgentBias strength|Yes|Never applied|
|Executor/evaluator activation|Packet contains it|Consumers ignore it|
|Governance/access/approval|Yes|No enforcement|
|Artifact/evidence references|Yes|No resolution|
|Decay policy|Yes|Ignored; one hard-coded decay rule|
|Staged formation|Documented|Not implemented|
|Skill distillation|Mentioned|Stub only|
|Recursive activation|No runtime state|Not implemented|
|Dynamic reactivation after surprise|Described in paper|Controller runs only before planning|
|Meta-policy learning|Described|Not implemented|

---

## 6. Implicit design philosophy

The implementation implies several sound commitments:

1. **Memory should affect action, not just supply text.** Activation modes and per-agent biases make this explicit.
    
2. **Memory should be external, inspectable, and revisable.** Provenance, lifecycle state, relations, and JSON persistence favor auditability over hidden-state memory.
    
3. **Semantic similarity is necessary but insufficient.** The score combines similarity, strength, frequency, and failure history. [bplane.py (line 124)](/home/mic/Projects/msk/msk_v0/msk/bplane.py:124)
    
4. **Memory use should be task-dependent.** The B-plane chooses whether retrieval is worthwhile and nominally selects a level band.
    
5. **Memory is a lifecycle.** Formation, reactivation, feedback, consolidation, and decay are intentionally separate modules.
    

The less desirable implicit assumption is that this philosophy can be validated by adding paper-shaped metadata before establishing which metadata changes behavior. Much of the architecture is currently **schema-first and demo-first** rather than trace- or experiment-driven.

---

## 7. Architectural inconsistencies and unnecessary structure

### The score does not match its conceptual meaning

The paper’s score includes recency, graph relevance, provenance, risk, and obsolescence. The implementation uses semantic similarity, strength, use count, an always-constant in-band bonus, and failure ratio. The comment calls use count a “recency/frequency proxy,” but it contains no recency. Node confidence, task risk, graph relations, intensity, and provenance do not participate. [bplane.py (line 133)](/home/mic/Projects/msk/msk_v0/msk/bplane.py:133)

### Level selection is partly broken

When no LLM is present, `classify()` returns directly from `_classify_heuristic()` before applying `_SCOPE_RULES`. Consequently procedural, strategic, and high-risk classifications retain the model default `(1, 3)`. `abstraction_need` is computed but never used. [bplane.py (line 65)](/home/mic/Projects/msk/msk_v0/msk/bplane.py:65), [models.py (line 249)](/home/mic/Projects/msk/msk_v0/msk/models.py:249)

High-risk checks also occur after diagnostic and procedural keyword checks, so mixed tasks such as “delete the failing test” can be classified as diagnostic rather than high-risk. [bplane.py (line 103)](/home/mic/Projects/msk/msk_v0/msk/bplane.py:103)

### Contradiction is confused with supersession

`_resolve_conflicts()` treats every target of a contradiction edge as superseded. It does not compare recency, evidence, scope, or strength. With reciprocal contradiction edges, both nodes would be removed. Contradiction should normally create competition or contextual choice, not automatic deletion. [reactivation.py (line 85)](/home/mic/Projects/msk/msk_v0/msk/reactivation.py:85)

### Generalization links are inconsistent

A strategy correctly adds `specializes → episode` edges during construction, but episodes are then also intended to receive `specializes → strategy`, which reverses the expected relation and fails because of the temporary-list bug. The duplicate-prevention check looks at `episode.generalizes`, which is never populated. Strategies also default to activation level 2 and no target agents, so a generated “strategy” has episode-like activation behavior. [consolidation.py (line 127)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:127), [consolidation.py (line 208)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:208)

### Decay is non-incremental

Decay subtracts the entire time since `last_used_at` every time consolidation runs, without updating a decay checkpoint. Repeated consolidation therefore charges overlapping periods repeatedly. Nodes that have never been used never decay. [consolidation.py (line 230)](/home/mic/Projects/msk/msk_v0/msk/consolidation.py:230)

### Duplicated and over-flexible state

- `active`, `strength`, `level`, and type are duplicated between JSON, SQLite columns, and Qdrant payloads.
- `strength` conflates reliability, historical utility, retention, and eligibility.
- `structured: dict` and free-form trigger/relation strings weaken the benefits of the otherwise rigid enums.
- `AgentActivation` is unused, while `ActivationPacket` uses a hard-coded string dictionary. [models.py (line 209)](/home/mic/Projects/msk/msk_v0/msk/models.py:209)
- Eight KNode types exist, but runtime behavior only distinguishes `tool_pattern` and `policy`.

For this prototype, SQLite plus a vector column/index—or even SQLite plus an in-process embedding cache—would express the currently implemented behavior more simply.

---

## 8. The five most important architectural problems

1. **The experiment does not isolate or test reactivation.**  
    In deterministic mode, the fallback plan already contains both commands. Rule-formed KNodes have no target agents and default to context mode, while the fallback planner parses only backticked agent guidance, not memory context. The three evaluation conditions therefore largely execute the same policy. [formation.py (line 156)](/home/mic/Projects/msk/msk_v0/msk/formation.py:156), [workflow.py (line 313)](/home/mic/Projects/msk/msk_v0/workflow.py:313), [evaluate.py (line 179)](/home/mic/Projects/msk/msk_v0/evaluate.py:179)
    
2. **“Activation” is selection plus planner prompt injection.**  
    There is no transient activation state, propagation, accumulation, inhibition, recursive reactivation, or structured set formation. Most nominal target-agent effects are ignored.
    
3. **Feedback assigns credit to retrieval, not influence.**  
    Every selected node is updated, nonuse can count as failure, and overall task success rewards all selected non-tool memories. This will cause self-reinforcement, accidental punishment, and misleading utility estimates.
    
4. **The relation layer is both behaviorally disconnected and internally incorrect.**  
    Edge mutations fail, directionality is inconsistent, contradiction resolution is destructive, and weights/provenance are unused.
    
5. **Level control, governance, and meta-control are represented more strongly than they are implemented.**  
    A one-time, mostly lexical classifier selects a hard band; risk does not govern tools or writes; policy and meta-rule KNodes cannot alter activation policy.
    

---

## 9. The activation problem

### What follows naturally from the existing architecture

A bounded, session-scoped graph activation engine follows naturally. An unrestricted cognitive simulation does not.

The current architecture already provides:

- semantic seeds;
- typed triggers;
- weighted edges;
- strength and confidence;
- level metadata;
- target-agent effects;
- a B-plane that can supply task-specific policy.

Those are enough for a conservative propagation experiment.

### Proposed conceptual model

Keep **persistent KNode state** separate from a task’s **activation state**.

For each task, create an `ActivationSession` containing:

- seed score per node;
- current activation per node;
- reason/path by which it activated;
- propagation depth;
- positive and inhibitory contributions;
- selected effect projections;
- resource consumption.

Initial seeds should combine:

```
semantic relevance
+ exact typed-trigger matches
+ task/entity/tool matches
+ verified policy priority
× node reliability
```

Semantic similarity should seed the graph, not determine the final set alone.

Then iterate a bounded update conceptually like:

```
next(i) =
    seed(i)
  + persistence × current(i)
  + Σ positive typed-edge contributions
  - Σ contradiction/inhibitory contributions
  - competition/crowding penalty
```

Important controls:

- normalize outgoing contribution so high-degree nodes do not manufacture energy;
- attenuate every hop;
- use a lower retention threshold than entry threshold to avoid oscillation;
- cap propagation at one or two hops initially;
- impose node, edge, token, and wall-clock budgets;
- stop on convergence, empty frontier, or budget exhaustion;
- retain a complete explanation trace.

Relation semantics should be explicit:

- `supports`: positive evidence;
- `coactivates_with`: positive associative spread;
- `contradicts`: inhibitory competition, not deletion;
- `generalizes` and `specializes`: direction depends on requested abstraction;
- unknown relations: no propagation until a policy defines them.

Activation intensity should govern the effect applied to the S-plane, not substitute for relevance. Strength/confidence should gate trust. Momentary activation should not be persisted back into the KNode.

### Competition and termination

Competition is more important than biologically elaborate decay. Start with:

- one winner or a confidence-weighted mixture within contradiction sets;
- diversity penalties for near-duplicate nodes;
- maximum one or two nodes per effect category;
- a total packet/token budget;
- deterministic maximum depth.

This gives MSK coherent activation without allowing graph loops or hubs to dominate.

### Semantic similarity versus graph structure

Semantic retrieval should answer: **Where should activation begin?**

The graph should answer: **Which additional memories form a useful, mutually supported configuration?**

The controller should answer: **Which parts of that configuration may influence this task, at what force, and through which control surfaces?**

---

## 10. K-recursion

Meaningful K-recursion is not currently implemented.

Relations are not traversed, and newly formed memories do not know which existing memories were active. Formation receives task events but not the activation packet or evidence that a selected KNode influenced an action. Consolidation can generate a strategy from stored tool-pattern nodes, but that is offline clustering, not reactivation of KNodes by KNodes. [formation.py (line 191)](/home/mic/Projects/msk/msk_v0/msk/formation.py:191), [workflow.py (line 504)](/home/mic/Projects/msk/msk_v0/workflow.py:504)

A useful modern interpretation would be:

1. record selected, delivered, consulted, and action-producing KNode IDs separately;
2. let formation inspect current events plus the actually used active set;
3. create explicit `derived_from_k_nodes` provenance distinct from `source_events`;
4. connect new memories only to parents that demonstrably contributed;
5. require fresh event evidence so recursive memories cannot endlessly launder their own confidence;
6. allow bounded propagation through those composition links on later tasks.

This would implement the valuable part of Minsky’s recursion principle: new memories can be compositions of previously useful dispositions. The underlying level-band and K-recursion ideas are described in the primary K-lines paper. Cognitive Science - April 1980 - Minsky - K‐Lines A theory of Memory.pdf

---

## 11. Level control

The representation is sufficient for a crude experiment but insufficient for robust level control.

It has a scalar `level` and nominal generalization relations. It lacks:

- a reliable generalization hierarchy;
- scope or domain breadth;
- content specificity;
- authority/risk separated from abstraction;
- expected token cost;
- evidence-detail requirements;
- validated correspondence between type and level.

A single four-valued level currently conflates rawness, strategic generality, and governance authority.

A better model would separate:

- `abstraction_level`;
- `scope` or applicability;
- `authority/risk class`;
- hierarchy links;
- optional granularity/token cost.

The B-plane should select a target abstraction distribution, not merely a hard interval. Activation could prefer the target level while allowing adjacent nodes when supported by the graph. Coarse-to-fine expansion is particularly natural: begin with a strategy/frame, descend to episodes or evidence only when uncertainty or contradiction requires it.

The KNode’s own `activation.level_band` appears unnecessary unless it is redefined as an explicit applicability constraint.

---

## 12. Meta-control

The `BPlane` is the only current meta-control component, but it is a pre-task classifier and scorer rather than a full memory governor. Its `context` argument is unused; it is not called after surprising tool results; and it does not govern formation, access, approval, or decay. [bplane.py (line 56)](/home/mic/Projects/msk/msk_v0/msk/bplane.py:56), [workflow.py (line 187)](/home/mic/Projects/msk/msk_v0/workflow.py:187)

Activation policy should belong primarily to a **retrieval/activation engine under a higher-level controller**:

- KNodes declare evidence, applicability, and possible effects.
- The graph declares typed relationships.
- The activation engine implements propagation mechanics.
- The B-plane selects task-specific parameters, budgets, bands, and safety rules.
- Meta-rule KNodes may advise the B-plane, but should not grant themselves authority.
- Governance enforcement should sit above both memory content and the graph.

The B-plane should run at least at:

1. task entry;
2. uncertainty, failure, or environmental surprise;
3. pre-action for risky effects;
4. post-task for write and credit decisions.

---

## 13. Five interesting opportunities

1. **Coherent memory assemblies.**  
    One-hop typed propagation could transform isolated search hits into small sets containing a strategy, supporting episode, relevant command, and evaluator check.
    
2. **K-recursive compositional learning.**  
    Active-memory provenance could support new strategies assembled from earlier strategies and episodes rather than repeatedly summarizing raw text.
    
3. **Coarse-to-fine recall.**  
    Generalization links could let MSK begin at the right abstraction and descend only when evidence is needed.
    
4. **Causal memory learning.**  
    Attaching KNode IDs to generated plan steps, tool calls, and checks would allow reward only when a memory was actually used—and counterfactual testing of whether it helped.
    
5. **Task-adaptive activation policies.**  
    Different tasks could choose sparse command recall, evidence-heavy diagnosis, high-level planning, or governance-first activation using the same K-plane.
    

The most surprising opportunity is that KNodes may be better understood not as “memories with lots of metadata,” but as **interfaces between evidence and reusable control effects**. That suggests separating the remembered claim from the reactivation program.

---

## 14. Alternative designs

### A. Minimal effectful retrieval

Use one relational store, embeddings, and explicit effect records. Retrieve independently, rank, enforce a token/effect budget, and construct packets without graph propagation.

- Lowest complexity.
- Best baseline for determining whether planner/tool/evaluator configuration adds value beyond context.
- May be all MSK needs if propagation does not produce measurable gains.

### B. Typed weighted activation graph

Retain KNodes but add session-scoped activation, typed propagation, inhibition, level-aware traversal, and explanation traces.

- Closest evolution of the present model.
- Supports structured assemblies and K-recursion.
- Requires careful graph integrity and stability controls.

### C. Separate memory claims from reactivation programs

Represent three objects:

```
Claim/Episode ──evidence──► Source events/artifacts
      │
      └──supports──► Reactivation program
                         ├─ planner effect
                         ├─ tool policy
                         └─ evaluator criterion
```

A single fact could support several reusable effects, and one effect could be grounded in several memories.

- Avoids making every KNode simultaneously content, policy, state, and graph vertex.
- Makes provenance and governance much clearer.
- More structural change, but likely the cleanest long-term model.

---

## 15. Prioritized small experiments

1. **Validate the core claim with a non-confounded action test.**  
    Hold retrieved content constant and compare: no memory, context-only, and effectful packet. Remove hard-coded correct commands from the planner. Measure first-action correctness, steps, and success.
    
2. **Instrument consumption and credit.**  
    Track whether each KNode changed a plan step, tool call, or evaluator check. Compare selection-level reinforcement with consumption-level reinforcement.
    
3. **Test one-hop propagation on a tiny hand-authored graph.**  
    Include useful chains, hubs, distractors, and contradictions. Compare seed-only retrieval with bounded propagation on set precision, action success, and packet size.
    
4. **Test level control independently.**  
    Construct the same knowledge at raw, episodic, and strategic levels. Evaluate narrow, diagnostic, and planning tasks under fixed, hard-band, and coarse-to-fine policies.
    
5. **Test environmental change and inhibition.**  
    Model old and new commands with dates, evidence, and contradiction. Compare deletion, winner-take-all, and confidence-weighted inhibition.
    
6. **Test K-recursive formation.**  
    Form one strategy from three episodes while preserving parent provenance. Evaluate transfer to a held-out task and compare against replaying the episodes.
    
7. **Only then test adaptive meta-control.**  
    Compare a fixed activation policy, the present heuristic classifier, and a small learned or LLM-selected policy. The controller should be optimized only after the activation mechanics have an observable signal.
    

---

## Final assessment

MSK’s strongest existing idea is not graph memory, decay, or the KNode taxonomy. It is the explicit distinction between **remembered information** and **how that information should configure an agent**.

The current implementation demonstrates the data shape of that distinction, but not yet its full behavior. The next research milestone should therefore not be a larger schema or a graph database. It should be a small, controlled demonstration that a memory-derived configuration changes action more reliably than the same memory supplied as text. Once that result exists, spreading activation, K-recursion, level control, and learned meta-policy become experimentally meaningful rather than architectural decoration.