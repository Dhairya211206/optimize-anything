# Track A: Continuous Optimization, Results

All numbers come from `python trackA_continuous/run_track_a.py` (raw output in `results/results.json`). Hardware: a shared cloud Linux VM, single-threaded NumPy, so runtimes are indicative only and dominated by Python overhead.

## Objective of the track

Compare the Chapter 6 continuous optimizers on a convex objective, non-convex objectives and a small ML model, and show how the landscape changes the outcome.

## Setup and fairness rules

- Same start point and same iteration budget for every method on a given problem (200 iterations on the quadratic, 5000 on Rosenbrock, 1500 on the MLP).
- Learning rate tuned per method on one shared grid (`1e-4` to `10`, 11 values), best final value kept.
- Stochastic experiments use seeds 0 to 9 and report mean plus or minus standard deviation.
- Correctness checks: `test_optimizers.py` (11 tests). Backprop matches finite differences to 1e-6. Analytic gradients and Hessians of all four test functions match finite differences. Newton solves the quadratic in one step. Gauss-Newton solves linear least squares in one step.

## 1. Strongly convex quadratic (condition number 20)

| Method | Best lr | Iterations to f < 1e-6 | Final f after 200 its |
|---|---|---|---|
| GD | 0.03 | not reached | 4.1e-05 |
| Momentum | 0.1 | 159 | 1.4e-08 |
| NAG | 0.03 | 68 | 1.1e-13 |
| AdaGrad | 3.0 | 7 | ~1e-224 |
| RMSProp | 0.03 | 170 | 7.8e-08 |
| Adam | 0.3 | 151 | 1.1e-08 |
| Newton | none | 1 | 0 |

Reading it correctly:
- Newton finishes in one step because the quadratic's Hessian is exact. This is a property of quadratics, not a general result.
- The AdaGrad row should not be taken as "AdaGrad is best". The tuner picked lr = 3.0, whose first step happens to land close to the optimum from this one start point. Final values near 1e-224 are below any meaningful precision. This is tuning to a single start. The curves in `convex_quadratic.png` and the iterations-to-tolerance column are the fairer comparison.
- Rate check: GD with lr = 1/L stays under the bound `f0 * (1 - mu/L)^(2k)` for all 60 iterations tested.

## 2. Non-convex: Rosenbrock (5000 iterations)

| Method | Best lr | Iterations to f < 1e-6 | Final f |
|---|---|---|---|
| GD | 0.001 | not reached | 5.0e-03 |
| Momentum | 0.001 | 1390 | 9.1e-20 |
| NAG | 0.001 | 1381 | 9.5e-20 |
| AdaGrad | 1.0 | not reached | 2.7e-04 |
| RMSProp | 0.001 | not reached | 5.6e-04 |
| Adam | 10.0 | 2914 | 3.0e-28 |
| Newton | none | 5 | 0 |

- Plain GD is slow in the curved valley because the stable step size is limited by the steep direction. Momentum and NAG gave the clearest gains over GD.
- Adam's tuned lr = 10 sits at the edge of the grid and is large. That result is specific to this start point and I would not generalise it.
- Newton converges in 5 iterations but each iteration needs the Hessian and a linear solve. Its path in `rosenbrock_paths.png` overshoots first (it passes through y about -4.8), so a damped or line-search version would be needed for safety.

## 3. Local minima and saddle points

- Himmelblau has four minima. From 200 random starts, final basin counts (minimum order: (3,2), (-2.81,3.13), (-3.78,-3.28), (3.58,-1.85)):
  GD [55, 52, 34, 59], Momentum [68, 50, 38, 44], Adam [62, 52, 36, 50], Newton [34, 31, 15, 32].
  Newton's counts sum to 112, not 200: the other starts ended at a saddle, the local maximum, or did not converge within 60 steps. The start point decides which minimum a method finds.
- Saddle `f = x^2 - y^2`, start (1, 0.001): GD escapes along y (|y| = 1.47 after 40 steps). Started exactly on y = 0 it converges to the saddle. Newton lands on the saddle in one step, because it is attracted to any stationary point.

## 4. ML as an optimization problem: backprop plus optimizers

Model: 2-8-1 tanh MLP, BCE loss plus L2 (lambda = 1e-3), 300 two-moons points, 1500 iterations, learning rate tuned per method, mean plus or minus std over 10 seeds.

| Method | lr | Train loss | Test accuracy |
|---|---|---|---|
| GD | 3.0 | 0.1124 ± 0.0007 | 0.992 ± 0.002 |
| SGD (batch 1) | 0.03 | 0.3114 ± 0.0040 | 0.904 ± 0.005 |
| Mini-batch SGD (32) | 1.0 | 0.1182 ± 0.0032 | 0.983 ± 0.005 |
| Momentum | 1.0 | 0.1121 ± 0.0005 | 0.991 ± 0.002 |
| NAG | 1.0 | 0.1120 ± 0.0006 | 0.992 ± 0.002 |
| AdaGrad | 1.0 | 0.1124 ± 0.0006 | 0.992 ± 0.002 |
| RMSProp | 0.01 | 0.1126 ± 0.0004 | 0.991 ± 0.002 |
| Adam | 0.1 | 0.1117 ± 0.0004 | 0.991 ± 0.002 |

- Once each method's learning rate is tuned, full-batch methods are essentially tied. Differences in the fourth decimal are not meaningful at this sample size.
- Several chosen learning rates are large, and several optimizers prefer different settings. The earlier version of this script used hand-picked learning rates and showed adaptive methods clearly ahead of GD. That gap was an artefact of untuned GD (see `FAILURE_LOG.md` candidate 1).
- SGD with batch 1 and mini-batch 32 do far less work per iteration than full-batch methods, so equal iteration counts are not equal compute.
- Regularization (single seed, 300 test points): weight norm falls from 19.5 (lambda = 0) to 9.8, 2.8 and 1.7 for lambda = 1e-3, 1e-2, 1e-1. Test accuracy was 0.983, 0.990, 0.907, 0.873. The change from 0.983 to 0.990 is within noise at this test-set size. The only supported conclusion is that too much regularization hurts here.

## 5. Gauss-Newton on nonlinear least squares

Fit `a * exp(-b t)` to 40 noisy points (true a = 2.0, b = 1.3).
- Gauss-Newton, 15 iterations: f = 1.2176e-3, parameters (2.0010, 1.3033).
- GD, 15 iterations: f = 0.339. GD, 2000 iterations: f = 1.2176e-3 (same optimum).
- Gauss-Newton ignores the second-order residual term, which is why it works well here (small residuals) and can fail when residuals stay large.

## 6. Noisy objective (gradient noise sigma = 1, 2000 iterations, 10 seeds)

| Method | Final f (mean ± std) |
|---|---|
| GD, lr 0.05 | 0.032 ± 0.032 |
| GD, lr 0.005 | 0.0032 ± 0.0028 |
| Adam, lr 0.05 | 0.027 ± 0.051 |
| SGD, decaying lr | 0.0015 ± 0.0011 |

A constant step leaves a noise floor that shrinks with a smaller or decaying step. The learning rates in this table were set by hand, not tuned, so it supports the noise-floor point and not any ranking of Adam against GD.

## 7. Curvature (trained MLP, 33 parameters)

- Hessian-vector products by central difference. Power iteration with deflation found the top three Hessian eigenvalues (0.5697, 0.2505, 0.0930), matching the exact eigenvalues from the full 33 x 33 Hessian to 8 digits.
- Smallest eigenvalue is -2.3e-4 (one slightly negative). The trained point is not an exact minimum, so I would describe this as a nearly flat direction, not claim it is a saddle.
- Diagonal Hessian by Hutchinson's estimator (300 samples) correlates 0.97 with the diagonal empirical Fisher. For this model near a good fit they are close; the Fisher is not equal to the Hessian in general.

## Limitations

- Toy problems and a very small network. Behaviour on large non-convex models can differ, and Newton and full-Hessian methods do not scale.
- Learning rates were tuned on the same start point used for reporting (and on seed 0 for the MLP), so the tuned results are slightly optimistic and a few winners sit at the edge of the grid.
- Runtimes are small and noisy; they are not a reliable speed ranking.
- Convergence theory (convex, strongly convex, non-convex) is only checked empirically by the rate test above. The write-up should state the theoretical rates from your lecture notes, with this experiment as supporting evidence.

## Figures

`results/convex_quadratic.png`, `rosenbrock.png`, `rosenbrock_paths.png`, `himmelblau.png`, `lr_sensitivity.png`, `mlp_training.png`, `noisy.png`.
