# Track A: Continuous Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude 3.5 Sonnet | **Date:** 2026-11-04  
**Track Focus:** First- and Second-Order Continuous Optimization, Neural Backpropagation, and Loss Landscapes

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert optimization engineer. Implement Track A (Continuous Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Problem Formulation:
   - Formulate continuous optimization across three distinct mathematical landscapes:
     a) Strictly convex quadratic objective (well-conditioned and ill-conditioned).
     b) Non-convex landscape with saddle points and local minima (Rosenbrock / Rastrigin).
     c) Supervised learning loss: Binary cross-entropy training of a 2-layer Multi-Layer Perceptron (MLP) on a non-linearly separable dataset.
   - Define decision variables (continuous weights/vectors w in R^d), objective function f(w), gradients, and termination criteria (gradient norm < 1e-6 or max iterations).

2. Algorithm Selection (Chapter 6 Syllabus):
   - First-Order Methods: Implement Gradient Descent (GD), Stochastic Gradient Descent (SGD) with mini-batches, Classical Momentum, Nesterov Accelerated Gradient (NAG), AdaGrad, RMSProp, and Adam.
   - Second-Order & Curvature Methods: Implement exact Newton's method, Gauss-Newton approximation for non-linear least squares, and curvature approximations:
     * Hessian-vector products (HVP) via finite differences.
     * Power iteration to estimate top Hessian eigenvalue (spectral norm / Lipschitz constant).
     * Empirical Fisher Information matrix / diagonal curvature approximation.
   - Implement backpropagation from scratch as the explicit gradient computation engine behind the MLP.

3. Implementation Details:
   - Pure Python with NumPy only. Clean, modular architecture: `objectives.py`, `optimizers.py`, `mlp.py`, `curvature.py`.
   - Implement fair hyperparameter tuning: sweep all optimizers across an identical logarithmic learning-rate grid [1e-3, 10.0].
   - Deterministic random seeds across all stochastic runs.

4. Verification & Testing:
   - Write pytest tests (`test_optimizers.py`):
     * Verify backpropagation gradients against numerical two-sided finite differences to within 1e-6.
     * Verify power-iteration top eigenvalue against full Hessian matrix decomposition to 8 decimal places.
     * Verify quadratic convergence of Newton's method on strictly convex quadratics.
     * Verify all 7 first-order optimizers monotonically decrease loss on convex quadratics.

5. Fair Benchmarking & Critical Review:
   - Run all optimizers on identical starting points w_0.
   - Record: convergence trajectory, final loss, iterations to reach 1e-6 tolerance, wall-clock runtime, and sensitivity to learning rate.
   - Analyze trade-offs: per-iteration cost of second-order methods vs first-order step count, saddle point escape behaviors, and optimizer stability.
```

---

## Session Execution Summary

* **Scaffolding & Architecture:** Claude scaffolded `trackA_continuous/` with modular components:
  - `objectives.py`: Quadratic (convex), Rosenbrock (non-convex saddle/valley).
  - `optimizers.py`: GD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton.
  - `mlp.py`: 2-layer MLP classifier with pure-NumPy manual backpropagation.
  - `curvature.py`: HVP, Fisher information approximation, power-iteration spectral norm.
  - `run_track_a.py`: Comprehensive benchmarking script outputting `results/results.json` and plots.
  - `test_optimizers.py`: 11 test suites verifying correctness.

---

## Revisions & Debugging During Session

1. **Fair Grid Tuning:** Initial run evaluated optimizers on hand-picked learning rates. On review, this gave unfair advantage; updated to an automated grid search sweeping all optimizers over $\eta \in [10^{-3}, 10.0]$.
2. **Grid Boundary Extension:** Winners clustered at the upper boundary ($\eta = 1.0$) on quadratic objectives; grid was broadened up to $10.0$ to ensure true optima were captured.
3. **Tolerance Metric:** Final loss values around $10^{-20}$ differed only by floating-point rounding. Added an explicit `iterations_to_tolerance(1e-6)` metric to fairly assess convergence speed.
4. **Syntax Fix:** Corrected a keyword naming issue (`iters_to_1e-6` is not a valid Python identifier) to `iters_to_1e6`.

---

## Verification Note

* **11 pytest tests pass** (`python -m pytest trackA_continuous -q`).
* Backpropagation analytical gradients match numerical finite differences to $< 10^{-6}$.
* Power-iteration eigenvalue estimation agrees with `scipy.linalg.eigvalsh` to 8 significant digits.
* Benchmark figures and convergence tables in `TRACK_A_RESULTS.md` are directly populated from `results/results.json`.
