"""Unit and integration tests for CLI commands and FastAPI telemetry server."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mutant_rl.cli import app as cli_app
from mutant_rl.server import app as api_app

runner = CliRunner()
client = TestClient(api_app)


def test_cli_version():
    result = runner.invoke(cli_app, ["version"])
    assert result.exit_code == 0
    assert "Mutant-RL" in result.stdout


def test_cli_generate(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "math_util.py").write_text("def add(a: int, b: int):\n    return a + b\n")
    (src_dir / "runner.py").write_text("def run():\n    return add(1, 2)\n")

    out_file = tmp_path / "out.json"
    result = runner.invoke(cli_app, ["generate", str(src_dir), "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text())
    assert "instance_id" in data
    assert "problem_statement" in data


def test_cli_audit_leak(tmp_path: Path):
    stmt = tmp_path / "stmt.txt"
    patch = tmp_path / "patch.diff"

    stmt.write_text("Crash observed when executing data loader.")
    patch.write_text("--- a/f.py\n+++ b/f.py\n+def fix_conn(): pass\n")

    result = runner.invoke(cli_app, ["audit-leak", "--statement", str(stmt), "--patch", str(patch)])
    assert result.exit_code == 0
    assert "Quarantine Decision: ALLOW" in result.stdout


def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_metrics():
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "sim_to_real_gap" in data
    assert "calibration_status" in data


def test_api_generate():
    payload = {
        "repo_name": "org/calc",
        "files": {
            "calc.py": "def add(x: int, y: int):\n    return x + y\n",
            "caller.py": "def compute():\n    return add(1, 2)\n",
        },
    }
    res = client.post("/api/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "instance" in data
    assert "topology" in data
    assert data["instance"]["repo_name"] == "org/calc"


def test_api_leak_audit():
    payload = {
        "instance_id": "test_1",
        "problem_statement": "System failed to connect on port 8080.",
        "patch_unified": "--- a/s.py\n+++ b/s.py\n+def bind_socket(): pass\n",
    }
    res = client.post("/api/audit/leak", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["quarantine_action"] == "allow"
    assert data["is_compromised"] is False
