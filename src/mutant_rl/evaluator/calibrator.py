"""Real PR anchor calibration for synthetic generator tuning."""

from __future__ import annotations

from dataclasses import dataclass

from mutant_rl.schemas.environment import EnvironmentInstance


@dataclass
class GeneratorCalibrationWeights:
    """Tuned parameter weights aligning synthetic generator to real PR distributions."""

    min_files_per_mutation: int
    config_code_mutation_ratio: float
    target_problem_statement_length: int
    recommended_compound_batch_size: int
    calibration_confidence: float


class RealPRAnchorCalibrator:
    """Calibrates synthetic generation parameters against empirical real PR distributions."""

    def calibrate_from_real_prs(
        self, real_pr_instances: list[EnvironmentInstance]
    ) -> GeneratorCalibrationWeights:
        """Extracts topological and linguistic distributions from real PR instances."""
        if not real_pr_instances:
            # Default conservative calibration
            return GeneratorCalibrationWeights(
                min_files_per_mutation=2,
                config_code_mutation_ratio=0.25,
                target_problem_statement_length=250,
                recommended_compound_batch_size=32,
                calibration_confidence=0.50,
            )

        file_counts = [len(inst.files) for inst in real_pr_instances]
        avg_files = sum(file_counts) / len(file_counts)

        # Config files ratio
        config_files_count = 0
        total_files = 0
        for inst in real_pr_instances:
            for p in inst.files.keys():
                total_files += 1
                if p.endswith((".yaml", ".yml", ".toml", ".json")):
                    config_files_count += 1

        config_ratio = config_files_count / max(1, total_files)

        # Problem statement word length
        lengths = [len(inst.problem_statement.split()) for inst in real_pr_instances]
        avg_len = sum(lengths) / max(1, len(lengths))

        min_files = max(2, int(round(avg_files * 0.7)))

        confidence = min(0.99, 0.50 + (len(real_pr_instances) * 0.05))

        return GeneratorCalibrationWeights(
            min_files_per_mutation=min_files,
            config_code_mutation_ratio=round(max(0.15, config_ratio), 3),
            target_problem_statement_length=int(avg_len),
            recommended_compound_batch_size=64,
            calibration_confidence=round(confidence, 3),
        )
