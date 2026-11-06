# Chapter 6 Coverage Checklist

The assignment says this must match the exact syllabus taught in class. Compare against your lecture slides and add or remove rows.

Status: Done / Planned. Update "Result" with the real number or plot after each run.

## Foundations

| Technique | Track | Code | Result |
|---|---|---|---|
| ML as optimization (parameters, loss, regularization) | A | `trackA_continuous/run_track_a.py` (section 5), `mlp.py` | Done (see `report/TECHNICAL_REPORT.md` Sec 1) |
| Continuous vs discrete | A, B | `trackA_continuous/`, `trackB_discrete/` | Done (see `report/TECHNICAL_REPORT.md` Sec 1) |
| Convex vs non-convex landscapes | A | `objectives.py` (quadratic vs Rosenbrock/Himmelblau) | Done |
| Local minima, global minima, saddle points | A | `objectives.py` (Himmelblau, saddle `x^2 - y^2`) | Done |
| Basic quantum concepts, optimization in QML | C, I | `trackC_quantum/`, `trackI_quantum_qml/` | Done (see `report/TECHNICAL_REPORT.md` Sec 1 & `FINAL_QUESTIONS.md`) |

## Continuous optimization (Track A)

| Technique | Code | Result |
|---|---|---|
| Gradient Descent | `optimizers.py: gd` | Done |
| SGD, mini-batch SGD | `optimizers.py: sgd` (batch size parameter) | Done |
| Momentum | `optimizers.py: momentum` | Done |
| Nesterov (NAG) | `optimizers.py: nag` | Done |
| AdaGrad | `optimizers.py: adagrad` | Done |
| RMSProp | `optimizers.py: rmsprop` | Done |
| Adam | `optimizers.py: adam` | Done |
| Newton | `optimizers.py: newton` | Done |
| Gauss-Newton | `optimizers.py: gauss_newton` | Done |
| Backpropagation (separate from the optimizer) | `mlp.py` (hand-written, checked against finite differences) | Done |
| Curvature approximations: Hessian-vector product, diagonal, Fisher | `curvature.py` | Done |
| Convergence: convex, strongly convex, non-convex | `run_track_a.py` | Done |
| Step-size / optimizer tuning | `run_track_a.py` (learning-rate sweep) | Done |
| Noisy objectives | `run_track_a.py` (noisy gradient experiment) | Done |

## Discrete optimization (Track B)

| Technique | Code | Result |
|---|---|---|
| Greedy | `trackB_discrete/discrete.py: greedy` | Done. Gap 0.59% on n=20, up to 8% on correlated instances; counterexample in tests |
| Integer Linear Programming | `discrete.py: ilp`, `qubo.py: maxcut_ilp` (HiGHS via `scipy.optimize.milp`) | Done. Matches DP and brute force |
| Branch-and-Bound | `discrete.py: bnb` | Done. Node counts reported |
| Dynamic programming | `discrete.py: dp` | Done. Cost vs capacity value measured |
| Feature selection (combinatorial) | `qubo.py: feature_selection_qubo`, `greedy_forward_selection` | Done. Exact vs greedy vs annealing |
| QUBO formulation, penalty terms | `qubo.py` (Max-Cut, feature selection cardinality penalty) | Done. Penalty sweep |
| Ising formulation, binary-to-spin | `qubo.py: qubo_to_ising` | Done. Verified on all assignments |
| Max-Cut | `qubo.py`, `run_track_b.py` | Done. n=8 (used by Track C) and n=20 |

Not covered in Track B: scheduling and portfolio selection (listed only as examples in the assignment).

## Quantum optimization (Tracks C, I)

Track C (all SIMULATED, no hardware):

| Technique | Code | Result |
|---|---|---|
| QAOA on the Track B Max-Cut QUBO | `trackC_quantum/qaoa_sim.py`, `run_track_c.py` | See `trackC_quantum/TRACK_C_RESULTS.md` |
| VQE (PQC ansatz), classical baseline = exact diagonalisation | `vqe.py` | See results file |
| Parameter-shift (per-gate; naive shared shift shown to be wrong) | `qaoa_sim.py` | Tested vs finite differences |
| SPSA | `qaoa_sim.py: spsa`, `vqe.py` | See results file |
| Quantum natural gradient | `vqe.py` (PennyLane `QNGOptimizer`, block-diagonal metric) | See results file |
| Finite measurement shots | `run_track_c.py: exp_shots` | See results file |
| Hardware noise (synthetic depolarizing model) | `run_track_c.py: exp_noise` | See results file |
| Barren plateaus | `barren.py` | See results file |
| Limits of QUBO on annealing hardware | `maxcut_qubo.py`, `trackB_discrete/qubo.py` | Done (analyzed in `report/TECHNICAL_REPORT.md` Sec 1 & `FINAL_QUESTIONS.md`) |

Planned for Track I: Deutsch-Jozsa, Bernstein-Vazirani, Grover, QFT, QPE, Shor, variational classifier, quantum kernels, QNN. Include only the algorithms your course taught.

## Submodular, parallel, distributed (Track D)

Results in `trackD_submodular_parallel/TRACK_D_RESULTS.md`. Real parallel timings come from a 2-core machine; results for more workers are labelled SIMULATED.

| Technique | Code | Result |
|---|---|---|
| Diminishing-returns test (numerical check of submodularity and monotonicity) | `submodular.py: check_conditions` | Done. Facility location passes; relevance minus redundancy is submodular but not monotone; synergy objective fails |
| Greedy selection and the 1 - 1/e guarantee | `submodular.py: greedy` | Done. Worst ratio 0.938 on facility location; guarantee stated only where its conditions hold |
| Lazy greedy | `submodular.py: lazy_greedy` | Done. Same value, 4.4x fewer evaluations |
| Speedup, efficiency, Amdahl, Gustafson | `parallel_exp.py` | Done (measured, 2 cores). Strong and weak scaling |
| Load balancing, makespan, work stealing | `parallel_exp.py: run_*`, `simulate_schedule` | Done. Measured on 2 workers, simulated up to 32 |
| Data / model / pipeline parallelism | `parallel_exp.py` | Done. Model parallelism gave no speedup here (negative result). Pipeline uses sleep-based stages |
| FedAvg, IID vs non-IID, communication rounds | `federated.py` | Done. 5 seeds; no clear drift at this scale |
| MGDA | `multitask.py: mgda_alpha` | Done. Closed form checked against grid search; starved task 2 in our setup |
| GradNorm | `multitask.py: train(method="gradnorm")` | Done. Best average, not best on each task |

## Main case study and strategy selection (Track E)

Shift rostering with synthetic data. Results in `trackE_case_study/TRACK_E_RESULTS.md`.

| Item | Where | Result |
|---|---|---|
| Formulation (variables, objective, constraints) | `roster.py`, results file section 1 | Done |
| Strategy-selection table (greedy, DP, B&B/ILP, hill climbing, annealing, CP, QUBO) | results file section 2 | Done |
| Method comparison with variability | `run_track_e.py` | Done. ILP proven optimal on all 16 instances; greedy about 25% above optimum; annealing 7 to 27% above |
| Sensitivity (annealing budget, fairness weight, ILP scaling to 600 x 28) | `run_extra.py`, `run_track_e.py` | Done |

## Compiler optimization (Track F)

Results in `trackF_compiler/TRACK_F_RESULTS.md`.

| Technique | Code | Result |
|---|---|---|
| Constant folding and propagation | `opt.py: const_fold` | Done |
| Algebraic simplification and strength reduction | `opt.py: strength` | Done (gain depends on the assumed mul = 3 cost) |
| Copy propagation, CSE | `opt.py: copy_prop`, `cse` | Done |
| Loop-invariant code motion | `opt.py: licm` | Done, with liveness-based safety conditions and tests |
| Dead-code elimination | `opt.py: dce` | Done |
| Register allocation as optimisation (linear scan, greedy, exact ILP) | `regalloc.py` | Done. ILP removes 33% of spill traffic vs linear scan on the benchmarks |
| Correctness by differential fuzzing | `fuzz.py`, `test_track_f.py` | 0 mismatches in 400 programs x 7 configurations |

## xv6 kernel optimization (Track G)

Results in `trackG_xv6/TRACK_G_RESULTS.md`.

| Technique | Code | Result |
|---|---|---|
| Reducing lock contention (per-CPU free lists, batch stealing) | `kernel/kalloc.c` | Failed lock attempts 500k to 0; wall-clock unchanged within noise (QEMU) |
| Scheduling policy as optimisation (lottery, proportional share) | `kernel/proc.c` | 10/20/70 tickets give 10.7/19.6/69.6% CPU; worse than round-robin for equal tickets |
| Benchmarking and variability | `run_track_g.py` | 3+ workloads, 20 runs each, mean ± std |
| Correctness | usertests -q | passes on all four kernel builds |

## Database optimization (Track H)

Results in `trackH_dbms/TRACK_H_RESULTS.md`.

| Technique | Code | Result |
|---|---|---|
| Index selection as budgeted optimisation (knapsack/ILP) | `selection.py` | Done |
| Greedy, knapsack DP, exact ILP vs default planner | `run_track_h.py` | Best measured speedup about 1.5x; exact ILP can be 2.6x slower than no index at larger budgets |
| Model vs reality (planner interaction) | harm-aware ILP | Recovers 1.47x to 1.55x |
| Result equality | `dbutil.result_hash` | identical in every configuration |

## Quantum algorithms and QML (Track I)

Results in `trackI_quantum_qml/TRACK_I_RESULTS.md`.

| Technique | Code | Result |
|---|---|---|
| Deutsch-Jozsa, Bernstein-Vazirani, Grover, QFT, QPE, Shor | `qalgs.py`, `qsim.py` | Done, simulated, cross-checked against PennyLane |
| Noise model | `run_track_i.py` | Synthetic depolarizing noise erases the Grover advantage by p about 0.1 |
| QNN and quantum kernel vs classical | `qml_sim.py` | No advantage; RBF-SVM equal or better |
| Contrast with parallel speedups (Track D) | results doc | Documented |

## Software-engineering optimization (Track J)

Results in `trackJ_software_eng/TRACK_J_RESULTS.md`.

| Technique | Code | Result |
|---|---|---|
| Test-suite minimisation as set cover (ILP vs greedy vs random) | `setcover.py` | 55% less summed test time at 100% line coverage |
| Prioritisation (APFD) | `setcover.py` | Greedy most-new-lines 0.89 vs random 0.81 |
| Mutation testing of the minimised suites | `mutate.py` | 4% to 10% of killed mutants lost |

