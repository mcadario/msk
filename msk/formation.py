"""Formation module — extracts K-nodes from task events using Claude."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
from anthropic.types import TextBlock

from .models import (
    ActivationMode,
    Event,
    KNode,
    KNodeType,
)

_FORMATION_PROMPT = """You are te formation module of the MSK memory architecture.
Analyze these events from a software debugging task and extract memorable K-nodes.

Events:
{events_text}

Extract K-nodes that represent:
1. Tool patterns: commands or tool sequences that worked or failed
2. Strategies: reasoning approaches that were effective
3. Episodes: specific failure/success patterns worth remembering
4. Facts: stable facts about the environment, repo, or user preferences

For each K-node return:
- type: tool_pattern | strategy | episode | fact | skill | frame | meta_rule
- content_text: concise description of what to remember
- keywords: 3-6 keywords for retrieval
- task_types: which task types this helps (debug | procedural | diagnostic | etc.)
- tool_names: tools involved (shell, editor, etc.)
- target_agents: which agents benefit (planner | executor | evaluator)
- level: 1=raw trace, 2=episode/fact, 3=strategy/skill, 4=governance
- mode: context | instruction | tool_bias | plan_bias | constraint
- intensity: 0.0-1.0
- confidence: 0.0-1.0
- preferred_commands: specific commands to use (if tool_pattern)

Return ONLY a JSON array. Example:
[
  {{
    "type": "tool_pattern",
    "content_text": "This repository uses npm run test:integration for integration tests.",
    "keywords": ["integration", "test", "npm", "repository"],
    "task_types": ["diagnostic", "procedural"],
    "tool_names": ["shell"],
    "target_agents": ["planner", "executor", "evaluator"],
    "level": 2,
    "mode": "tool_bias",
    "intensity": 0.85,
    "confidence": 0.9,
    "preferred_commands": ["npm run test:integration"]
  }}
]

If nothing is worth remembering, return [].
Be selective — only extract memories that would genuinely help future tasks."""


class FormationModule:
    """
    task events -->  candidate K-nodes
    three write modes:
      - immediate: high confidence
      - staged: inferred facts (need confirmation)
      - discard: low-value
    """

    def __init__(self, client: Optional[anthropic.Anthropic]):
        self.client = client


    def _call_llm(self, events_text: str) -> list[dict]:
        prompt = _FORMATION_PROMPT.format(events_text=events_text)

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(
            block.text
            for block in response.content
            if isinstance(block, TextBlock)
        ).strip()

        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        return json.loads(raw)
    
    def _build_k_node(
        self, raw: dict, events: list[Event], task_id: str
    ) -> KNode | None:
        try:
            ktype = KNodeType(raw.get("type", "episode")) # "episode" is the generico type
        except ValueError:
            ktype = KNodeType.episode

        confidence = float(raw.get("confidence", 0.7))
        # discard very low-confidence inferences
        if confidence < 0.4:
            return None

        # build triggers using the graph-based structure
        triggers = KNode.KNodeTriggers()
        for kw in raw.get("keywords", []):
            triggers.add(kw, "keyword")
        for tt in raw.get("task_types", []):
            triggers.add(tt, "task_type")
        for tn in raw.get("tool_names", []):
            triggers.add(tn, "tool")

        return KNode(
            id=str(uuid.uuid4()),
            type=ktype,
            content=KNode.KNodeContent(
                text=raw.get("content_text", ""),
                structured={"preferred_commands": raw.get("preferred_commands", [])},
            ),
            triggers=triggers,
            activation=KNode.KNodeActivation(
                target_agents=raw.get("target_agents", ["planner"]),
                level=int(raw.get("level", 2)),
                level_band=(1, 4),
                intensity=float(raw.get("intensity", 0.7)),
                mode=self._parse_mode(raw.get("mode", "context")),
            ),
            provenance=KNode.KNodeProvenance(
                source_events=[e.id for e in events],
                created_at=datetime.now(timezone.utc),
                created_by="formation_module",
                confidence=confidence,
            ),
            lifecycle=KNode.KNodeLifecycle(
                strength=confidence * 0.8,
                use_count=0,
                success_count=0,
                failure_count=0,
            ),
            governance=KNode.KNodeGovernance(
                privacy_label="internal",  # type: ignore[arg-type]
            ),
            relations=KNode.KNodeRelations(),
        )
    
    TRIVIAL_COMMANDS = {"ls", "ls -la", "pwd", "cat README.md", "cat readme.md"}
    
    #rule-base: doesn't use anthropic apis (demo scenario)
    def _extract_rule_based(self, events: list[Event]) -> list[KNode]:
        nodes = []
        for event in events:
            if event.tool_input and event.tool_input.strip() in self.TRIVIAL_COMMANDS:
                continue
            if event.outcome == "success" and event.tool_name == "shell":
                # successful command → tool_pattern K-node
                node = KNode(
                    type=KNodeType.tool_pattern,
                    content=KNode.KNodeContent(
                        text=f"For this repository, use: {event.tool_input}",
                        structured={"preferred_commands": [event.tool_input]},
                    ),
                    lifecycle=KNode.KNodeLifecycle(strength=0.7),
                )
                triggers = KNode.KNodeTriggers()
                for word in (event.tool_input or "").split():
                    if len(word) > 3:
                        triggers.add(word.lower(), "keyword")
                node.triggers = triggers
                nodes.append(node)

            elif event.outcome == "failure" and event.tool_name == "shell":
                # failed command → episode K-node warning
                node = KNode(
                    type=KNodeType.episode,
                    content=KNode.KNodeContent(
                        text=f"Command failed: {event.tool_input}. Output: {(event.tool_output or '')[:100]}",
                    ),
                    lifecycle=KNode.KNodeLifecycle(strength=0.5),
                )
                nodes.append(node)

        return nodes

    def extract(self, events: list[Event], task_id: str) -> list[KNode]:
        """extract K-nodes from a list of events"""
        if not events:
            return []
        if self.client is None: # fallback to rule-based extraction
            return self._extract_rule_based(events)

        events_text = self._format_events(events)
        try:
            raw_nodes = self._call_llm(events_text)
        except Exception as e:
            print(f"[Formation] LLM extraction failed: {e}")
            return []

        k_nodes: list[KNode] = []
        for raw in raw_nodes:
            node = self._build_k_node(raw, events, task_id)
            if node is not None:
                k_nodes.append(node)
        return k_nodes

    def _format_events(self, events: list[Event]) -> str:
        lines: list[str] = []
        for e in events:
            line = f"[{e.actor}] {e.content}"
            if e.tool_name:
                line += f" \n - tool={e.tool_name}"
            if e.tool_input:
                line += f"\n - input={e.tool_input}"
            if e.tool_output:
                line += f"\n - output={e.tool_output[:200]}"
            line += f"\n - outcome={e.outcome}"
            lines.append(line)
        return "\n".join(lines)


    def _parse_mode(self, mode_str: str) -> ActivationMode:
        try:
            return ActivationMode(mode_str)
        except ValueError:
            return ActivationMode.context