"""Reactivation planner — multi-channel K-node search → ActivationPacket.

Implements the MSK_REACTIVATE pseudocode from Section 6.2.3.
"""
 
from .bplane import BPlane
from .models import ActivationMode, ActivationPacket, AgentBias, KNode, TaskClassification
from .storage import KNodeStore
from sentence_transformers import util


class ReactivationPlanner:
    """
    Given a task and working context, queries the K-plane across multiple
    channels, applies level-band filtering and scoring, and builds an
    ActivationPacket that configures the S-plane agents.
    """

    def __init__(self, store: KNodeStore, bplane: BPlane):
        self.store = store
        self.bplane = bplane

    def reactivate(
        self,
        task: str,
        task_id: str,
        classification: TaskClassification,
        top_k: int = 6,
    ) -> ActivationPacket:
        """Full MSK reactivation: classify → search → filter → score → packet."""

        if not self.bplane.should_retrieve_memory(classification):
            return ActivationPacket(task_id=task_id, level_band=classification.level_band)

        # Multi-channel candidate collection
        candidates = self._collect_candidates(task, classification)

        # Remove expired / unauthorized
        candidates = [c for c in candidates if c.is_active()]

        # Resolve contradictions: if a node is superseded, skip it
        candidates = self._resolve_conflicts(candidates)

        # Apply level-band filter
        lo, hi = classification.level_band
        candidates = [
            c for c in candidates if lo <= c.activation.level <= hi
        ]

        # Score and rank
        scored = self._score_candidates(candidates, task, classification)
        selected = scored[:top_k]

        return self._build_packet(selected, task_id, classification)

    # ------------------------------------------------------------------
    # Retrieval channels
    # ------------------------------------------------------------------

    def _collect_candidates(
        self, task: str, classification: TaskClassification
    ) -> list[KNode]:
        seen: set[str] = set()
        results: list[KNode] = []

        def add(nodes: list[KNode]) -> None:
            for n in nodes:
                if n.id not in seen:
                    seen.add(n.id)
                    results.append(n)

        # Semantic with qdrant
        add(self.store.search(task, top_k=8, level_band=classification.level_band))

        # Task-type specific search
        add(self.store.search(
            classification.scope, top_k=4, level_band=classification.level_band
        ))

        # All active nodes in band (for small stores this is fine)
        add(self.store.by_level_band(*classification.level_band))

        return results

    def _resolve_conflicts(self, candidates: list[KNode]) -> list[KNode]:
        superseded: set[str] = set()
        for node in candidates:
            if node.relations.contradicts:
                for cid in node.relations.contradicts:
                    superseded.add(cid)
        return [c for c in candidates if c.id not in superseded]

    # ------------------------------------------------------------------
    # Scoring (Equation 2 from paper, Section 6.1.1)
    # ------------------------------------------------------------------

    def _score_candidates(
        self,
        candidates: list[KNode],
        task: str,
        classification: TaskClassification,
    ) -> list[KNode]:
        if not candidates:
            return []

        task_embedding = self.store._embed(task)

        scored: list[tuple[float, KNode]] = []
        for node in candidates:
            # semantic similarity via sentence-transformers
            node_embedding = self.store._embed(node.content.text)
            sim = float(util.cos_sim(task_embedding, node_embedding))

            score = self.bplane.compute_activation_score(
                node_strength=node.lifecycle.strength,
                sim_score=sim,          
                node_level=node.activation.level,
                level_band=classification.level_band,
                node_use_count=node.lifecycle.use_count,
                node_failure_count=node.lifecycle.failure_count,
            )
            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored if _ > 0]

    # ------------------------------------------------------------------
    # Packet construction
    # ------------------------------------------------------------------

    def _build_packet(  #activation packet
        self,
        selected: list[KNode],
        task_id: str,
        classification: TaskClassification,
    ) -> ActivationPacket:
        context_items: list[str] = []
        constraints: list[str] = []
        agent_biases: dict[str, AgentBias] = {
            "planner": AgentBias(),
            "executor": AgentBias(),
            "evaluator": AgentBias(),
        }
        governance_flags: list[str] = []

        for node in selected:
            # Add to context regardless of mode
            context_items.append(node.content.text)

            # Per-mode configuration of agent biases
            mode = node.activation.mode
            for agent_name in node.activation.target_agents:
                if agent_name not in agent_biases:
                    agent_biases[agent_name] = AgentBias()
                bias = agent_biases[agent_name]

                if mode == ActivationMode.instruction:
                    bias.instructions.append(node.content.text)
                elif mode == ActivationMode.tool_bias:
                    cmds = node.content.structured.get("preferred_commands", [])
                    bias.preferred_commands.extend(cmds)
                    bias.enable_tools.extend(node.triggers.tool_names)
                    bias.instructions.append(f"Prefer: {node.content.text}")
                elif mode == ActivationMode.plan_bias:
                    bias.bias = node.content.text
                elif mode == ActivationMode.constraint:
                    constraints.append(node.content.text)
                else:  # context
                    pass  # content_items covers it

                # Always give evaluator the checks from tool_patterns
                if node.type.value == "tool_pattern" and agent_name != "evaluator":
                    agent_biases["evaluator"].checks.append(
                        f"Verify: {node.content.text}"
                    )

            if node.type.value == "policy":
                governance_flags.append(node.content.text)

        return ActivationPacket(
            task_id=task_id,
            selected_k_node_ids=[n.id for n in selected],
            agent_activations=agent_biases,
            context_items=list(dict.fromkeys(context_items)),  # deduplicate
            constraints=constraints,
            level_band=classification.level_band,
            governance_flags=governance_flags,
        )

    # ------------------------------------------------------------------
    # Repository-style retrieval (comparison baseline)
    # ------------------------------------------------------------------

    def retrieve_repository_style(self, task: str, task_id: str, top_k: int = 5) -> ActivationPacket:
        """Top-k qdrant retrieval with context injection only — no agent configuration."""
        nodes = self.store.search(task, top_k=top_k)
        context_items = [n.content.text for n in nodes if n.is_active()]
        return ActivationPacket(
            task_id=task_id,
            selected_k_node_ids=[n.id for n in nodes],
            context_items=context_items,
        )
