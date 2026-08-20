## KNode (models.py)

the core memory unit. nested classes inside KNode — access as KNode.KNodeContent etc.

### KNodeContent
```python
text: str                    # main retrieval surface, embedded by qdrant
structured: dict             # arbitrary. formation puts preferred_commands here
artifact_refs: list[str]     # unused in v0
```
**gotcha**: `preferred_commands` lives in `content.structured["preferred_commands"]` not as a field. memory_updater reads it with `.get("preferred_commands", [])`. if formation doesnt populate this, per-node strengthening falls back to overall task success.

### KNodeTriggers (graph-based)
```python
# internal edge
KNodeTrigger(entity_id: str, entity_type: str, weight: float = 1.0)

triggers: list[KNodeTrigger]

# methods
.add(entity_id, entity_type, weight=1.0)
.of_type(entity_type) -> list[str]

# @property backwards compat
.keywords   → .of_type("keyword")
.task_types → .of_type("task_type")
.tool_names → .of_type("tool")
.graph_entities → .of_type("graph_entity")
```
**formation.py uses .add() correctly. consolidation.py may not. check.**

### KNodeActivation
```python
target_agents: list[str]     # ["planner", "executor", "evaluator"]
level: int                   # 1=raw, 2=episode/fact, 3=strategy/skill, 4=governance
level_band: tuple[int,int]   # stored but B-plane overrides at reactivation time
intensity: float             # 0-1, used in AgentBias.strength
mode: ActivationMode         # context|instruction|tool_bias|plan_bias|constraint
```
**mode determines how reactivation planner routes the knode content into the activation packet. tool_bias → preferred_commands + enable_tools. instruction → bias.instructions. plan_bias → bias.bias field. constraint → packet.constraints. context → just packet.context_items.**

### KNodeProvenance
```python
source_events: list[str]     # event IDs, not task_id directly
created_at: datetime         # timezone-aware UTC
created_by: str              # "formation_module" | "formation_rule_based" | "consolidation_abstraction"
confidence: float            # 0-1, used as initial strength multiplier (strength = confidence * 0.8)
evidence_refs: list[str]     # unused in v0
```

### KNodeLifecycle
```python
strength: float              # 0-1, the main activation weight
last_used_at: Optional[datetime]  # updated by record_use()
use_count: int
success_count: int
failure_count: int
decay_policy: str            # "time_and_use" — only value used, consolidation reads this
expires_at: Optional[datetime]    # None = no expiry
superseded_by: Optional[str]      # knode id or "decayed" sentinel
```
**is_active() returns False if superseded_by is not None OR strength < 0.05 OR expired.**
**record_use(success=True) → strength += 0.05, capped at 1.0**
**record_use(success=False) → strength -= 0.15, floored at 0.0**

### KNodeRelations (graph-based)
```python
KNodeEdge(target_id: str, relation: str, weight: float=1.0, provenance: str="")
edges: list[KNodeEdge]

.add(target_id, relation, weight=1.0, provenance="")
.of_type(relation) -> list[str]

# @property backwards compat
.supports, .contradicts, .specializes, .generalizes, .coactivates_with
```
**IMPORTANT: consolidation.py still uses old syntax in two places. these will crash.**
```python
# BROKEN in consolidation.py:
a.relations.contradicts.append(b.id)           # contradicts is a @property returning list copy
KNodeRelations(specializes=[ep.id for ep in episodes])  # no such kwarg

# CORRECT:
a.relations.add(b.id, "contradicts")
relations = KNode.KNodeRelations()
for ep in episodes: relations.add(ep.id, "specializes")
```

### KNodeGovernance
```python
privacy_label: PrivacyLabel  # public|internal|personal|sensitive
access_scope: list[str]      # unused in v0
human_approval_required: bool  # unused in v0, hook for future
deletion_policy: str         # "on_request" — unused
```
**governance fields exist for the paper's claims about safety/privacy. none are enforced in v0.**

## Event (models.py)

```python
id: str                      # uuid, auto-generated
timestamp: datetime          # timezone-aware UTC
session_id: str = ""         # NOT auto-generated, left empty intentionally
task_id: str = ""            # set by workflow nodes from state["task_id"]
actor: str                   # "agent"|"tool"|"user"|"human_reviewer"|"environment"
content: str                 # human-readable description
tool_name: Optional[str]     # "shell" in v0
tool_input: Optional[str]    # the command string
tool_output: Optional[str]   # truncated to 400 chars in executor
outcome: str                 # "success"|"failure"|"partial"|"unknown"
feedback: Optional[str]      # unused in v0
```
**session_id is intentionally empty. traceability goes event.id → knode.provenance.source_events. task is traceable via event.task_id.**

## ActivationPacket (models.py)

```python
task_id: str
selected_k_node_ids: list[str]   # used by memory_updater to find nodes to update
agent_activations: dict[str, AgentBias]  # key = agent name string
context_items: list[str]         # deduplicated, all activated knode texts
constraints: list[str]           # from mode=constraint knodes
level_band: tuple[int,int]       # what B-plane selected
governance_flags: list[str]      # from type=policy knodes, unused in v0

.for_agent(agent_id) -> Optional[AgentBias]   # dict.get() wrapper
.render() -> str                 # context_items + constraints as prompt string
```

## AgentBias (models.py)

```python
instructions: list[str]          # added to planner prompt as bullet points
enable_tools: list[str]          # tool names to prioritize (conceptual, not enforced)
preferred_commands: list[str]    # injected into _fallback_plan via backtick extraction
checks: list[str]                # evaluator verification criteria (conceptual)
bias: Optional[str]              # high-level strategy string for planner
strength: float = 0.7            # used to set instruction weight in prompt
```
**enable_tools and checks are populated but not mechanically enforced in v0. they appear in the activation packet and in prompts but the executor doesnt filter tools and the evaluator doesnt run the checks programmatically. these are LLM-facing hints only.**

## TaskClassification (models.py)

```python
scope: str        # "narrow_factual"|"procedural"|"diagnostic"|"strategic"|"high_risk"
uncertainty: float  # 0-1, controls whether memory retrieval happens at all
risk: float       # 0-1, used for governance flag logic (not enforced)
abstraction_need: int  # 1-4, maps to level_band
level_band: tuple[int,int]  # computed by BPlane from scope
reasoning: str    # LLM explanation, for logging only
```
**BPlane.should_retrieve_memory() returns True if uncertainty >= 0.3. so if classify() returns uncertainty < 0.3 the whole reactivation is skipped.**

## KNodeType enum values

fact, episode, strategy, skill, frame, tool_pattern, policy, meta_rule

formation.py creates: tool_pattern (success), episode (failure)
consolidation creates: strategy (abstraction from episodes)
seed_demo_knowledge creates: tool_pattern

## ActivationMode enum values
context → knode text goes to context_items only  
instruction → knode text goes to agent_activations[x].instructions  
tool_bias → preferred_commands + enable_tools + instructions  
plan_bias → agent_activations[x].bias field  
constraint → packet.constraints list