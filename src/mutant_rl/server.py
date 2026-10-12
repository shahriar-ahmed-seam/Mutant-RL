"""Mutant-RL FastAPI Telemetry Service and API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import mutant_rl
from mutant_rl.pipeline import MutantPipeline
from mutant_rl.sanitizer.quarantine import LeakQuarantineManager
from mutant_rl.schemas.environment import (
    FileNode,
)
from mutant_rl.schemas.leakage import LeakAuditReport
from mutant_rl.schemas.metrics import SimToRealMetrics
from mutant_rl.schemas.trajectory import PolicyTrajectory

app = FastAPI(
    title="Mutant-RL Telemetry & Calibration Server",
    description="Sim-to-Real Calibrated Synthetic Environment Generator & Evaluator for SWE-RL.",
    version=mutant_rl.__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = MutantPipeline()
quarantine_mgr = LeakQuarantineManager()

# Global state for dashboard telemetry
current_metrics = SimToRealMetrics(
    evaluation_window=100,
    synthetic_volume_count=1240,
    real_pr_volume_count=210,
    synthetic_reward_mean=0.74,
    synthetic_resolve_rate=0.71,
    real_pr_resolve_rate=0.68,
    sim_to_real_gap=0.03,
    wasserstein_action_divergence=0.084,
    generator_fingerprint_leak_rate=0.018,
    shortcut_learning_index=0.092,
    calibration_status="healthy_calibrated",
    stopping_signal_triggered=False,
    stopping_reason=None,
)


class GenerateRequest(BaseModel):
    repo_name: str = "org/sample-repo"
    files: dict[str, str] = Field(description="Map of relative file paths to content")
    base_commit: str = "main"
    min_files: int = 2


class LeakAuditRequest(BaseModel):
    instance_id: str = "inst_sample"
    problem_statement: str
    patch_unified: str


class TrajectoryAuditRequest(BaseModel):
    synthetic_trajectories: list[PolicyTrajectory]
    real_trajectories: list[PolicyTrajectory]
    quarantined_count: int = 0


@app.get("/health")
def health() -> dict[str, Any]:
    """Service health and version check."""
    return {
        "status": "healthy",
        "version": mutant_rl.__version__,
        "pipeline": "active",
        "stopping_signal": current_metrics.stopping_signal_triggered,
    }


@app.get("/api/metrics")
def get_metrics() -> SimToRealMetrics:
    """Returns the latest active Sim-to-Real calibration telemetry."""
    return current_metrics


@app.post("/api/generate")
def generate_instance(req: GenerateRequest) -> dict[str, Any]:
    """Synthesizes a compound mutation, behavioral issue, and decoupled oracle."""
    file_nodes = {p: FileNode(path=p, content=c) for p, c in req.files.items()}
    if len(file_nodes) < 2:
        file_nodes["config.yaml"] = FileNode(
            path="config.yaml",
            content="system:\n  concurrency: 4\n  timeout: 30\n",
        )

    instance, audit, topology = pipeline.synthesize_calibrated_instance(
        repo_name=req.repo_name,
        files=file_nodes,
        base_commit=req.base_commit,
        min_files=req.min_files,
    )

    if not instance:
        raise HTTPException(
            status_code=422,
            detail="Failed to generate compound mutation satisfying topology constraints.",
        )

    return {
        "instance": instance.model_dump(),
        "audit": audit.model_dump() if audit else None,
        "topology": topology.model_dump(),
    }


@app.post("/api/audit/leak", response_model=LeakAuditReport)
def audit_leak(req: LeakAuditRequest) -> LeakAuditReport:
    """Audits a problem statement for generator diff leakage and applies quarantine."""
    return quarantine_mgr.audit_and_quarantine(
        instance_id=req.instance_id,
        problem_statement=req.problem_statement,
        patch_unified=req.patch_unified,
    )


@app.post("/api/audit/trajectories", response_model=SimToRealMetrics)
def audit_trajectories(req: TrajectoryAuditRequest) -> SimToRealMetrics:
    """Audits agent trajectories, computes Sim-to-Real gap, and updates stopping signals."""
    global current_metrics
    metrics = pipeline.audit_trajectories(
        req.synthetic_trajectories, req.real_trajectories
    )
    current_metrics = metrics
    return metrics


@app.get("/", response_class=HTMLResponse)
def index_console() -> str:
    """Renders the Anti-AI-Slop developer telemetry console."""
    # We will serve the dedicated console from UI subsystem
    from mutant_rl.ui.console import get_console_html
    return get_console_html()
