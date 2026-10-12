# Mathematical Metric Formulations and Benchmark Evaluation Standards

This document establishes the mathematical foundations, statistical estimators, confidence bounds, and production acceptance criteria implemented in Mutant-RL.

---

## 1. Action Space and Distribution Divergence

Let $\mathcal{A}$ denote the set of discrete actions available to a coding agent:

$$\mathcal{A} = \{ \text{edit\_file}, \text{view\_file}, \text{list\_dir}, \text{run\_command}, \text{grep\_search}, \text{git\_revert}, \text{git\_checkout}, \text{other} \}$$

For a set of $N$ trajectories $\mathcal{T}_{\text{synth}}$ collected on synthetic environments and $M$ trajectories $\mathcal{T}_{\text{real}}$ collected on empirical real pull requests, the empirical action probability vectors $P \in \Delta^{|\mathcal{A}|}$ and $Q \in \Delta^{|\mathcal{A}|}$ are defined as:

$$P(a) = \frac{\sum_{\tau \in \mathcal{T}_{\text{synth}}} \sum_{s \in \tau} \mathbb{I}(s.\text{action} = a)}{\sum_{\tau \in \mathcal{T}_{\text{synth}}} |\tau|}, \quad Q(a) = \frac{\sum_{\tau \in \mathcal{T}_{\text{real}}} \sum_{s \in \tau} \mathbb{I}(s.\text{action} = a)}{\sum_{\tau \in \mathcal{T}_{\text{real}}} |\tau|}$$

### Total Variation Distance
The Total Variation Distance $D_{\text{TV}}(P, Q)$ provides an upper bound on the maximum difference in probability assigned to any subset of actions:

$$D_{\text{TV}}(P, Q) = \frac{1}{2} \sum_{a \in \mathcal{A}} |P(a) - Q(a)|$$

Bounded on the unit interval: $0 \le D_{\text{TV}}(P, Q) \le 1$.

### Jensen-Shannon Divergence
The symmetric Jensen-Shannon divergence measures informational divergence between synthetic and real behaviors:

$$M(a) = \frac{1}{2} (P(a) + Q(a))$$

$$D_{\text{JS}}(P \parallel Q) = \frac{1}{2} D_{\text{KL}}(P \parallel M) + \frac{1}{2} D_{\text{KL}}(Q \parallel M)$$

The Jensen-Shannon distance is defined as $\sqrt{D_{\text{JS}}(P \parallel Q)}$.

---

## 2. Sim-to-Real Transfer Gap and Statistical Bounds

Let $Y_{\text{synth}, i} \sim \text{Bernoulli}(\rho_{\text{synth}})$ and $Y_{\text{real}, j} \sim \text{Bernoulli}(\rho_{\text{real}})$ denote binary task resolution indicators.

The sample resolve rates are:

$$\hat{\rho}_{\text{synth}} = \frac{1}{N} \sum_{i=1}^N Y_{\text{synth}, i}, \quad \hat{\rho}_{\text{real}} = \frac{1}{M} \sum_{j=1}^M Y_{\text{real}, j}$$

### Sim-to-Real Gap
The transfer gap $\Delta$ is defined as:

$$\hat{\Delta} = \hat{\rho}_{\text{synth}} - \hat{\rho}_{\text{real}}$$

Under independent Bernoulli trials, the asymptotic variance of $\hat{\Delta}$ is:

$$\text{Var}(\hat{\Delta}) = \frac{\hat{\rho}_{\text{synth}}(1 - \hat{\rho}_{\text{synth}})}{N} + \frac{\hat{\rho}_{\text{real}}(1 - \hat{\rho}_{\text{real}})}{M}$$

The two-sided $(1 - \alpha)$ confidence interval using the Wilson score approximation is:

$$\hat{\Delta} \pm z_{1 - \alpha/2} \sqrt{\text{Var}(\hat{\Delta})}$$

For $\alpha = 0.05$, $z_{1 - \alpha/2} \approx 1.96$.

---

## 3. Shortcut Learning Exploitation Index

To detect whether a policy has overfit to synthetic generator artifacts, we evaluate four orthogonal behavioral indicators for each trajectory $\tau$:

1. **Revert Ratio ($r_{\text{rev}}$)**:
   $$r_{\text{rev}}(\tau) = \frac{1}{|\tau|} \sum_{s \in \tau} \mathbb{I}(s.\text{is\_revert} \lor s.\text{action} \in \{\text{git\_revert}, \text{git\_checkout}\})$$

2. **Isolated Single-Line Edit Ratio ($r_{\text{1line}}$)**:
   $$r_{\text{1line}}(\tau) = \frac{\sum_{s \in \tau} \mathbb{I}(s.\text{action} = \text{edit} \land s.\text{lines} = 1)}{\max(1, \sum_{s \in \tau} \mathbb{I}(s.\text{action} = \text{edit}))}$$

3. **Blind Diff Search Ratio ($r_{\text{diff}}$)**:
   $$r_{\text{diff}}(\tau) = \frac{1}{|\tau|} \sum_{s \in \tau} \mathbb{I}(s.\text{is\_diff\_grep})$$

4. **Shallow Exploration Deficit ($s_{\text{shallow}}$)**:
   $$s_{\text{shallow}}(\tau) = \max\left(0, 1 - \frac{\sum_{s \in \tau} \mathbb{I}(s.\text{action} = \text{view})}{2 \cdot \max(1, \sum_{s \in \tau} \mathbb{I}(s.\text{action} = \text{edit}))}\right)$$

The aggregate Shortcut Exploitation Index $I_{\text{shortcut}}$ is computed via weighted linear combination:

$$I_{\text{shortcut}}(\tau) = 0.40 \cdot r_{\text{rev}}(\tau) + 0.30 \cdot r_{\text{1line}}(\tau) + 0.20 \cdot r_{\text{diff}}(\tau) + 0.10 \cdot s_{\text{shallow}}(\tau)$$

---

## 4. Production Acceptance Criteria

A policy checkpoint or synthetic generator configuration is certified as production-ready for reinforcement learning training if and only if it satisfies all of the following invariants over an evaluation window $N \ge 100$:

| Telemetry Metric | Production Bound | Interpretation |
|---|---|---|
| Transfer Gap $\hat{\Delta}$ | $\le 0.150$ | Synthetic and real resolve rates remain closely coupled |
| TV Action Divergence $D_{\text{TV}}$ | $\le 0.200$ | Tool usage distribution matches real software development |
| Shortcut Index $I_{\text{shortcut}}$ | $\le 0.250$ | Policy engages in multi-file reasoning, not trivial reverts |
| Leak Quarantine Rate $\lambda_{\text{leak}}$ | $\le 0.050$ | Problem statements exhibit minimal diff text or symbol leaks |
| AST Syntax Preservation Rate | $= 1.000$ | 100% of generated environments preserve AST parseability |
