"""MSK v0 demo — the running example from the paper.

Phases:
  1. Learning   — agent runs task on v1 repo; K-nodes are formed
  2. Reuse      — same task; K-nodes reactivated, plan pre-configured
  3. Migration  — repo switches to npm; K-node fails and is superseded
  4. Recovery   — updated K-node guides the next run correctly
"""
from __future__ import annotations

import os
import sys

import anthropic
from dotenv import load_dotenv
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

load_dotenv()

from msk.storage import KNodeStore
from sim.environment import SimulatedRepository
from workflow import MSKWorkflow

console = Console()

TASK = "The integration tests are failing. Debug and fix the issue so tests pass."


def _print_memory_log(log: list[str]) -> None:
    for line in log:
        prefix = "  [dim]│[/dim] "
        if "✓" in line:
            rprint(f"  [green]│[/green] {line}")
        elif "✗" in line or "error" in line.lower():
            rprint(f"  [red]│[/red] {line}")
        elif "B-plane" in line:
            rprint(f"  [cyan]│[/cyan] {line}")
        elif "Memory updater" in line or "formed" in line or "strengthened" in line or "weakened" in line:
            rprint(f"  [yellow]│[/yellow] {line}")
        else:
            rprint(f"{prefix}{line}")


def _print_result(state: dict, phase: str) -> None:
    success = state["success"]
    outcome = state["outcome"]
    results = state["execution_results"]

    color = "green" if success else "red"
    label = "SUCCESS" if success else "FAILED"
    rprint(f"\n  [{color}]◉ {label}[/{color}] — {outcome[:90]}")

    if results:
        t = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
        t.add_column("Step", style="dim", width=4)
        t.add_column("Command", width=36)
        t.add_column("RC", width=4)
        t.add_column("Output snippet", width=50)
        for r in results:
            rc_style = "green" if r["returncode"] == 0 else "red"
            t.add_row(
                str(r["step"]),
                r["command"],
                f"[{rc_style}]{r['returncode']}[/{rc_style}]",
                r["stdout"][:60].replace("\n", " "),
            )
        console.print(t)


def run_phase(wf: MSKWorkflow, phase_num: int, title: str, description: str) -> dict:
    console.print(Rule(f"[bold]Phase {phase_num}: {title}[/bold]", style="blue"))
    rprint(f"\n  [dim]{description}[/dim]")
    rprint(f"  [bold]Task:[/bold] {TASK}\n")

    state = wf.run(TASK, mode="msk")

    rprint("  [bold dim]Memory log:[/bold dim]")
    _print_memory_log(state["memory_log"])
    _print_result(state, title)
    return state


def show_kplane(store: KNodeStore) -> None:
    nodes = store.all_active()
    if not nodes:
        rprint("  [dim](K-plane empty)[/dim]")
        return
    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    t.add_column("Type",     width=14)
    t.add_column("Content",  width=60)
    t.add_column("Strength", width=9)
    t.add_column("Uses",     width=5)
    for n in nodes:
        t.add_row(
            n.type.value,
            n.content.text[:58],
            f"{n.lifecycle.strength:.2f}",
            str(n.lifecycle.use_count),
        )
    console.print(t)


def main() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        rprint("[red]Error: ANTHROPIC_API_KEY not set. Add it to .env or export it.[/red]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    store  = KNodeStore(":memory:")     # persistent: pass a file path instead
    env    = SimulatedRepository(version=1)

    wf = MSKWorkflow(client, store, env)

    console.print(Panel.fit(
        "[bold]MSK v0 — Memory as Reactivation Demo[/bold]\n"
        "[dim]Paper: 'MSK: K-S System for Multi-Agent Architectures'[/dim]",
        border_style="cyan",
    ))

    # ── Phase 1: First run — no prior memory ──────────────────────────
    run_phase(
        wf, 1, "Learning",
        "First run. No K-nodes exist. Agent discovers the test command.\n"
        "  Formation module extracts K-nodes from the task events.",
    )
    rprint("\n  [bold dim]K-plane after phase 1:[/bold dim]")
    show_kplane(store)

    # ── Phase 2: Second run — K-nodes reactivated ─────────────────────
    console.print()
    run_phase(
        wf, 2, "Reactivation",
        "Same task, same repo. K-nodes from phase 1 are now reactivated.\n"
        "  Planner receives tool_bias instructions; plan should be more direct.",
    )
    rprint("\n  [bold dim]K-plane after phase 2:[/bold dim]")
    show_kplane(store)

    # ── Phase 3: Repo migration — K-node becomes wrong ────────────────
    console.print()
    rprint(Rule("[bold]Repository Migration[/bold]", style="yellow"))
    env.migrate_to_v2()
    rprint("  [yellow]⚠ Repository migrated: make test-integration → npm run test:integration[/yellow]\n")

    run_phase(
        wf, 3, "Failure + Update",
        "K-node for 'make test-integration' is reactivated but the command now fails.\n"
        "  Memory updater weakens the old K-node and forms a new one for npm.",
    )
    rprint("\n  [bold dim]K-plane after phase 3:[/bold dim]")
    show_kplane(store)

    # ── Phase 4: Updated K-node guides recovery ───────────────────────
    console.print()
    run_phase(
        wf, 4, "Recovery",
        "New npm K-node is now active. Agent should use npm run test:integration\n"
        "  without trial-and-error.",
    )
    rprint("\n  [bold dim]K-plane after phase 4:[/bold dim]")
    show_kplane(store)

    console.print(Rule("[bold green]Demo complete[/bold green]", style="green"))


if __name__ == "__main__":
    main()
