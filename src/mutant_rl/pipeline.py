"""End-to-end pipeline linking mutators, leak sanitizers, and evaluators."""

from __future__ import annotations

from mutant_rl.evaluator.auditor import SimToRealGapAuditor
from mutant_rl.evaluator.calibrator import (
    GeneratorCalibrationWeights,
    RealPRAnchorCalibrator,
)
from mutant_rl.mutator.engine import CompoundMutationEngine
from mutant_rl.mutator.oracle import DecoupledOracleSynthesizer
from mutant_rl.sanitizer.quarantine import LeakQuarantineManager
from mutant_rl.sanitizer.synthesizer import BehavioralIssueSynthesizer
from mutant_rl.schemas.environment import (
    EnvironmentInstance,
    FileNode,
    InstanceType,
)
from mutant_rl.schemas.leakage import LeakAuditReport
from mutant_rl.schemas.metrics import SimToRealMetrics
from mutant_rl.schemas.mutation import MutationTopology
from mutant_rl.schemas.trajectory import PolicyTrajectory


class MutantPipeline:
    """High-throughput synthesis and sim-to-real evaluation orchestrator."""

    def __init__(self) -> None:
        self.mutation_engine = CompoundMutationEngine()
        self.oracle_synthesizer = DecoupledOracleSynthesizer()
        self.issue_synthesizer = BehavioralIssueSynthesizer()
        self.quarantine_manager = LeakQuarantineManager()
        self.gap_auditor = SimToRealGapAuditor()
        self.anchor_calibrator = RealPRAnchorCalibrator()

    def synthesize_calibrated_instance(
        self,
        repo_name: str,
        files: dict[str, FileNode],
        base_commit: str = "main",
        min_files: int = 2,
    ) -> tuple[EnvironmentInstance | None, LeakAuditReport | None, MutationTopology]:
        """Synthesizes a compound mutation, generates blackbox issue, and validates leakage."""
        mutation, topology = self.mutation_engine.generate_compound_mutation(
            files, min_files=min_files
        )

        if not mutation:
            return None, None, topology

        mutated_files = self.mutation_engine.apply_mutation(files, mutation)
        patch = self.mutation_engine.generate_ground_truth_patch(files, mutated_files)
        test_patch = self.oracle_synthesizer.synthesize_reproduction_test(
            mutation, module_name=repo_name.replace("/", ".")
        )

        # Behavioral issue synthesis
        behavior_spec = self.issue_synthesizer.synthesize_from_coupled_mutation(repo_name, mutation)
        raw_statement = self.issue_synthesizer.synthesize_from_spec(behavior_spec)

        # Audit against diff leakage
        audit = self.quarantine_manager.audit_and_quarantine(
            instance_id=f"inst_{mutation.mutation_id}",
            problem_statement=raw_statement,
            patch_unified=patch,
        )

        if audit.is_compromised or audit.quarantine_action == "reject":
            return None, audit, topology

        final_statement = audit.sanitized_statement or raw_statement

        instance = EnvironmentInstance(
            instance_id=audit.instance_id,
            repo_name=repo_name,
            base_commit=base_commit,
            instance_type=InstanceType.SYNTHETIC,
            problem_statement=final_statement,
            files=mutated_files,
            patch=patch,
            test_patch=test_patch,
            oracle_command="pytest",
            metadata={
                "mutation_id": mutation.mutation_id,
                "operator_type": mutation.operator_type.value,
                "topology_density": topology.graph_density,
                "config_code_ratio": topology.config_code_ratio,
            },
        )

        return instance, audit, topology

    def audit_trajectories(
        self,
        synthetic_trajectories: list[PolicyTrajectory],
        real_trajectories: list[PolicyTrajectory],
    ) -> SimToRealMetrics:
        """Computes Sim-to-Real gap, divergence, and stopping signals."""
        return self.gap_auditor.audit_trajectories(synthetic_trajectories, real_trajectories)

    def calibrate_generator(
        self, real_instances: list[EnvironmentInstance]
    ) -> GeneratorCalibrationWeights:
        """Calibrates generation parameters against empirical real PR distributions."""
        return self.anchor_calibrator.calibrate_from_real_prs(real_instances)
