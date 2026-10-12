"""Mutant-RL command-line interface with Rich-rendered telemetry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import mutant_rl
from mutant_rl.pipeline import MutantPipeline
from mutant_rl.sanitizer.quarantine import LeakQuarantineManager
from mutant_rl.schemas.environment import FileNode
from mutant_rl.schemas.trajectory import PolicyTrajectory

app = typer.Typer(
    name="mutant-rl",
    help="Sim-to-Real Calibrated Synthetic Environment Generator & Evaluator for SWE-RL.",
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print the current Mutant-RL release version."""
    v = mutant_rl.__version__
    console.print(f"[bold green]Mutant-RL[/bold green] version [cyan]{v}[/cyan]")


@app.command()
def generate(
    repo_path: Annotated[
        Path, typer.Argument(help="Path to repository or code sample directory.")
    ],
    repo_name: Annotated[
        str, typer.Option("--name", "-n", help="Repository identifier.")
    ] = "sample/repo",
    output_file: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Output path for generated instance JSON."),
    ] = None,
) -> None:
    """Procedurally synthesizes calibrated compound environments and decoupled oracles."""
    console.print(f"[bold cyan]Scanning repository components at:[/bold cyan] {repo_path}")

    files: dict[str, FileNode] = {}
    if repo_path.is_dir():
        for p in repo_path.rglob("*"):
            if p.is_file() and not p.name.startswith((".", "__")):
                try:
                    rel_p = str(p.relative_to(repo_path))
                    content = p.read_text(encoding="utf-8", errors="replace")
                    files[rel_p] = FileNode(path=rel_p, content=content)
                except Exception:
                    pass
    elif repo_path.is_file():
        content = repo_path.read_text(encoding="utf-8", errors="replace")
        files[repo_path.name] = FileNode(path=repo_path.name, content=content)

    if len(files) < 2:
        console.print(
            "[yellow]Warning: At least 2 files required to avoid 1-line bug shape.[/yellow]"
        )
        files["config.yaml"] = FileNode(
            path="config.yaml",
            content="pipeline:\n  batch_size: 32\n  timeout: 60\n",
        )

    pipeline = MutantPipeline()
    instance, audit, topology = pipeline.synthesize_calibrated_instance(repo_name, files)

    if not instance:
        console.print("[red]Failed to synthesize valid compound mutation preserving syntax.[/red]")
        raise typer.Exit(code=1)

    table = Table(title="Synthesized Environment Instance", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Instance ID", instance.instance_id)
    table.add_row("Spans Multi-File", str(topology.spans_multi_file))
    table.add_row("Code / Config Ratio", f"{topology.config_code_ratio:.2f}")
    table.add_row("Diff Leak Status", audit.quarantine_action if audit else "clean")
    table.add_row("Files Mutated", str(len(instance.files)))

    console.print(table)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(instance.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[green]Saved instance to:[/green] {output_file}")


@app.command()
def audit_leak(
    statement_file: Annotated[
        Path, typer.Option("--statement", "-s", help="Path to problem statement text file.")
    ],
    patch_file: Annotated[
        Path, typer.Option("--patch", "-p", help="Path to ground-truth patch diff file.")
    ],
) -> None:
    """Audits a problem statement for generator diff text leakage."""
    statement = statement_file.read_text(encoding="utf-8")
    patch = patch_file.read_text(encoding="utf-8")

    manager = LeakQuarantineManager()
    report = manager.audit_and_quarantine("cli_audit", statement, patch)

    color = "green" if not report.is_compromised else "red"
    action_str = report.quarantine_action.upper()
    console.print(
        Panel(
            f"[bold {color}]Quarantine Decision: {action_str}[/bold {color}]\n"
            f"N-Gram Overlap Score: {report.fingerprint.n_gram_overlap_score:.2%}\n"
            f"Token Jaccard Score: {report.fingerprint.token_jaccard_score:.2%}\n"
            f"Symbol Leaks: {report.fingerprint.symbol_leak_count}\n"
            f"Line Number Leaks: {report.fingerprint.line_number_leak_count}\n"
            f"Patch Reconstruction Risk: {report.fingerprint.patch_reconstruction_risk:.2%}",
            title="Diff Fingerprint Leak Audit",
            border_style=color,
        )
    )

    if report.is_compromised:
        raise typer.Exit(code=1)


@app.command()
def audit_sim_to_real(
    synth_trajectories_file: Annotated[
        Path, typer.Option("--synth", help="Path to JSON file of synthetic rollouts.")
    ],
    real_trajectories_file: Annotated[
        Path, typer.Option("--real", help="Path to JSON file of real PR rollouts.")
    ],
) -> None:
    """Computes Sim-to-Real gap, action divergence, and checks stopping signal."""
    synth_data = json.loads(synth_trajectories_file.read_text(encoding="utf-8"))
    real_data = json.loads(real_trajectories_file.read_text(encoding="utf-8"))

    synth_trajs = [PolicyTrajectory.model_validate(item) for item in synth_data]
    real_trajs = [PolicyTrajectory.model_validate(item) for item in real_data]

    pipeline = MutantPipeline()
    metrics = pipeline.audit_trajectories(synth_trajs, real_trajs)

    status_color = "green" if metrics.calibration_status == "healthy_calibrated" else "red"

    table = Table(title="Sim-to-Real Divergence Audit", border_style="cyan")
    table.add_column("Telemetry Metric", style="bold white")
    table.add_column("Observation", style="yellow")
    table.add_column("Status / Boundary", style=status_color)

    table.add_row(
        "Synthetic Resolve Rate",
        f"{metrics.synthetic_resolve_rate:.2%}",
        f"Volume: {metrics.synthetic_volume_count}",
    )
    table.add_row(
        "Real PR Resolve Rate",
        f"{metrics.real_pr_resolve_rate:.2%}",
        f"Volume: {metrics.real_pr_volume_count}",
    )
    table.add_row(
        "Sim-to-Real Gap (Delta)",
        f"{metrics.sim_to_real_gap:.2%}",
        "Max allowed: 25.00%",
    )
    table.add_row(
        "Action Distribution TV Divergence",
        f"{metrics.wasserstein_action_divergence:.4f}",
        "Max allowed: 0.3500",
    )
    table.add_row(
        "Shortcut Learning Index",
        f"{metrics.shortcut_learning_index:.4f}",
        "Max allowed: 0.4500",
    )
    table.add_row(
        "Stopping Signal Triggered",
        str(metrics.stopping_signal_triggered),
        metrics.stopping_reason or "Nominal calibration",
    )

    console.print(table)

    if metrics.stopping_signal_triggered:
        console.print(
            Panel(
                f"[bold red]EMERGENCY STOPPING SIGNAL TRIGGERED[/bold red]\n"
                f"Reason: {metrics.stopping_reason}",
                border_style="red",
            )
        )
        raise typer.Exit(code=2)


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", "-h", help="Bind address.")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", "-p", help="Port number.")] = 8080,
) -> None:
    """Launch the Mutant-RL telemetry REST API server and console."""
    console.print(
        f"[bold green]Starting Mutant-RL Telemetry Service on http://{host}:{port}[/bold green]"
    )
    uvicorn.run("mutant_rl.server:app", host=host, port=port, log_level="info")
