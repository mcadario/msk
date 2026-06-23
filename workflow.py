"""LangGraph S-plane workflow.

Five nodes: memory_controller → planner → executor → evaluator
            ↕                                           ↓
            └──────────────── memory_updater ←──────────┘

The mode parameter controls memory behaviour:
  "none"       — no memory, bare agent
  "repository" — top-k retrieval injected as plain context (baseline)
  "msk"        — full B-plane classification + activation packet (MSK)

The no_llm flag disables all Claude API calls and uses deterministic
fallbacks — useful for demos without an API key.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Optional

import anthropic
from anthropic.types import TextBlock
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from msk.bplane import BPlane
from msk.consolidation import ConsolidationModule
from msk.formation import FormationModule
from msk.models import ActivationPacket, Event
from msk.reactivation import ReactivationPlanner
from msk.storage import KNodeStore
from sim.environment import SimulatedRepository


# ------------------------------------------------------------------
# State schema
# ------------------------------------------------------------------

class MSKState(TypedDict):
    task: str
    task_id: str
    mode: str                        # "msk" | "repository" | "none"
    activation_packet: Optional[dict]
    plan: list[dict]
    current_step_idx: int
    execution_results: list[dict]
    events: list[dict]
    success: bool
    iterations: int
    max_iterations: int
    outcome: str
    memory_log: list[str]


# ------------------------------------------------------------------
# Prompts
# ------------------------------------------------------------------

PLANNER_PROMPT = """\
You are a debugging agent for a software repository.

Task: {task}

{memory_context}

Create a concrete step-by-step plan using shell commands to debug and resolve the issue.

{agent_guidance}

Return ONLY a JSON array (2–5 steps):
[
  {{"step": 1, "description": "brief description", "command": "shell command here", "expected": "expected outcome"}}
]"""

EVALUATOR_PROMPT = """\
Task: {task}

Execution results:
{results_text}

Did the integration tests run and pass?
Return ONLY JSON: {{"success": true/false, "outcome": "one sentence"}}"""

# ------------------------------------------------------------------
# Fallback plan used when no_llm=True or LLM call fails
# Tries both make and npm so it works on v1 and v2 repos
# ------------------------------------------------------------------

FALLBACK_PLAN = [
    {"step": 1, "description": "List files",     "command": "ls",                       "expected": "project files"},
    {"step": 2, "description": "Read README",    "command": "cat README.md",             "expected": "test instructions"},
    {"step": 3, "description": "Run tests (v1)", "command": "make test-integration",     "expected": "tests pass"},
    {"step": 4, "description": "Run tests (v2)", "command": "npm run test:integration",  "expected": "tests pass"},
]


# ------------------------------------------------------------------
# Workflow class
# ------------------------------------------------------------------

class MSKWorkflow:
    """Wraps the LangGraph S-plane and all MSK memory modules."""

    def __init__(
        self,
        client: Optional[anthropic.Anthropic],
        store: KNodeStore,
        env: SimulatedRepository,
        max_iterations: int = 6,
        no_llm: bool = False, #demo flag
    ):
        self.client = client
        self.store = store
        self.env = env
        self.max_iterations = max_iterations
        self.no_llm = no_llm

        # pass None to modules when no_llm=True so they use their fallbacks
        llm_client = None if no_llm else client
        self.bplane = BPlane(llm_client)
        self.formation = FormationModule(llm_client)
        self.reactivation = ReactivationPlanner(store, self.bplane)
        self.consolidation = ConsolidationModule(store, llm_client)

        self.app = self._build_graph() #this is the stategraph COMPILED

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, task: str, mode: str = "msk") -> dict:
        """Run a task through the S-plane and return the final state."""
        state: MSKState = {
            "task": task,
            "task_id": str(uuid.uuid4())[:8],
            "mode": mode,
            "activation_packet": None,
            "plan": [],
            "current_step_idx": 0,
            "execution_results": [],
            "events": [],
            "success": False,
            "iterations": 0,
            "max_iterations": self.max_iterations,
            "outcome": "",
            "memory_log": [],
        }
        return self.app.invoke(state)

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        g = StateGraph(MSKState)
        g.add_node("memory_controller", self._memory_controller)
        g.add_node("planner",           self._planner)
        g.add_node("executor",          self._executor)
        g.add_node("evaluator",         self._evaluator)
        g.add_node("memory_updater",    self._memory_updater)

        g.set_entry_point("memory_controller")
        g.add_edge("memory_controller", "planner")
        g.add_edge("planner",           "executor")
        g.add_edge("executor",          "evaluator")
        g.add_conditional_edges(
            "evaluator",
            self._route,
            {"executor": "executor", "memory_updater": "memory_updater"},
        )
        g.add_edge("memory_updater", END)
        return g.compile()

    def _route(self, state: MSKState) -> str:
        if state["success"]:
            return "memory_updater"
        if state["iterations"] >= state["max_iterations"]:
            return "memory_updater"
        if state["current_step_idx"] >= len(state["plan"]):
            return "memory_updater"
        return "executor"

    # ------------------------------------------------------------------
    # Node: memory_controller  (B-plane)
    # ------------------------------------------------------------------

    def _memory_controller(self, state: MSKState) -> MSKState:
        mode    = state["mode"]
        task    = state["task"]
        task_id = state["task_id"]
        log     = list(state["memory_log"])

        if mode == "none":
            log.append("B-plane [none]  no memory retrieval")
            return {**state, "activation_packet": None, "memory_log": log}

        if mode == "repository":
            packet = self.reactivation.retrieve_repository_style(task, task_id)
            log.append(
                f"B-plane [repo]  {len(packet.context_items)} context items injected"
            )
            return {**state, "activation_packet": packet.model_dump(), "memory_log": log}

        # ── MSK mode ──────────────────────────────────────────────────
        # classify() uses heuristic fallback automatically when client is None (no_llm = True)
        cls = self.bplane.classify(task)
        log.append(
            f"B-plane [msk]   scope={cls.scope}  "
            f"band={cls.level_band}  uncertainty={cls.uncertainty:.2f}"
            + (" [heuristic]" if self.no_llm else "")
        )
        packet = self.reactivation.reactivate(task, task_id, cls)
        n = len(packet.selected_k_node_ids)
        log.append(
            f"B-plane [msk]   reactivated {n} K-node(s)  "
            + (f"→ {len(packet.context_items)} context items" if packet.context_items else "→ no prior memory")
        )
        return {**state, "activation_packet": packet.model_dump(), "memory_log": log}

    # ------------------------------------------------------------------
    # Node: planner
    # ------------------------------------------------------------------

    def _planner(self, state: MSKState) -> MSKState:
        task     = state["task"]
        mode     = state["mode"]
        pkt_dict = state.get("activation_packet")
        log      = list(state["memory_log"])

        memory_context = ""
        agent_guidance = ""

        if pkt_dict:
            packet = ActivationPacket.model_validate(pkt_dict)

            if packet.context_items:
                memory_context = (
                    "Past experience:\n"
                    + "\n".join(f"  · {c}" for c in packet.context_items)
                )

            # MSK adds agent-specific guidance on top of context
            if mode == "msk":
                planner_bias = packet.for_agent("planner")
                if planner_bias:
                    lines: list[str] = []
                    if planner_bias.bias:
                        lines.append(f"Strategy: {planner_bias.bias}")
                    lines.extend(planner_bias.instructions)
                    if planner_bias.preferred_commands:
                        cmds = "  ".join(f"`{c}`" for c in planner_bias.preferred_commands)
                        lines.append(f"Use these commands if applicable: {cmds}")
                    if lines:
                        agent_guidance = (
                            "Instructions from memory system:\n"
                            + "\n".join(f"  · {l}" for l in lines)
                        )
                if packet.constraints:
                    agent_guidance += "\nConstraints:\n" + "\n".join(
                        f"  · {c}" for c in packet.constraints
                    )

        # ── no_llm: use fallback plan, inject memory context as description ──
        if self.no_llm:
            plan = self._fallback_plan(memory_context, agent_guidance)
            log.append(f"Planner [no_llm]: {len(plan)} steps (deterministic fallback)")
        else:
            plan = self._llm_plan(task, memory_context, agent_guidance, log)

        log.append(
            f"Planner: {len(plan)} steps — "
            + " → ".join(f"`{s.get('command','?')}`" for s in plan)
        )

        event = Event(
            task_id=state["task_id"], actor="agent",
            content=f"Plan: {[s.get('command','') for s in plan]}", outcome="success",
        )
        return {
            **state,
            "plan": plan,
            "current_step_idx": 0,
            "events": list(state["events"]) + [event.model_dump()],
            "memory_log": log,
        }

    def _llm_plan(
        self, task: str, memory_context: str, agent_guidance: str, log: list[str]
    ) -> list[dict]:
        prompt = PLANNER_PROMPT.format(
            task=task,
            memory_context=memory_context,
            agent_guidance=agent_guidance,
        )
        try:
            assert self.client is not None
            msg = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            block = msg.content[0]
            if not isinstance(block, TextBlock):
                raise ValueError(f"Unexpected block type: {type(block)}")
            raw = block.text.strip()
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            log.append(f"Planner: LLM error ({e}), using fallback plan")
            return self._fallback_plan(memory_context, agent_guidance)

    def _fallback_plan(self, memory_context: str, agent_guidance: str) -> list[dict]:
        """
        Deterministic plan that works for both v1 and v2 repos.
        If memory context contains preferred commands, put them first.
        """
        preferred: list[str] = []

        # extract preferred commands from agent_guidance if present
        for line in agent_guidance.splitlines():
            if "`" in line:
                cmds = re.findall(r"`([^`]+)`", line)
                preferred.extend(cmds)

        plan: list[dict] = [
            {"step": 1, "description": "List files",  "command": "ls",           "expected": "project files"},
            {"step": 2, "description": "Read README", "command": "cat README.md", "expected": "test instructions"},
        ]

        step = 3
        # preferred commands from memory go first
        for cmd in preferred:
            plan.append({"step": step, "description": f"Run (from memory): {cmd}", "command": cmd, "expected": "tests pass"})
            step += 1

        # always try both as fallback
        if "make test-integration" not in preferred:
            plan.append({"step": step, "description": "Try make", "command": "make test-integration", "expected": "tests pass"})
            step += 1
        if "npm run test:integration" not in preferred:
            plan.append({"step": step, "description": "Try npm",  "command": "npm run test:integration", "expected": "tests pass"})
            step += 1

        return plan

    # ------------------------------------------------------------------
    # Node: executor
    # ------------------------------------------------------------------

    def _executor(self, state: MSKState) -> MSKState:
        plan = state["plan"]
        idx  = state["current_step_idx"]
        log  = list(state["memory_log"])

        if idx >= len(plan):
            return {**state, "iterations": state["iterations"] + 1}

        step    = plan[idx]
        command = step.get("command", "")
        result  = self.env.execute(command)

        status = "✓" if result["success"] else "✗"
        log.append(f"Executor [{status}] `{command}`  rc={result['returncode']}")

        exec_entry = {
            "step":        idx + 1,
            "command":     command,
            "description": step.get("description", ""),
            "stdout":      result["stdout"],
            "returncode":  result["returncode"],
            "success":     result["success"],
        }
        event = Event(
            task_id=state["task_id"], actor="tool",
            content=f"exec: {command}",
            tool_name="shell", tool_input=command,
            tool_output=result["stdout"][:400],
            outcome="success" if result["success"] else "failure",
        )

        return {
            **state,
            "execution_results": list(state["execution_results"]) + [exec_entry],
            "events":            list(state["events"]) + [event.model_dump()],
            "current_step_idx":  idx + 1,
            "iterations":        state["iterations"] + 1,
            "memory_log":        log,
        }

    # ------------------------------------------------------------------
    # Node: evaluator
    # ------------------------------------------------------------------
    def _evaluator(self, state: MSKState) -> MSKState:
        results = state["execution_results"]
        task    = state["task"]
        log     = list(state["memory_log"])

        if not results:
            return {**state, "success": False, "outcome": "no steps executed"}

        test_keywords = ("test-integration", "test:integration", "pytest", "jest", "spec")

        # scan ALL results for a successful test command
        successful_test = next(
            (r for r in results
            if r["success"] and any(kw in r["command"].lower() for kw in test_keywords)),
            None,
        )

        if successful_test:
            log.append(f"Evaluator: ✓ task succeeded via `{successful_test['command']}`")
            return {
                **state,
                "success": True,
                "outcome": successful_test["stdout"][:100],
                "memory_log": log,
            }

        # no successful test command found yet
        if self.no_llm:
            log.append("Evaluator [no_llm]: · no test success yet, continuing")
            return {**state, "success": False, "outcome": "", "memory_log": log}

        # LLM evaluation for ambiguous outcomes
        last         = results[-1]
        results_text = "\n".join(
            f"  Step {r['step']}: `{r['command']}`  rc={r['returncode']}\n"
            f"  {r['stdout'][:200]}"
            for r in results
        )
        try:
            assert self.client is not None
            msg = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=128,
                messages=[{"role": "user", "content": EVALUATOR_PROMPT.format(
                    task=task, results_text=results_text
                )}],
            )
            block = msg.content[0]
            if not isinstance(block, TextBlock):
                raise ValueError(f"Unexpected block type: {type(block)}")
            raw     = block.text.strip()
            raw     = re.sub(r"^```[a-z]*\n?", "", raw)
            raw     = re.sub(r"\n?```$", "", raw)
            data    = json.loads(raw)
            success = bool(data.get("success", False))
            outcome = data.get("outcome", "")
        except Exception:
            success = last["success"]
            outcome = last["stdout"][:80]

        label = "✓ success" if success else "· continuing"
        log.append(f"Evaluator: {label} — {outcome[:70]}")
        return {**state, "success": success, "outcome": outcome, "memory_log": log}

    # ------------------------------------------------------------------
    # Node: memory_updater
    # ------------------------------------------------------------------

    def _memory_updater(self, state: MSKState) -> MSKState:
        log      = list(state["memory_log"])
        events   = [Event.model_validate(e) for e in state["events"]]
        success  = state["success"]
        task_id  = state["task_id"]
        pkt_dict = state.get("activation_packet")

        # 1. Update strength of every K-node that was reactivated
        if pkt_dict:
            packet       = ActivationPacket.model_validate(pkt_dict)
            strengthened = 0
            weakened     = 0

            for nid in packet.selected_k_node_ids:
                node = self.store.get(nid)
                if node is None:
                    continue

                # check if this specific node's preferred commands succeeded
                preferred = node.content.structured.get("preferred_commands", [])
                if preferred:
                    cmd_succeeded = any(
                        r["success"] and any(cmd in r["command"] for cmd in preferred)
                        for r in state["execution_results"]
                    )
                else:
                    # non-tool nodes: use overall task success
                    cmd_succeeded = success

                node.record_use(cmd_succeeded)
                self.store.update(node)

                if cmd_succeeded:
                    strengthened += 1
                else:
                    weakened += 1

            if strengthened:
                log.append(f"Memory updater: strengthened {strengthened} K-node(s)")
            if weakened:
                log.append(f"Memory updater: weakened {weakened} K-node(s)")

        # 2. Form new K-nodes from this task's events
        new_nodes = self.formation.extract(events, task_id)
        for node in new_nodes:
            self.store.save(node)
        if new_nodes:
            log.append(f"Memory updater: formed {len(new_nodes)} new K-node(s)")
            for n in new_nodes:
                log.append(f"  + [{n.type.value}] \"{n.content.text[:75]}\"")

        # 3. Consolidation pass
        stats      = self.consolidation.run()
        active_ops = {k: v for k, v in stats.items() if v > 0}
        if active_ops:
            log.append(f"Memory updater: consolidation → {active_ops}")

        log.append(
            f"Memory updater: K-plane now has "
            f"{self.store.stats()['active']} active K-node(s)"
        )
        return {**state, "memory_log": log}