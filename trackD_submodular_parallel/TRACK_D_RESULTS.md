# Track D: Submodular, Parallel and Distributed Optimization

Run: `python trackD_submodular_parallel/run_track_d.py` (about 40 s). Tests: `python -m pytest trackD_submodular_parallel -q` (16 pass).
Raw numbers: `results/results.json`. Figures: `results/parallel.png`, `results/fedavg.png`, `results/multitask.png`.

**Measured vs simulated, stated up front.** The machine has 2 CPU cores. Real parallel speedups cannot exceed about 2, and any result with p > 2 workers is either oversubscribed (labelled) or comes from a discrete-event simulation (labelled SIMULATED). The pipeline experiment uses `time.sleep` as stage work. Federated clients are simulated on one machine and communication is counted in rounds, not measured.

## D1. Submodular maximisation

We checked the conditions numerically (3000 random (A ⊆ B, x) triples per objective) before relying on any guarantee.

| Objective | Diminishing-returns violations | Monotonicity violations | Greedy guarantee applies? |
|---|---|---|---|
| Facility location | 0 | 0 | Yes (monotone submodular): ≥ 1 − 1/e ≈ 0.632 of OPT |
| Relevance − redundancy (the Track B feature objective) | 0 | 2076 | No: submodular but not monotone |
| Relevance + synergy | 2432 | 0 | No: not submodular |

Greedy against the exact optimum (exhaustive search):
- Facility location, n=16, k=4, 10 instances: worst ratio 0.938, mean 0.970. The 0.632 bound holds, with a large margin. The bound is a worst-case guarantee, so a much better typical ratio is expected.
- Relevance − redundancy, n=12: ratios 0.990 to 1.0 for k=3..6 (the theorem does not cover this case; this is empirical).
- Relevance + synergy, n=12: greedy found the optimum for every k tried. The guarantee does not apply, so this is luck on one small instance, not evidence that greedy is safe for supermodular objectives.

Lazy greedy (n=500 candidates, k=20): same value as standard greedy, 2241 marginal-gain evaluations instead of 9811 (4.4× fewer), 0.019 s vs 0.095 s. Lazy greedy is only valid because marginal gains can only shrink (submodularity).

## D2. Parallel computing

**Strong scaling (measured, 64 CPU tasks, median of 3).**

| Workers | Time (s) | Speedup | Efficiency |
|---|---|---|---|
| 1 | 0.635 | 1.00 | 1.00 |
| 2 | 0.382 | 1.66 | 0.83 |
| 4 (more workers than cores) | 0.414 | 1.53 | 0.38 |

Amdahl fitted at p=2 gives a "serial fraction" of 0.20. That number lumps together process start-up, chunking and result transfer, not only truly serial code, and it was fitted from one point. Extrapolating it to p=4 predicts 2.49, but the measured 1.53 is lower because only 2 cores exist. Amdahl's law does not model oversubscription.

**Weak scaling (Gustafson, measured).** Problem size grows with workers: scaled speedup 0.87 (p=1; a timing-noise reference, since it should be 1), 1.68 (p=2), 1.81 (p=4, oversubscribed). The p=1 reading shows run-to-run noise of about 15%, so small differences here are not meaningful.

**Load balancing, measured, 2 workers, 60 lognormally skewed tasks sorted largest first** (ideal makespan 0.434 s):

| Strategy | Time (s) | Ratio to ideal |
|---|---|---|
| Static blocks | 0.765 | 1.76 |
| Static round-robin | 0.461 | 1.06 |
| Dynamic queue | 0.522 | 1.20 |
| Dynamic, longest first | 0.559 | 1.29 |

Static blocks are clearly worst, because one block holds the biggest tasks. The ordering among the other three is within the noise level seen above (one task set, 3 repeats), so we do not claim round-robin beats dynamic scheduling in general. In theory longest-first should not be worse than plain dynamic; its measured deficit is most likely noise plus pool overhead.

**Scheduling at larger scale, SIMULATED (1000 skewed tasks, makespan ÷ lower bound):**

| p | static block | round-robin | dynamic | LPT | work stealing |
|---|---|---|---|---|---|
| 4 | 1.07 | 1.09 | 1.01 | 1.00 | 1.02 |
| 8 | 1.12 | 1.19 | 1.04 | 1.00 | 1.02 |
| 16 | 1.37 | 1.43 | 1.25 | 1.00 | 1.12 |
| 32 | 1.97 | 1.73 | 1.67 | 1.00 | 1.46 |

Imbalance matters more as p grows (fewer tasks per worker, so the largest tasks dominate). LPT is near the lower bound because it sees all task costs in advance, an assumption real systems often cannot make. Work stealing (113 steals at p=32, with steal cost and a locality penalty) sits between static and LPT.

**Overhead vs granularity, SIMULATED (8 workers, per-dispatch/steal cost 0.05).** With tiny tasks (mean cost 0.02), a central dynamic queue is 3.5× the lower bound, worse than static blocks (1.18), while work stealing stays at 1.10. With large tasks (mean 10), dynamic is best (1.01). So the best strategy depends on task granularity relative to scheduling overhead. The overhead constants are assumptions we chose, not measurements.

**Pipeline parallelism (real processes, stage work is `sleep`, so this checks overlap, not compute).** Balanced 3×30 ms stages, 30 micro-batches: 2.77× vs 2.81× predicted by sum + (M−1)·max. Unbalanced 20/60/20 ms: 1.62× vs 1.63× predicted. The slowest stage sets throughput, and balancing stages matters more than adding stages.

**Model parallelism (one layer's columns split over 2 worker processes, input sent to both on every call, output verified equal).**

| Hidden size | Single (s) | Two processes (s) | Speedup |
|---|---|---|---|
| 512 | 0.011 | 0.038 | 0.28 |
| 2048 | 0.043 | 0.051 | 0.84 |
| 8192 | 0.158 | 0.183 | 0.86 |

Honest negative result: splitting did not help at any size tried. Inter-process communication of the batch dominates, and numpy matmul already runs in optimised native code. We cannot say where the break-even point lies on this machine; it would need larger layers or a real interconnect.

## D3. FedAvg vs centralized training (logistic regression, 10 clients × 200 samples, d=20, 5 seeds, 40 rounds)

Mean test accuracy after 40 rounds (± std over seeds):

| Setting | IID | Non-IID (label skew + covariate shift) |
|---|---|---|
| FedAvg E=1 | 0.864 ± 0.027 | 0.781 ± 0.038 |
| FedAvg E=5 | 0.865 ± 0.029 | 0.841 ± 0.040 |
| FedAvg E=20 | 0.866 ± 0.030 | 0.860 ± 0.037 |
| Centralized SGD, same sequential steps as E=5 | 0.864 ± 0.029 | 0.831 ± 0.040 |
| Centralized SGD, same total gradient work as E=5 | 0.868 ± 0.029 | 0.844 ± 0.043 |

Reading these numbers carefully:
- With IID data all methods agree to within the seed standard deviation (about 0.03).
- With non-IID data, more local steps per round gave **better** accuracy per communication round, not worse. At this model size and learning rate, we do not see client drift hurting; E=1 is simply slower per round. The differences between E=5, E=20 and centralized (0.84 to 0.86) are within one standard deviation, so we cannot rank them. Only E=1 is clearly lower.
- Drift is known to hurt with larger local work, a stronger skew or non-convex models. We did not test those settings, so this result should not be read as "FedAvg is immune to non-IID data".

## D4. Multi-task weighting (two tasks, shared tanh layer, task 2 targets about 25× larger, 5 seeds, 1500 Adam steps)

Test relative MSE (0 = perfect, 1 = no better than the mean):

| Method | Task 1 | Task 2 | Mean of tasks |
|---|---|---|---|
| Equal weights | 0.430 ± 0.171 | 0.039 ± 0.010 | 0.234 ± 0.089 |
| MGDA (min-norm) | 0.027 ± 0.018 | 0.690 ± 0.239 | 0.358 ± 0.111 |
| GradNorm (α=1.5) | 0.188 ± 0.085 | 0.077 ± 0.023 | 0.132 ± 0.054 |

- Equal weighting lets the large-scale task 2 dominate; task 1 is learned poorly.
- MGDA did the opposite: its final weights were about (2.0, 0.00001). Min-norm weighting favours the task with the smaller gradient, here task 1, so task 2 was starved. We used raw gradients. The original MGDA-UB paper normalises gradients first, which may behave differently, and we did not test that variant.
- GradNorm gave the best average and the most balanced result, but it did not beat the best method on either single task. Its tuned constants (`gn_lr`, α) were set by hand with no separate validation sweep, so "GradNorm is best" is a statement about this one synthetic setup.
- Both adaptive methods have the std shown across only 5 seeds.

## Caveats
- 2-core machine; p > 2 results are oversubscribed or simulated.
- Timings are short (under 1 s) and have about 15% run-to-run noise.
- Small synthetic instances throughout.
- Simulator overheads (dispatch, steal, locality) are assumed constants.
