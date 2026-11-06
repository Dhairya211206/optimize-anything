# Track C: Quantum Optimization, Results

**Everything in this track is a classical simulation. Nothing was run on quantum hardware.** The noise results use a synthetic depolarizing model, not a calibrated device model. Numbers come from `python trackC_quantum/run_track_c.py` (raw output in `results/results.json`). Checks are in `test_track_c.py` (13 tests). Tool used: PennyLane 0.45.1 (default.qubit and default.mixed simulators) plus a hand-written NumPy state-vector simulator, cross-checked against PennyLane to 1e-9.

## What was run

| Item | Setup |
|---|---|
| Problem | Max-Cut on the 8-node, 18-edge graph from Track B (exact optimum cut = 14, found by brute force) |
| QAOA | p = 1, 2, 3; cost Hamiltonian from the Track B Ising form (`J_ij = 1/2`, `h = 0`); energy of bitstring = minus its cut value |
| Optimizers | Adam driven by parameter-shift gradients, and SPSA |
| Fair budget | Both limited to 4,000 circuit evaluations. One parameter-shift gradient costs `2 x (gates)` evaluations (52 for p=1), so Adam gets 75, 38 and 25 steps for p=1, 2, 3. SPSA costs 2 evaluations per step |
| Seeds | Hyperparameters tuned on seeds 100 to 102, evaluated on seeds 0 to 19, so tuning and evaluation never share a start |
| Classical baselines | Exact brute force and simulated annealing (Track B), plus uniform random sampling |

## 1. Gradient correctness (the shared-parameter trap)

In QAOA, `gamma` drives 18 gates at once. Gradient error against finite differences over 20 random parameter sets:

| Gradient method | Max abs error p=1 | Max abs error p=2 |
|---|---|---|
| Parameter shift, applied per gate and summed | 7.7e-09 | 5.7e-09 |
| Naive shift of the shared parameter by +-pi/2 | 6.5 | 7.7 |

The naive rule is badly wrong (median error 3.5 and 2.5) because the generator `sum_e Z_i Z_j / 2` has more than two distinct eigenvalues. The per-gate rule is exact. Both are tested.

## 2. QAOA results (4,000 circuit evaluations, 20 starts)

Approximation ratio = expected cut / 14. Uniform random guess = 0.643.

| p | Adam + parameter shift | SPSA | Chosen Adam lr / SPSA a |
|---|---|---|---|
| 1 | 0.751 ± 0.021 (max 0.774) | 0.744 ± 0.031 (max 0.774) | 0.3 / 1.0 |
| 2 | 0.759 ± 0.046 (max 0.839) | 0.768 ± 0.040 (max 0.841) | 0.3 / 0.5 |
| 3 | 0.759 ± 0.056 (max 0.841) | 0.754 ± 0.071 (max 0.889) | 0.3 / 1.0 |

- For p=1 a dense grid search over (gamma, beta) gives the true best value, 0.774 (gamma 0.42, beta 1.27), and the best runs of both optimizers reach it, but the averages (about 0.75) are lower, so some starts end short of the best point at this budget.
- At this budget, Adam and SPSA are statistically indistinguishable, and a larger p did not raise the mean ratio. The best single runs did improve (0.774, then 0.84, then 0.89), but deeper circuits also got far fewer Adam steps (75, 38, 25), so this does not show that depth fails to help in principle.
- The chosen learning rates sit at the top of the tuning grid (0.3 for Adam, 1.0 for SPSA in two cases), so the grid was probably too narrow and these results are somewhat undertuned.
- Probability of seeing an optimal cut at least once in 100 measurement shots: 0.97 to 0.997 for optimised QAOA, versus 0.54 for uniform random sampling. Simulated annealing (Track B) found the optimum in 100% of runs, and a 256-state problem can simply be enumerated, so **this experiment shows no advantage over classical methods**.
- Cost of simulation: a state vector doubles with each qubit, so this approach cannot scale. That is a property of classical simulation, not of QAOA.

## 3. Finite measurement shots

At the best p=1 parameters (exact energy -10.831, single-shot standard deviation 1.564), 300 repeats per setting:

| Shots | Measured std of the estimate | Predicted sigma/sqrt(S) |
|---|---|---|
| 10 | 0.510 | 0.495 |
| 100 | 0.154 | 0.156 |
| 1,000 | 0.050 | 0.049 |
| 10,000 | 0.016 | 0.016 |
| 100,000 | 0.0049 | 0.0049 |

The estimator is unbiased and its error follows `1/sqrt(S)`. To halve the error you need four times the shots.

SPSA when every function evaluation is a finite-shot estimate (same a and c for all, not re-tuned, 300 steps, 20 starts, final energy evaluated exactly): approximation ratio 0.739 ± 0.030 (10 shots), 0.733 ± 0.042 (100), 0.729 ± 0.045 (1,000), and 0.733 ± 0.042 with exact expectations. At these settings SPSA gives the same result at every shot count, so this experiment does not show an effect of shot noise on SPSA, and no tuning was done to look for one.

## 4. Hardware-style noise (synthetic depolarizing model, simulated)

Single-qubit depolarizing noise after every gate (the circuit has 26 gate positions), p=1 QAOA at its best parameters:

| Depolarizing probability per gate | Approximation ratio |
|---|---|
| 0 | 0.774 |
| 0.001 | 0.772 |
| 0.003 | 0.770 |
| 0.01 | 0.760 |
| 0.03 | 0.737 |
| 0.1 | 0.683 |

Noise pulls the result toward the random-guess ratio of 0.643. At 1% noise per gate only about 0.014 of ratio is lost, but the circuit here is tiny (26 gates). Deeper circuits have more gates and lose more. A fully depolarized state returns the random-guess energy exactly (tested).

## 5. Barren plateaus

Variance of `dC/dtheta` for one fixed parameter (middle layer, middle qubit) over 200 random initialisations, RY + CZ-chain circuit. Slope = fitted change in log2(variance) per added qubit (n = 4 to 12).

| Circuit and cost | Variance at n=4 | at n=12 | Slope per qubit |
|---|---|---|---|
| Deep (L = 2n), global cost | 4.8e-03 | 9.5e-07 | -1.63 |
| Deep (L = 2n), local cost | 5.2e-03 | 4.9e-05 | -0.80 |
| Shallow (L = 2), global cost | 3.7e-03 | 4.1e-07 | -1.60 |
| Shallow (L = 2), local cost | 4.7e-03 | 5.4e-04 | -0.38 |

The global-cost gradient variance drops by roughly a factor of 3 for every added qubit at either depth, so at 12 qubits it is thousands of times smaller than at 4 (about 5,000 times for the deep circuit and 9,000 times for the shallow one). The local cost decays much more slowly, especially for a shallow circuit. With only 2 to 12 qubits and 200 samples per point, I cannot say whether the slow local-cost decay is polynomial or exponential, so no claim is made about its asymptotic form. The last global point at n=12 deep is also noisy.

## 6. VQE (4-qubit transverse-field Ising chain, exact ground energy -4.7588)

Hardware-efficient ansatz, 16 parameters. Classical baseline: exact diagonalisation. 5 random starts per optimizer, learning rates tuned on separate seeds. Error = energy minus exact ground energy. "Executions" are PennyLane's count, and each Hamiltonian term group counts separately, so absolute values are 3 times the number of energy evaluations.

| Optimizer | Chosen lr | Steps | Final error (mean ± std) | Range | Starts reaching error < 0.01 | Total executions per run |
|---|---|---|---|---|---|---|
| Gradient descent (parameter shift) | 0.3 | 80 | 0.107 ± 0.148 | 0.0002 to 0.397 | 1 of 5 | 7,920 |
| Adam (parameter shift) | 0.3 | 80 | 0.0111 ± 0.0049 | 0.0036 to 0.0171 | 2 of 5 | 7,920 |
| Quantum natural gradient (block-diagonal metric) | 0.03 | 80 | 0.066 ± 0.057 | 0.0044 to 0.167 | 1 of 5 | 8,240 |
| SPSA | 1.0 | 400 | 0.038 ± 0.012 | 0.018 to 0.051 | 0 of 5 | 2,400 |

Reading it correctly:
- Adam gave the lowest typical error at roughly equal execution cost for the three gradient-based methods.
- **SPSA stopped at about 30% of the executions the others used** (2,400 versus about 7,900) and its error curve was still falling, so this table does not rank SPSA against the others at equal cost.
- QNG's best learning rate (0.03) is the lowest value in the grid, and GD, Adam and SPSA picked values at the top of theirs. The grids were too narrow to judge the optimizers fairly, and I do not conclude that QNG is worse in general. Its extra metric-tensor cost also appears in its execution count (8,240).
- Five starts per method is a small sample, and the range for GD (0.0002 to 0.397) shows high sensitivity to the starting point.

## Not covered in this track

- **Real quantum hardware**: no access in this environment.
- **Quantum neural networks, variational classifiers and quantum kernels**: planned for Track I.
- **Quantum annealing and the limits of embedding a QUBO on annealer hardware**: no annealer was used. This should be discussed in the report from your lecture notes.
- **Qiskit**: not used, PennyLane was used instead.

## Limitations

- All tests are on tiny problems (8 qubits for QAOA, 4 for VQE, up to 12 for barren plateaus), chosen so exact answers exist.
- Learning-rate grids were narrow (several winners at the edge), and the shot experiment reuses untuned SPSA settings.
- Runtimes are not reported because they measure simulator overhead, not quantum cost. Execution counts are the fair cost measure used here.
