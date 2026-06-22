"""Consolidation module organises the K-plane after formation.

six consolidation operations:
  1. Deduplication
  2. Contradiction detection
  3. Abstraction
  4. Graph linking
  5. Skill distillation  (stub for v0)
  6. Decay and forgetting
"""

import string
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
from anthropic.types import TextBlock


from .models import (
    KNode,
    KNodeType,
)
from .storage import KNodeStore


def _bag(text: str) -> set[str]:
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return set(text.split())


def _jaccard(a: str, b: str) -> float: #jaccard score
    sa, sb = _bag(a), _bag(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


SIMILARITY_THRESHOLD = 0.65
DECAY_RATE = 0.02          # strength lost per day of non-use
MIN_EPISODES_FOR_ABSTRACTION = 3


class ConsolidationModule:

    def __init__(self, store: KNodeStore, client: Optional[anthropic.Anthropic]):
        self.store = store
        self.client = client

    def run(self) -> dict:
        """Run all consolidation operations. Returns a summary dict."""
        stats: dict[str, int] = {
            "deduplicated": 0,
            "contradictions_flagged": 0,
            "abstractions_created": 0,
            "nodes_decayed": 0,
        }
        nodes = self.store.all_active()

        stats["deduplicated"] = self._deduplicate(nodes)
        stats["contradictions_flagged"] = self._detect_contradictions(nodes)
        stats["abstractions_created"] = self._abstract_episodes()
        stats["nodes_decayed"] = self._decay(nodes)

        return stats

    # ------------------------------------------------------------------
    # 1. Deduplication (ordinary maintenance)
    # ------------------------------------------------------------------

    def _deduplicate(self, nodes: list[KNode]) -> int:
        merged = 0
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                if a.type != b.type:
                    continue
                sim = _jaccard(a.content.text, b.content.text)
                if sim >= SIMILARITY_THRESHOLD:
                    # Keep the stronger node; merge use counts into it
                    if a.lifecycle.strength >= b.lifecycle.strength:
                        survivor, duplicate = a, b
                    else:
                        survivor, duplicate = b, a
                    survivor.lifecycle.use_count += duplicate.lifecycle.use_count
                    survivor.lifecycle.success_count += duplicate.lifecycle.success_count
                    survivor.lifecycle.failure_count += duplicate.lifecycle.failure_count
                    survivor.lifecycle.strength = min(
                        1.0, survivor.lifecycle.strength + 0.05
                    )
                    # Mark duplicate as superseded
                    duplicate.lifecycle.superseded_by = survivor.id
                    duplicate.lifecycle.strength = 0.0
                    self.store.update(survivor)
                    self.store.update(duplicate)
                    merged += 1
        return merged

    # ------------------------------------------------------------------
    # 2. Contradiction detection
    # ------------------------------------------------------------------

    def _detect_contradictions(self, nodes: list[KNode]) -> int:
        """Flag pairs of tool_pattern nodes with the same keywords but different commands."""
        flagged = 0
        tool_patterns = [n for n in nodes if n.type == KNodeType.tool_pattern]
        for i, a in enumerate(tool_patterns):
            for b in tool_patterns[i + 1:]:
                # Same keywords overlap but different commands
                kw_overlap = set(a.triggers.keywords) & set(b.triggers.keywords)
                a_cmds = set(a.content.structured.get("preferred_commands", []))
                b_cmds = set(b.content.structured.get("preferred_commands", []))
                if kw_overlap and a_cmds and b_cmds and not (a_cmds & b_cmds):
                    # They share context but suggest different tools → potential contradiction
                    if b.id not in a.relations.contradicts:
                        a.relations.contradicts.append(b.id)
                        b.relations.contradicts.append(a.id)
                        self.store.update(a)
                        self.store.update(b)
                        flagged += 1
        return flagged

    # ------------------------------------------------------------------
    # 3. Abstraction: episodes → strategy
    # ------------------------------------------------------------------

    def _abstract_episodes(self) -> int:
        """When ≥ MIN_EPISODES_FOR_ABSTRACTION tool_pattern episodes share keywords,
        generate a strategy K-node summarising them (LLM-assisted if available)."""
        created = 0
        episodes = self.store.by_type(KNodeType.tool_pattern)
        if len(episodes) < MIN_EPISODES_FOR_ABSTRACTION:
            return 0

        # Group by keyword overlap
        clusters = self._cluster_by_keywords(episodes)
        for cluster in clusters:
            if len(cluster) < MIN_EPISODES_FOR_ABSTRACTION:
                continue
            # Check if a strategy already covers this cluster
            existing_ids = set()
            for n in cluster:
                existing_ids.update(n.relations.generalizes)
            if existing_ids:
                continue

            strategy = self._build_strategy_node(cluster)
            if strategy:
                self.store.save(strategy)
                # Link episodes to strategy
                for ep in cluster:
                    ep.relations.specializes.append(strategy.id)
                    self.store.update(ep)
                created += 1
        return created

    def _cluster_by_keywords(self, nodes: list[KNode]) -> list[list[KNode]]:
        """Simple greedy clustering by keyword set intersection."""
        clusters: list[list[KNode]] = []
        assigned: set[str] = set()
        for node in nodes:
            if node.id in assigned:
                continue
            cluster = [node]
            assigned.add(node.id)
            for other in nodes:
                if other.id in assigned:
                    continue
                overlap = set(node.triggers.keywords) & set(other.triggers.keywords)
                if len(overlap) >= 2:
                    cluster.append(other)
                    assigned.add(other.id)
            if len(cluster) >= 2:
                clusters.append(cluster)
        return clusters

    def _build_strategy_node(self, episodes: list[KNode]) -> KNode | None:
        if self.client:
            return self._build_strategy_with_llm(episodes)
        # Fallback: simple concatenation summary
        summary = "General pattern: " + "; ".join(
            e.content.text[:60] for e in episodes[:3]
        )
        return self._make_strategy_node(summary, episodes)

    def _build_strategy_with_llm(self, episodes: list[KNode]) -> KNode | None:
        texts = "\n".join(f"- {e.content.text}" for e in episodes)
        prompt = (
            "Summarise these observations into one general strategy (1-2 sentences):\n"
            + texts
        )
        try:
            msg = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=128,
                messages=[{"role": "user", "content": prompt}],
            )
            block = msg.content[0]

            if not isinstance(block, TextBlock):
                raise ValueError(f"Expected TextBlock, got {type(block)}")
            
            summary = block.text.strip()
            return self._make_strategy_node(summary, episodes)
        except Exception:
            return None

    def _make_strategy_node(self, summary: str, episodes: list[KNode]) -> KNode:
        relations = KNode.KNodeRelations()
        for ep in episodes:
            relations.add(ep.id, "specializes")

        return KNode(
            id=str(uuid.uuid4()),
            type=KNodeType.strategy,
            content=KNode.KNodeContent(text=summary),
            lifecycle=KNode.KNodeLifecycle(strength=0.6),
            provenance=KNode.KNodeProvenance(
                source_events=[ep.id for ep in episodes],
                created_by="consolidation_abstraction",
                confidence=0.7,
            ),
            relations=relations,
        )

    # ------------------------------------------------------------------
    # 6. Decay and forgetting
    # ------------------------------------------------------------------

    def _decay(self, nodes: list[KNode]) -> int:
        decayed = 0
        now = datetime.now(timezone.utc)
        for node in nodes:
            if node.lifecycle.last_used_at is None:
                continue
            days_unused = (now - node.lifecycle.last_used_at).total_seconds() / 86400
            if days_unused > 1:
                loss = DECAY_RATE * days_unused
                node.lifecycle.strength = max(0.0, node.lifecycle.strength - loss)
                if node.lifecycle.strength < 0.05:
                    node.lifecycle.superseded_by = "decayed"
                self.store.update(node)
                decayed += 1
        return decayed
