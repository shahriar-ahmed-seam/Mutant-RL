"""Trajectory action distribution divergence metrics."""

from __future__ import annotations

import math

from mutant_rl.schemas.trajectory import AgentActionType, PolicyTrajectory


class TrajectoryDistributionDivergence:
    """Computes statistical divergence between policy behavior on synthetic vs real PR tasks."""

    def compute_action_distribution(
        self, trajectories: list[PolicyTrajectory]
    ) -> dict[AgentActionType, float]:
        """Calculates normalized action frequencies across trajectories."""
        counts = {action: 0 for action in AgentActionType}
        total_actions = 0

        for traj in trajectories:
            for step in traj.steps:
                counts[step.action_type] = counts.get(step.action_type, 0) + 1
                total_actions += 1

        if total_actions == 0:
            return {a: 1.0 / len(AgentActionType) for a in AgentActionType}

        return {a: count / total_actions for a, count in counts.items()}

    def compute_total_variation_distance(
        self,
        synth_trajectories: list[PolicyTrajectory],
        real_trajectories: list[PolicyTrajectory],
    ) -> float:
        """Calculates Total Variation Distance (D_TV) between action distributions."""
        p_dist = self.compute_action_distribution(synth_trajectories)
        q_dist = self.compute_action_distribution(real_trajectories)

        tv_sum = sum(abs(p_dist[a] - q_dist[a]) for a in AgentActionType)
        return round(0.5 * tv_sum, 4)

    def compute_jensen_shannon_divergence(
        self,
        synth_trajectories: list[PolicyTrajectory],
        real_trajectories: list[PolicyTrajectory],
    ) -> float:
        """Calculates Jensen-Shannon Divergence between action distributions."""
        p_dist = self.compute_action_distribution(synth_trajectories)
        q_dist = self.compute_action_distribution(real_trajectories)

        eps = 1e-9
        m_dist = {a: 0.5 * (p_dist[a] + q_dist[a]) for a in AgentActionType}

        def kl_divergence(
            d1: dict[AgentActionType, float],
            d2: dict[AgentActionType, float],
        ) -> float:
            kl = 0.0
            for a in AgentActionType:
                p = max(eps, d1[a])
                q = max(eps, d2[a])
                kl += p * math.log2(p / q)
            return kl

        jsd = 0.5 * kl_divergence(p_dist, m_dist) + 0.5 * kl_divergence(q_dist, m_dist)
        return round(math.sqrt(max(0.0, jsd)), 4)
