# Optimize Anything: Technical Report

Course: Optimization Techniques, Assignment 8 (14-Day Vibe-Coding Challenge). Student: Dhairya.
Repository layout, setup and run commands: `README.md`. Chapter 6 mapping: `CHECKLIST.md`. AI disclosure: `AI_TOOLS_REGISTER.md`, `FAILURE_LOG.md`, `TOOL_COMPARISON.md`, `prompts/`. Answers to the eleven-section final questions: `report/FINAL_QUESTIONS.md`. Demo outline: `report/DEMO_SCRIPT.md`.

**How to read the numbers.** Every result is labelled *measured* (wall-clock or counted on this machine, a shared 2-core cloud VM), *simulated* (a model or a classical simulation of something else), or *theoretical*. Nothing was run on quantum hardware. xv6 ran under QEMU emulation. All data in Tracks E and H are synthetic. Stochastic methods report mean ± standard deviation over repeated seeds. Each track's own results file has the full tables, setup and caveats; this report summarises them and does not replace them.

## 1. Summary of outcomes

| Track | What was optimised | Main outcome | Evidence label |
|---|---|---|---|
| A | Continuous optimisers (GD, momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss-Newton) | Momentum/NAG clearly beat plain GD on Rosenbrock (1,390 vs not converged in 5,000 its); Newton takes 1 step on a quadratic but overshoots on Rosenbrock; a constant step leaves a noise floor | measured |
| B | Knapsack; Max-Cut and feature selection as QUBO/Ising | DP and branch-and-bound match brute force; greedy can be arbitrarily bad (2 vs 15 on a 2-item case); annealing finds the Max-Cut optimum in 100% of runs, hill climbing in 50% | measured |
| C | QAOA, VQE, SPSA, shots, noise, barren plateaus | QAOA reaches an approximation ratio about 0.75 vs 0.64 for a random guess, but classical annealing is exact on this size; global-cost gradient variance falls about 3x per added qubit | simulated |
| D | Submodular greedy, parallelism, FedAvg, multi-task weighting | Greedy within 0.94 of optimum on facility location (bound 0.63); real parallel speedup 1.66x on 2 cores; GradNorm best on average in multi-task, MGDA starved one task | measured + labelled simulation |
| E | Shift rostering (main case study) | Exact ILP optimal and fastest (0.04–0.73 s); greedy 25–27% above optimum; annealing 7–27% above | measured on synthetic data |
| F | Mini compiler: 6 passes, register allocation | Full pipeline cost ratio 0.467 (geometric mean; depends on an assumed mul = 3 cycles); ILP allocation cuts spill traffic 33% vs linear scan; 0 mismatches in 400 fuzz programs × 7 configurations | measured (instruction counts) + assumed cost model |
| G | xv6 kernel: per-CPU allocator, lottery scheduler | Lock contention removed (about 500k failed attempts to 0) with no measurable run-time change; lottery follows tickets (69.6% for a 70% share) but is less fair than round-robin for equal tickets | measured under QEMU |
| H | Index selection on SQLite | Best speedup about 1.5x; the exact ILP can make the workload 2.6x slower because the model ignores planner interaction; a harm-aware ILP recovers 1.47–1.55x | measured on synthetic data |
| I | Quantum algorithms and QML | Grover cuts oracle calls up to 652x (n=20) but the simulation is slower than a Python scan; no QML advantage | simulated + theoretical |
| J | Test-suite minimisation | 55% less summed test time at the same line coverage; 4–10% of killed mutants lost | measured |

Two results are deliberate negative or neutral findings and are reported as such: G feature 1 (no run-time gain) and I (no quantum advantage). Several results are *worse* than the baseline in some settings (H exact ILP, G lottery with equal tickets, F `register_pressure` program unchanged, D MGDA on task 2), and the explanation for each is in its section.

## 2. Process followed

For every track: state the objective, fix a baseline, formulate variables/objective/constraints, choose methods and say why, run under equal conditions (same data, budgets and seeds), then compare and discuss trade-offs. AI-generated code was checked by tests that compare against an independent reference (brute force, finite differences, a PennyLane implementation, a reference interpreter, or stock xv6 behaviour). Section 9 lists what the AI got wrong.

## 3. Track A: Continuous optimisation
Code `trackA_continuous/`, results `TRACK_A_RESULTS.md`, tests in `test_optimizers.py`.

- **Setup:** quadratic with condition number 20, Rosenbrock, saddle/local-minimum landscapes, an MLP trained by backprop (33 parameters), nonlinear least squares, noisy gradients. Learning rates tuned per method on a separate start, evaluated on others (fair-tuning rule; Failure Log 1–2).
- **Findings:** Newton: 1 step on the quadratic (a property of quadratics only), 5 on Rosenbrock with an overshoot. Momentum and NAG: 1,390 and 1,381 iterations on Rosenbrock; GD does not reach 1e-6. Adam's tuned rate sits at the edge of the grid, so no ranking of Adam is claimed. With gradient noise, a constant step stalls at a noise floor (0.032 ± 0.032) and a decaying step does better (0.0015 ± 0.0011); learning rates there were hand-set, so no ranking is claimed. Analytic gradients/Hessians are verified against finite differences.
- **Trade-off:** second-order methods cost a Hessian and a solve per step and need safeguards.

## 4. Track B: Discrete optimisation and QUBO/Ising
Code `trackB_discrete/`, results `TRACK_B_RESULTS.md`.

- **Knapsack (20 items):** optimum 682; greedy 678 (0.59% gap), DP, branch-and-bound and ILP exact, brute force as reference. DP's table grows about 96x when weights are scaled up (pseudo-polynomial). A two-item instance shows greedy can return 2 against an optimum of 15.
- **Max-Cut as QUBO:** `Q_ii = -deg(i)`, `Q_ij = 2` per edge; Ising `J_ij = Q_ij/4`. Tests check that the QUBO energy equals minus the cut for every assignment and that the Ising conversion is exact. Annealing: 100% optimal (8 and 20 nodes); hill climbing 50% and 24%.
- **Feature selection with a penalty:** greedy is within 0.07%–1.0% of the exact optimum; annealing reached the exact subset in only 10–17% of runs at 200 sweeps. The first explanation I wrote for this weak result was wrong (Failure Log 6).

## 5. Track C: Quantum optimisation (simulation only)
Code `trackC_quantum/`, results `TRACK_C_RESULTS.md`.

- **QAOA on the Track B 8-node Max-Cut** (optimum 14), p = 1 to 3, with parameter-shift Adam and SPSA at equal 4,000-circuit budgets, 20 starts: mean ratio 0.744–0.768, indistinguishable between optimisers, versus 0.643 for random sampling. Annealing finds the optimum every time, so **no advantage over classical is claimed**.
- **Correctness trap:** a shared QAOA parameter drives many gates, so the naive ±π/2 shift is wrong (error up to 7.7 vs 6e-9 for the per-gate rule; Failure Log 7).
- **Shots, noise, barren plateaus, VQE:** finite shots add sampling variance as expected; synthetic depolarizing noise lowers the result; global-cost gradient variance falls about 1.6 bits (about 3x) per added qubit (4 to 12 qubits); VQE on a 4-qubit Ising chain compared across optimisers at unequal evaluation counts (SPSA used about 30% of the evaluations, so no ranking).

## 6. Track D: Submodular, parallel, federated, multi-task
Code `trackD_submodular_parallel/`, results `TRACK_D_RESULTS.md`.

- **Submodular greedy:** conditions were checked numerically before relying on any guarantee. Facility location (monotone submodular): worst ratio 0.938, mean 0.970 vs the 0.632 bound. The relevance−redundancy objective is submodular but not monotone, and the synergy objective is not submodular, so the guarantee does not apply there (results are empirical only). Lazy greedy: 4.4x fewer evaluations, same value.
- **Parallel (measured, 2 cores):** 64 CPU tasks, 1.66x with 2 workers (efficiency 0.83), 1.53x with 4 (oversubscribed). Larger worker counts are labelled discrete-event simulation. Pipeline parallelism matches the model sum + (M−1)·max (2.77x vs 2.81x). Load balancing and granularity: dynamic queues lose to static blocks on tiny tasks (3.5x vs 1.18x the bound) and win on large ones.
- **FedAvg:** with IID data all methods agree within noise (about 0.86); with non-IID data, more local steps helped (0.781 for E=1, 0.860 for E=20); drift was not seen at this scale, which is not evidence of immunity.
- **Multi-task:** equal weights lets the large-scale task dominate; MGDA with raw gradients starved task 2 (0.690 error); GradNorm best mean (0.132 vs 0.234) but not on either single task.

## 7. Track E: Main case study, shift rostering
Code `trackE_case_study/`, results `TRACK_E_RESULTS.md`.

- **Problem:** assign workers to morning/evening/night shifts over D days to minimise preference cost plus a workload-spread penalty, subject to coverage, one shift per day, availability, at most 5 shifts in any 7 days, and no morning after a night. A 0-1 ILP, NP-hard in general. Data are synthetic. The ILP equals brute force on tiny instances.
- **Baselines and methods:** greedy, hill climbing, simulated annealing, exact ILP (HiGHS); DP and CP were considered and not used (reasons in the strategy table).
- **Results (gap to proven optimum):** greedy 24.5–26.8%; hill climbing 19–22%; annealing 6.7%, 10.0%, 13.8%, 26.8% across the four sizes. The ILP took 0.04–0.73 s up to 150 × 28 and scaled to 50,400 binary variables in 1.8 s. At the largest size, annealing at default settings returned the greedy roster (tuning/budget problem; 1.5M iterations reached 10.8% in one run). A spread of 2 shifts costs about 2% extra preference cost.
- **Limits:** real rosters have more rules (skills, contracts) that could make the ILP much harder; the numbers describe this synthetic generator only.

## 8. Tracks F to J (systems and software)

### Track F: Compiler optimisation
Code `trackF_compiler/`, results `TRACK_F_RESULTS.md`. A mini compiler (parser, three-address IR, VM) with constant folding, strength reduction, copy propagation, CSE, loop-invariant code motion and dead-code elimination, plus register allocation as an optimisation problem.
- **Pass ablation on seven programs:** all passes give a geometric-mean weighted-cost ratio of 0.467 (dynamic instruction count 0.596); the headline is flattered by one program that collapses from 19 instructions to 2, and the mul→shift saving exists only because mul was set to 3 cycles. No pass dominates; passes enable each other (removing `dce` from the full pipeline raises the ratio to 0.683); CSE adds nothing on top of the others here; one program was not improved.
- **Register allocation (K = 4):** exact ILP cuts spill traffic to 6,698 vs 10,069 (linear scan, −33%) and 7,807 (greedy, −14%); on random programs linear scan is 41% ± 38% above the ILP static optimum. The ILP is checked against exhaustive search.
- **Correctness:** differential testing against a reference interpreter, 0 mismatches in 400 random programs × 7 pass configurations; tests for LICM safety hazards.

### Track G: xv6 kernel
Code and patch `trackG_xv6/` (`xv6_changes.patch`, applies to xv6-riscv commit e93dabe), results `TRACK_G_RESULTS.md`. Two kernel changes: a per-CPU page allocator with batch stealing (lock-contention concept) and a lottery scheduler with `settickets` (proportional-share scheduling concept).
- **Correctness:** `usertests -q` passes on all four kernel builds; the maximum obtainable pages (32,469) are identical before and after.
- **Allocator:** failed lock attempts fall from 503,874 and 568,610 to 0 on the 3- and 8-process memory benchmarks; run time is unchanged within noise (std 8–15% of the mean). No speedup is claimed; the zeroing of pages outside the lock dominates and QEMU timing is noisy.
- **Scheduler (1 CPU, shortened timer in both kernels):** shares 10.7/19.6/69.6% for tickets 10/20/70 (error 2.6 points) vs 24.5 for round-robin, but 2.5 vs 0.6 points of error when all tickets are equal.
- A biased benchmark that made the scheduler look worse was caught and fixed (Failure Log 11).

### Track H: DBMS
Code `trackH_dbms/`, results `TRACK_H_RESULTS.md`. Index selection on SQLite as a budgeted problem (ILP with `y_i`, `x_qi`, storage constraint), on synthetic TPC-H-like data (600,487 line items), 12 weighted queries, 25 candidates.
- **Methods:** greedy by ratio, knapsack DP, greedy marginal, exact ILP, a harm-aware ILP (our extension), and the default planner. Result hashes are identical to the no-index run in every configuration.
- **Outcome:** best speedup about 1.5x, reached with 5 MB; building all 25 indexes gives 0.93x. At a 20% budget the exact ILP's predicted 0.38 s saving became a measured 1.1 s loss (0.38x): with `li_shipmode_shipdate` present, SQLite replaced a table scan with an index search plus row lookups (Q1 152 ms → 872 ms). The harm-aware ILP gave 1.47–1.55x at every budget. EXPLAIN plans before and after are in the results.

### Track I: Quantum algorithms and QML
Code `trackI_quantum_qml/`, results `TRACK_I_RESULTS.md`. A NumPy state-vector simulator with hand-written circuits (Deutsch-Jozsa, Bernstein-Vazirani, Grover, QFT, QPE, Shor order finding), a noisy Grover run (synthetic noise), and QNN/quantum-kernel versus classical models.
- **Grover:** oracle calls 3 to 804 (n = 4 to 20) vs expected classical (N+1)/2: a 2.8x to 652x call ratio, success ≥ 0.96; simulated wall-clock is slower than a Python scan (2.1 s vs 28 ms at n = 20).
- **QML:** moons — QNN 0.948 ± 0.024 (16 parameters, about 396k circuit runs), quantum kernel 0.927 ± 0.008, RBF-SVM 0.945 ± 0.018; circles — RBF 0.993 vs QNN 0.974, kernel 0.979. No advantage. A fair tuning budget was needed (Failure Log 12).
- **Contrast with Track D:** parallel speedup is measured on real cores but small (at most 1.7x on 2 cores); quantum query reduction is large in the oracle model but is not a wall-clock gain here and ignores data loading, oracle cost, error correction and shots.

### Track J: Software-engineering optimisation
Code `trackJ_software_eng/`, results `TRACK_J_RESULTS.md`. Test-suite minimisation as weighted set cover over the repository's own 5,159 lines of Python (76 tests), checked with a custom mutation tester.
- **Profile:** one test is 51% of the 12.2 s suite. **Gain:** exact ILP and greedy cut summed test time to 5.5 s at the same 100% line coverage (−55%).
- **Cost:** on the Track F compiler (90 mutants, full suite kills 72 of 89 valid), the ILP subset keeps 95.8% of kills and the smallest 6-test suite 90.3%; random subsets of the same size keep 93.2% ± 4.5%, so the ILP's advantage is not clearly significant. Prioritisation: only "most new lines first" beats random on APFD (0.89 vs 0.81 ± 0.05); fastest-first is worse (0.69).

## 9. Failures, errors and how they were found

Fourteen entries are in `FAILURE_LOG.md`. The ones with the largest effect on conclusions: unequal tuning between optimisers (1, 2, and again for quantum vs classical in 12), a wrong shared-parameter gradient rule (7), a benchmark that biased a scheduler result (11), results text that disagreed with the numbers (10), and a wrong explanation of a weak result that was replaced after testing the hypothesis (6). Detection methods were: comparison against an independent reference, noticing a suspiciously large gap, and recomputing every number in the write-up from the raw results. Two further lessons are in the results themselves: a model that is exactly optimal can still lose to a heuristic if its assumptions fail (H), and a mechanism that works (lock contention removed) need not produce a measurable benefit (G).

## 10. Limitations

- Shared 2-core machine: timing noise of 8–15% in some measurements; no result in this report is a hardware benchmark.
- Synthetic data (E, H) and small problem sizes (C, D, I), chosen so exact answers exist; scaling statements are limited to what was tested.
- Learning rates and parameters for several experiments are on the edge of their tuning grids (A, C), so rankings between optimisers are not claimed.
- Tracks C and I are classical simulations; the noise models are synthetic.
- The cost model in F (mul = 3) is an assumption; the mutation tester in J is simple and uses 90 sampled mutants.
- The student must still be able to explain all code, including AI-generated parts, and the prompt logs contain placeholders that the student must complete with their real prompts.

## 11. Possible next steps

- E: add skills, contracts and holidays; test CP-SAT and column generation; real (anonymised) data.
- G: measure on a many-core machine or real hardware; add per-CPU statistics; try a stride scheduler for lower variance.
- H: use multi-index (pairwise) benefit estimates or what-if costing in a larger DBMS; real TPC-H data.
- I: noise models from a real device; hardware run for Grover on 2–3 qubits.
- J: more mutation operators, a second codebase, and a test-impact-analysis pipeline.
- Across tracks: repeat the key comparisons on a machine with more cores and report confidence intervals.

## 12. How to reproduce

```
pip install -r requirements.txt
python -m pytest -q --ignore=trackG_xv6        # 106 tests
python trackA_continuous/run_track_a.py        # and similarly for B, C, D, E (run_track_e.py + run_extra.py), F, H, I, J
bash trackG_xv6/build.sh && python trackG_xv6/run_track_g.py   # needs qemu-system-riscv64 and a RISC-V toolchain
```
Seeds are fixed in each script. Raw numbers are in each track's `results/results.json`.
