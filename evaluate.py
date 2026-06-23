"""MSK v0 evaluation — three-condition comparison.

Conditions:
  none       — no long-term memory
  repository — top-k context injection (retrieval baseline)
  msk        — full B-plane + activation packet

Tasks run against a v1 repository (make test-integration works).
After 3 tasks, the repo migrates to v2 (npm) and 3 more tasks run.
We measure: success rate, steps-to-solution, and correct command rate.
"""
 
import os
import sys
import time
from typing import Optional

import anthropic
from dotenv import load_dotenv
from rich import print as rprint
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

load_dotenv()

from msk.storage import KNodeStore
from sim.environment import SimulatedRepository
from workflow import MSKWorkflow

console = Console()

TASKS = [
    "The CI pipeline is failing because integration tests aren't passing. Fix it.",
    "Integration tests are broken after the last merge. Debug and resolve.",
    "Running the test suite fails. Investigate and make the tests pass.",
]

TASK_V2 = [
    "Integration tests fail after the dependency upgrade. Fix them.",
    "The test suite is broken. Find out why and make it pass.",
    "CI is red. Integration tests are failing. Get them green.",
]


def run_condition(
    mode: str,
    tasks_v1: list[str],
    tasks_v2: list[str],
    client: Optional[anthropic.Anthropic],
    no_llm = False
) -> dict:
    """Run all tasks for one condition and collect metrics."""
    store = KNodeStore(":memory:")
    env   = SimulatedRepository(version=1)
    wf    = MSKWorkflow(client, store, env, max_iterations=6, no_llm=no_llm)

    records: list[dict] = []

    for i, task in enumerate(tasks_v1):
        t0 = time.time()
        state = wf.run(task, mode=mode)
        elapsed = time.time() - t0
        records.append(_record(state, "v1", i + 1, elapsed))

    env.migrate_to_v2()

    for i, task in enumerate(tasks_v2):
        t0 = time.time()
        state = wf.run(task, mode=mode)
        elapsed = time.time() - t0
        records.append(_record(state, "v2", len(tasks_v1) + i + 1, elapsed))

    return {"mode": mode, "records": records}


def _record(state: dict, repo_ver: str, run_num: int, elapsed: float) -> dict:
    results  = state["execution_results"]
    commands = [r["command"] for r in results]

    # Did agent use the correct command for the repo version?
    v1_cmd = "make test-integration"
    v2_cmd = "npm run test:integration"
    if repo_ver == "v1":
        correct_cmd = any(v1_cmd in c for c in commands)
    else:
        correct_cmd = any(v2_cmd in c for c in commands)

    k_hits = 0
    pkt = state.get("activation_packet")
    if pkt:
        k_hits = len(pkt.get("selected_k_node_ids", []))

    return {
        "run":         run_num,
        "repo":        repo_ver,
        "success":     state["success"],
        "steps":       len(results),
        "correct_cmd": correct_cmd,
        "k_hits":      k_hits,
        "elapsed":     elapsed,
    }


def _summary(records: list[dict]) -> dict:
    total   = len(records)
    v1      = [r for r in records if r["repo"] == "v1"]
    v2      = [r for r in records if r["repo"] == "v2"]

    def pct(lst: list[dict], key: str) -> float:
        return 100 * sum(1 for r in lst if r[key]) / len(lst) if lst else 0

    return {
        "success_v1":     pct(v1, "success"),
        "success_v2":     pct(v2, "success"),
        "success_total":  pct(records, "success"),
        "correct_cmd_v1": pct(v1, "correct_cmd"),
        "correct_cmd_v2": pct(v2, "correct_cmd"),
        "avg_steps":      sum(r["steps"] for r in records) / total,
        "avg_k_hits":     sum(r["k_hits"] for r in records) / total,
        "avg_time":       sum(r["elapsed"] for r in records) / total,
    }


def print_detail(result: dict) -> None:
    mode    = result["mode"]
    records = result["records"]
    rprint(f"\n  [bold]{mode.upper()}[/bold] — per-run detail")
    t = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
    t.add_column("Run",       width=4)
    t.add_column("Repo",      width=4)
    t.add_column("Success",   width=8)
    t.add_column("Steps",     width=6)
    t.add_column("Cmd✓",      width=6)
    t.add_column("K-hits",    width=7)
    t.add_column("Time(s)",   width=8)
    for r in records:
        t.add_row(
            str(r["run"]),
            r["repo"],
            "[green]✓[/green]" if r["success"] else "[red]✗[/red]",
            str(r["steps"]),
            "[green]✓[/green]" if r["correct_cmd"] else "[red]✗[/red]",
            str(r["k_hits"]),
            f"{r['elapsed']:.1f}",
        )
    console.print(t)


def print_summary_table(results: list[dict]) -> None:
    console.print(Rule("[bold]Summary[/bold]", style="cyan"))
    t = Table(show_header=True, header_style="bold", padding=(0, 2))
    t.add_column("Mode",           width=12)
    t.add_column("Success (v1)",   width=13)
    t.add_column("Success (v2)",   width=13)
    t.add_column("Cmd accuracy v2",width=16)
    t.add_column("Avg steps",      width=10)
    t.add_column("Avg K-hits",     width=11)

    for res in results:
        s    = _summary(res["records"])
        mode = res["mode"]
        t.add_row(
            f"[bold]{mode}[/bold]",
            f"{s['success_v1']:.0f}%",
            f"{s['success_v2']:.0f}%",
            f"{s['correct_cmd_v2']:.0f}%",
            f"{s['avg_steps']:.1f}",
            f"{s['avg_k_hits']:.1f}",
        )

    console.print(t)
    rprint(
        "\n  [dim]Cmd accuracy v2: % of runs where agent used `npm run test:integration`[/dim]"
        "\n  [dim]K-hits: avg K-nodes reactivated per task (0 for none/repo in no-memory phase)[/dim]"
    )


def main() -> None:
    # client is optional — remove the hard exit if no API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client  = anthropic.Anthropic(api_key=api_key) if api_key else None
    no_llm  = client is None

    if no_llm:
        rprint("[yellow]No ANTHROPIC_API_KEY found — running in no_llm mode.[/yellow]")

    console.print(Rule("[bold]MSK v0 — Three-Condition Evaluation[/bold]", style="cyan"))
    rprint(
        f"\n  Tasks v1 (make works):   {len(TASKS)}\n"
        f"  Tasks v2 (npm required): {len(TASK_V2)}\n"
        f"  Conditions: none · repository · msk\n"
        f"  LLM: {'disabled (no_llm)' if no_llm else 'enabled'}\n"
    )

    results: list[dict] = []
    for mode in ("none", "repository", "msk"):
        console.print(Rule(f"[bold]Condition: {mode}[/bold]", style="dim"))
        rprint(f"  Running {len(TASKS) + len(TASK_V2)} tasks...")
        res = run_condition(mode, TASKS, TASK_V2, client, no_llm=no_llm)
        results.append(res)
        print_detail(res)

    print_summary_table(results)
    console.print(Rule("[bold green]Evaluation complete[/bold green]", style="green"))


if __name__ == "__main__":
    main()
