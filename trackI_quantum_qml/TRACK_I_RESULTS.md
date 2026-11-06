# Track I: Quantum Algorithms and Quantum ML, Results

**Everything here is a classical state-vector simulation written for this repo (`qsim.py`, `qalgs.py`, `qml_sim.py`). Nothing was run on quantum hardware.** The noise experiment uses a synthetic depolarizing model, not a calibrated device model. All "quantum" timings are simulator times and say nothing about quantum hardware speed. Numbers come from `python trackI_quantum_qml/run_track_i.py` (about 30 s for algorithms, a few minutes for QML) and are stored in `results/results.json`.

## What was built

| Item | Notes |
|---|---|
| Simulator | NumPy state vector, qubit 0 is the most significant bit. Gates: single-qubit, controlled, controlled-phase, swap, Hadamard on all qubits, QFT circuit. |
| Hand-written circuits | Deutsch-Jozsa, Bernstein-Vazirani, Grover, QFT, QPE, Shor order finding, data re-uploading QNN, ZZ feature-map kernel. That is well over the required two. |
| Cross-checks | 15 tests (`test_track_i.py`): closed-form Grover probability, gate-level vs fast Grover, QFT circuit equals the DFT matrix to ~1e-15, unitarity, agreement with PennyLane (QFT, Grover, QNN expectation), parameter-shift gradient vs finite differences, kernel is symmetric, PSD, unit diagonal. |
| Noise experiment | PennyLane `default.mixed`, synthetic depolarizing noise after each gate. This is a **noise model**, not hardware. |

## 1. Deutsch-Jozsa and Bernstein-Vazirani

One simulated query decides constant vs balanced (DJ) or recovers the secret string (BV), with probability 1 up to rounding. The classical deterministic worst case is 2^(n-1)+1 queries for DJ and n for BV. Caveat: a *randomized* classical algorithm solves DJ with a handful of queries with tiny error, so the DJ gap is only against deterministic classical algorithms. BV's n vs 1 is a genuine query gap.

## 2. Grover vs linear search

Marked item placed at N/2, so the classical scan needs N/2+1 calls (its average). Quantum uses the optimal number of iterations.

| n qubits | N | Grover oracle calls | Success prob. | Classical expected calls | Call ratio | Grover simulation time | Python linear scan time |
|---|---|---|---|---|---|---|---|
| 4 | 16 | 3 | 0.961 | 8.5 | 2.8x | 0.1 ms | ~0 |
| 8 | 256 | 12 | 1.000 | 128.5 | 10.7x | 0.04 ms | 0.01 ms |
| 12 | 4,096 | 50 | 1.000 | 2,048.5 | 41x | 0.4 ms | 0.1 ms |
| 16 | 65,536 | 201 | 1.000 | 32,768.5 | 163x | 27 ms | 1.7 ms |
| 20 | 1,048,576 | 804 | 1.000 | 524,288.5 | 652x | 2.1 s | 28 ms |

- Query count follows (pi/4)sqrt(N), as expected. The measured success curve matches sin^2((2k+1)theta) to ~1e-14 and shows the overshoot: for n=6 it peaks at k=6 (0.9966) and falls to ~0 at k=12 if you keep iterating.
- Gate count: each iteration is one oracle query plus 2n Hadamards, 2n X gates and one n-qubit controlled-Z (O(n) elementary gates with ancillas, O(n^2) without). The oracle itself is counted as one query; building it for a real unstructured database is not free and is not counted here.
- **Wall-clock: the simulated Grover is slower than a plain Python linear scan at every size** (2.1 s vs 28 ms at n=20), because the simulator spends 2^n work per iteration. Query reduction is real in the oracle-call model; it is not a speedup of this program.

## 3. QFT and QPE

- QFT circuit vs DFT matrix: max error ~1e-15.
- QPE for phase 5/16 is exact once t >= 4 counting qubits. For phase 0.3 (not a dyadic fraction) the error falls as t grows, and the best outcome carries about 0.875 probability, so a single shot is not guaranteed to give the best estimate.

## 4. Shor order finding (simulated)

Modular exponentiation is applied as a permutation at oracle level (not compiled to elementary gates), and the inverse QFT uses an FFT checked against the circuit. So gate counts for the arithmetic are not reported and no fault-tolerant resource claim is made.

| N | Qubits | Mean per-shot factoring probability over bases | Simulation time | Classical trial division |
|---|---|---|---|---|
| 15 | 12 | 0.57 | ms | 2 steps |
| 21 | 15 | 0.38 | ms | 2 steps |
| 35 | 18 | 0.61 | ms | 2-6 steps |
| 77 | 21 | 0.36 | 17.5 s | 2-6 steps |

The algorithm factors these small numbers correctly in simulation, but trial division is trivially faster at this size. Shor's asymptotic advantage is a claim about large N on fault-tolerant hardware; nothing here tests it.

## 5. Noisy Grover (synthetic noise)

3 qubits, depolarizing probability p after every gate (the three-qubit CCZ counted as one gate). Success probability of finding the marked item:

| p | k=2 iterations | k=1 iteration |
|---|---|---|
| 0 | 0.945 | 0.781 |
| 0.001 | 0.915 | 0.767 |
| 0.003 | 0.857 | 0.741 |
| 0.01 | 0.687 | 0.655 |
| 0.03 | 0.393 | 0.471 |
| 0.1 | 0.149 | 0.202 |

Reference: random guess 0.125; a classical algorithm making 2 queries succeeds with probability 0.25. With this noise model, the deeper circuit (k=2) stops being the better choice by p = 0.03, where the shallower k=1 circuit does better (0.471 vs 0.393). Both stay above the classical 2-query success of 0.25 at p = 0.03, but by p = 0.1 both are below it (0.149 and 0.202), and k=2 is close to a random guess. This shows noise erasing the query advantage; it is not a prediction for any specific device.

## 6. QML vs classical on the same data

Data: two-moons and concentric circles, 2 features, same train/test split per seed, 5 seeds, test accuracy mean ± std.

| Dataset | Model | Test accuracy | Train time | Trainable parameters / support vectors | Circuit executions |
|---|---|---|---|---|---|
| moons | QNN (4-layer data re-uploading, 16 params) | 0.948 ± 0.024 | 2.35 s | 16 | ~396,000 |
| moons | Quantum kernel SVM (ZZ map) | 0.927 ± 0.008 | 0.11 s | 13 SV | ~32,000 |
| moons | RBF SVM | 0.945 ± 0.018 | ms | n/a | 0 |
| moons | MLP | 0.932 ± 0.021 | | 33 | 0 |
| moons | Logistic regression | 0.865 | | 3 | 0 |
| circles | QNN | 0.974 ± 0.017 | | 16 | ~396,000 |
| circles | Quantum kernel SVM | 0.979 ± 0.013 | | | |
| circles | RBF SVM | 0.993 ± 0.004 | | n/a | 0 |
| circles | MLP | 0.948 | | | 0 |
| circles | Logistic regression | 0.431 | | 3 | 0 |

Notes on fairness: QNN gradients are exact parameter-shift, so circuit runs = epochs x N x (1 + 2P). The quantum kernel's feature scale and C were tuned with the same 3-fold CV budget as the RBF grid. Before that tuning the quantum kernel looked about 15 points worse (about 0.77), which was a comparison artifact, not a property of the method (Failure Log entry 12).

Finite-shot QNN (moons): accuracy 0.825 with 1 shot per prediction, 0.916 (5), 0.951 (25), 0.957 (125), 0.960 (625). Readout noise from few shots costs accuracy, and shots multiply the circuit-execution cost on real hardware.

**Result: no quantum advantage.** The classical RBF-SVM is as good (moons) or better (circles) with essentially zero circuit evaluations. The QNN matches RBF on moons but costs ~10^5 to 10^6 simulated circuit runs and 16 parameters vs a few support vectors. This is an honest negative result for these toy datasets.

## When quantum helps, when it does not, and the contrast with Track D

| | Track D (classical parallel) | Track I (quantum) |
|---|---|---|
| Speedup measured on | real wall-clock, 2 cores | oracle-call count in simulation; wall-clock is slower |
| Size of gain | at most ~1.7x on 2 cores, bounded by core count and Amdahl | query ratio grows as sqrt(N) (652x at n=20) |
| Where it applies | any task you can split across workers | only a structured subroutine (search oracle, period finding) and only if the oracle is cheap and the machine is fault tolerant |
| Hidden costs | communication, serial part | state preparation / data loading, oracle construction, error correction overhead, readout shots |

Where quantum should not be expected to help: tiny inputs (simulation cost dominates and classical is trivial), problems solved by randomized classical algorithms (DJ), data loading-bound ML (loading N numbers into amplitudes costs about N operations, erasing a sublinear advantage unless data are already quantum), and trainability-limited circuits: Track C measured the gradient variance of a global-cost circuit falling by roughly 3x per added qubit (about 5,000x smaller at 12 qubits than at 4), which makes training deeper circuits hard (barren plateaus).

## Limits and honesty notes

- Simulator only; the 2^n memory/time cost is why timings go the wrong way.
- Synthetic noise, one qubit count (3), one noise channel. No hardware experiment was run.
- Small toy datasets, 5 seeds; differences of ~1-2 points are within the seed spread.
- Shor's modular arithmetic is oracle-level, not a gate-level circuit.
- Grover's oracle cost is counted as one query, as in the query-complexity model.
- No claim of quantum advantage is made anywhere in this track.

## Files

`qsim.py`, `qalgs.py`, `qml_sim.py`, `run_track_i.py`, `test_track_i.py`, `results/` (results.json, grover.png, grover_noise.png, qml.png, run_output.txt).
