"""
Here i implement the following:
.Knode
.AgentBias
.Event
.TaskClassification
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class KNodeType(str, Enum):
    fact = "fact"
    episode = "episode"
    strategy = "strategy"
    skill = "skill"
    frame = "frame"
    tool_pattern = "tool_pattern"
    policy = "policy"
    meta_rule = "meta_rule"


class ActivationMode(str, Enum):
    context = "context"
    instruction = "instruction"
    tool_bias = "tool_bias"
    plan_bias = "plan_bias"
    constraint = "constraint"


class PrivacyLabel(str, Enum):
    public = "public"
    internal = "internal"
    personal = "personal"
    sensitive = "sensitive"


class KNode(BaseModel):

    class KNodeContent(BaseModel):
        text: str
        structured: dict = Field(default_factory=dict)
        artifact_refs: list[str] = Field(default_factory=list)


    class KNodeTriggers(BaseModel):
        """
        graph-based structure
        """

        class KNodeTrigger(BaseModel):
            entity_id: str
            entity_type: str   # keyword, task_type, agent, ...
            weight: float = 1.0

        triggers: list[KNodeTrigger] = Field(default_factory=list)

        def of_type(self, entity_type: str) -> list[str]: #filter by entity_type
            return [t.entity_id for t in self.triggers if t.entity_type == entity_type]

        def add(self, entity_id: str, entity_type: str, weight: float = 1.0) -> None:
            self.triggers.append(
                self.KNodeTrigger(entity_id=entity_id, entity_type=entity_type, weight=weight)
            )

        #attributes but better as they are actually functions
        @property
        def keywords(self) -> list[str]:
            return self.of_type("keyword")

        @property
        def task_types(self) -> list[str]:
            return self.of_type("task_type")

        @property
        def tool_names(self) -> list[str]:
            return self.of_type("tool")

        @property
        def graph_entities(self) -> list[str]:
            return self.of_type("graph_entity")


    class KNodeActivation(BaseModel):
        target_agents: list[str] = Field(default_factory=list)
        level: int = 2          # 1=raw, 2=episode, 3=strategy, 4=governance
        level_band: tuple[int, int] = (1, 3)
        intensity: float = 0.7
        mode: ActivationMode = ActivationMode.context


    class KNodeProvenance(BaseModel):
        source_events: list[str] = Field(default_factory=list)
        created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
        created_by: str = "agent"
        confidence: float = 0.8
        evidence_refs: list[str] = Field(default_factory=list)


    class KNodeLifecycle(BaseModel):
        strength: float = 0.7
        last_used_at: Optional[datetime] = None
        use_count: int = 0
        success_count: int = 0
        failure_count: int = 0
        decay_policy: str = "time_and_use"
        expires_at: Optional[datetime] = None
        superseded_by: Optional[str] = None


    class KNodeGovernance(BaseModel):
        privacy_label: PrivacyLabel = PrivacyLabel.internal
        access_scope: list[str] = Field(default_factory=list)
        human_approval_required: bool = False
        deletion_policy: str = "on_request"


    class KNodeRelations(BaseModel):
        """
        graph-based structure, KNodeTriggers-like
        """

        class KNodeEdge(BaseModel):
            target_id: str
            relation: str      # supports, contradicts, generalizes, ...
            weight: float = 1.0 #default unweighted
            provenance: str = ""

        edges: list[KNodeEdge] = Field(default_factory=list)

        def of_type(self, relation: str) -> list[str]:
            return [e.target_id for e in self.edges if e.relation == relation]

        def add(self, target_id: str, relation: str, weight: float = 1.0, provenance: str = "") -> None:
            self.edges.append(
                self.KNodeEdge(target_id=target_id, relation=relation,
                               weight=weight, provenance=provenance)
            )

        @property
        def supports(self) -> list[str]:
            return self.of_type("supports")

        @property
        def contradicts(self) -> list[str]:
            return self.of_type("contradicts")

        @property
        def specializes(self) -> list[str]:
            return self.of_type("specializes")

        @property
        def generalizes(self) -> list[str]:
            return self.of_type("generalizes")

        @property
        def coactivates_with(self) -> list[str]:
            return self.of_type("coactivates_with")


    """ KNODE ATTRIBUTES """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: KNodeType
    content: KNodeContent
    triggers: KNodeTriggers = Field(default_factory=KNodeTriggers)
    activation: KNodeActivation = Field(default_factory=KNodeActivation)
    provenance: KNodeProvenance = Field(default_factory=KNodeProvenance)
    lifecycle: KNodeLifecycle = Field(default_factory=KNodeLifecycle)
    governance: KNodeGovernance = Field(default_factory=KNodeGovernance)
    relations: KNodeRelations = Field(default_factory=KNodeRelations)

    def is_active(self) -> bool:
        if self.lifecycle.superseded_by is not None:
            return False
        if self.lifecycle.expires_at and datetime.now(timezone.utc) > self.lifecycle.expires_at:
            return False
        return self.lifecycle.strength > 0.05

    def record_use(self, success: bool) -> None:
        self.lifecycle.use_count += 1
        self.lifecycle.last_used_at = datetime.now(timezone.utc)
        if success:
            self.lifecycle.success_count += 1
            self.lifecycle.strength = min(1.0, self.lifecycle.strength + 0.05)
        else:
            self.lifecycle.failure_count += 1
            self.lifecycle.strength = max(0.0, self.lifecycle.strength - 0.15)


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str = ""
    task_id: str = ""
    actor: str = "agent"
    content: str = ""
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    tool_output: Optional[str] = None
    outcome: str = "unknown"
    feedback: Optional[str] = None


class AgentBias(BaseModel):
    instructions: list[str] = Field(default_factory=list)
    enable_tools: list[str] = Field(default_factory=list)
    preferred_commands: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    bias: Optional[str] = None
    strength: float = 0.7


class AgentActivation(BaseModel):
    """
    agent - bias pair
    agent_id is a graph reference ( not a hardcoded string key).
    """
    agent_id: str
    bias: AgentBias


class ActivationPacket(BaseModel):
    task_id: str
    selected_k_node_ids: list[str] = Field(default_factory=list)
    agent_activations: dict[str, AgentBias] = Field(default_factory=dict)#eg. {"planner":AgentBias(),"executor":...}
    context_items: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    level_band: tuple[int, int] = (1, 4)
    governance_flags: list[str] = Field(default_factory=list)


    def for_agent(self, agent_id: str) -> Optional[AgentBias]:
        return self.agent_activations.get(agent_id)

    def render(self) -> str:
        parts: list[str] = []
        if self.context_items:
            parts.append("Memory context:\n" + "\n".join(f"- {c}" for c in self.context_items))
        if self.constraints:
            parts.append("Constraints:\n" + "\n".join(f"- {c}" for c in self.constraints))
        return "\n\n".join(parts)


class TaskClassification(BaseModel):
    scope: str = "diagnostic"
    uncertainty: float = 0.5
    risk: float = 0.2
    abstraction_need: int = 2
    level_band: tuple[int, int] = (1, 3)
    reasoning: str = ""