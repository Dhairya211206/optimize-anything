# Answers to the Final Questions (Section 11 of the assignment)

Numbers are copied from the track results files; see those for setup and caveats.

## 1. What process did you choose, and what evidence showed that it needed optimization?

Main case study (Track E): **weekly shift rostering for a manufacturing plant** (workers, three shifts, availability, rest rules). The data are synthetic, so the evidence is from the baseline we built, not from a real plant: a day-by-day greedy roster ended **24.5% to 26.8% above the proven optimum** in preference-plus-fairness cost at every size from 20 workers × 7 days to 150 × 28 days. The fixed-domain tracks each had their own baseline: stock xv6 (500k failed lock attempts, equal-share round-robin), SQLite with no indexes, the unoptimised compiler IR, and the full 12.2 s test suite (one test is 51% of it).

## 2. How did you formulate the objective function and constraints?

Rostering: binary `x[w,d,s]`; minimise total preference cost + λ(Lmax − Lmin); constraints: coverage per shift, one shift per day, availability, at most 5 shifts per 7 days, no morning after night, and workload bounds linking to Lmax/Lmin. It is a 0-1 ILP, checked against brute force on tiny instances. Other formulations: Max-Cut and feature selection as QUBO/Ising (Track B), register allocation as a 0-1 ILP over live intervals (F), index selection with `y_i`, `x_qi` and a storage budget (H), test minimisation as weighted set cover (J), and the xv6 changes as constrained design problems (no memory lost, no lock held twice).

## 3. Which Chapter 6 methods did you test, and why were they appropriate?

See `CHECKLIST.md` for the full map. Examples: gradient descent family, momentum, NAG, AdaGrad, RMSProp, Adam, Newton and Gauss-Newton on convex, non-convex and noisy objectives (A); knapsack by greedy/DP/branch-and-bound/ILP and annealing/hill climbing on QUBOs (B); QAOA, VQE, SPSA, parameter-shift, shots, noise and barren plateaus (C); submodular greedy and lazy greedy, Amdahl/Gustafson, load balancing, pipeline/model parallelism, FedAvg, MGDA and GradNorm (D); and Deutsch-Jozsa, Bernstein-Vazirani, Grover, QFT, QPE, Shor and QML (I). Each method was used on a problem whose structure it suits and, where a guarantee exists, its conditions were checked first (e.g. submodularity was tested numerically; the guarantee was not applied to the non-monotone and non-submodular objectives).

## 4. How did the optimized solution compare with the baseline?

- Rostering: exact ILP optimal in 0.04–0.73 s; greedy 24.5–26.8% worse; annealing 6.7–26.8% worse.
- Compiler: weighted cost ratio 0.467 (geometric mean; part of it is the assumed mul = 3 cost; dynamic instructions 0.596); ILP register allocation cuts spill traffic 33% vs linear scan.
- xv6: lock contention eliminated, **run time unchanged within noise**; lottery scheduling tracks tickets (69.6% for 70%), but is less fair than round-robin for equal tickets.
- SQLite: best speedup about 1.5x; the exact ILP did worse than no index at larger budgets (0.38x) until planner harm was modelled (1.47–1.55x).
- Tests: −55% test time at equal line coverage, losing 4–10% of killed mutants.
- QML/quantum: no advantage over classical; Grover's oracle-call saving is real in the query model but not in simulated wall-clock.

## 5. What trade-offs, failures, or limitations did you discover?

Exact methods can beat clever heuristics when the problem is linear (E), but an exactly optimal solution of an *approximate* model can fail in reality (H). A working mechanism need not give speed (G allocator). Fairness and speed trade off in scheduling (G lottery). Pass benefits depend on the cost model (F). Minimising a test suite by coverage loses fault detection (J). Quantum algorithms save queries but not wall-clock on a simulator, and QML loses to a tuned RBF-SVM (I). Limits: synthetic data, 2-core noisy machine, small sizes, simulators only. Failures are in `FAILURE_LOG.md` (14 entries).

## 6. What evidence demonstrates that your results are correct and reproducible?

106 automated tests: optimisers vs finite differences; knapsack/ILP/rostering vs brute force; QUBO energy equals minus cut for every assignment; PennyLane cross-checks of the quantum simulators; a three-way differential fuzz of the compiler (0 mismatches in 400 programs × 7 configurations); identical query result hashes in every SQLite configuration; `usertests -q` and the same obtainable-page count on stock and modified xv6; the xv6 patch applies cleanly to upstream. Fixed seeds, repeated runs with standard deviations, raw numbers in each `results/results.json`, and commands in the report (section 12). The first biased benchmark runs are kept for transparency (e.g. `results_first_run.json`).

## 7. How could the optimization approach be adapted if the scale, data, constraints, or hardware changed?

- Larger rosters or richer rules: the ILP scaled to 50,400 binaries in 1.8 s here, but real constraints (skills, contracts) may need CP-SAT, decomposition/column generation, or ILP-warm-started annealing.
- Different data: re-measure; the H results show benefits are workload- and planner-specific, so index benefits must be re-measured and checked for harm.
- More cores/hardware: re-run the xv6 and parallel experiments; contention effects that vanished under emulation may appear on real many-core machines; Amdahl-style fits must be refitted.
- Quantum hardware: the noise results show circuit depth must stay small; this would need a calibrated noise model and shot budgets.
- Tight time limits: greedy/lazy greedy for submodular objectives (with the guarantee only when its conditions hold).

## 8. For the compiler, xv6 and DBMS tracks: what did you implement, what OS/database concept did you learn, and how was correctness preserved?

- **Compiler (F):** constant folding, strength reduction, copy propagation, CSE, LICM, DCE and register allocation by linear scan, greedy and exact ILP. Concept: passes enable each other and gains depend on the cost model; register allocation is an interval-covering optimisation. Correctness: differential testing vs a reference interpreter, 0 mismatches in 400 programs × 7 configurations, LICM hazard tests.
- **xv6 (G):** a per-CPU free-list allocator with batch stealing and a lottery scheduler with a `settickets` syscall. Concepts: spinlock contention (holding only one lock at a time to avoid deadlock) and proportional-share scheduling. Correctness: `usertests -q` passes on all four builds, same obtainable-page count (32,469), patch applies to upstream.
- **DBMS (H):** index selection with greedy, knapsack DP, exact ILP and a harm-aware ILP on SQLite. Concepts: indexes trade storage for read speed; the optimizer's plan choice (EXPLAIN QUERY PLAN) decides whether an index helps or hurts; benefits are not additive. Correctness: identical result hashes for all 12 queries in every configuration.

## 9. What advantages and limits of QML, quantum algorithms and parallel computing did your experiments reveal compared with classical computing?

- **Quantum algorithms (simulated):** query reductions are real in the oracle model (Grover 3 to 804 calls vs (N+1)/2; 2.8x to 652x), and BV needs one query vs n. But classical randomized DJ needs few queries, the simulator costs 2^n so wall-clock was slower (2.1 s vs 28 ms at n = 20), Shor was only tested on N up to 77 with an oracle-level arithmetic step, and synthetic noise erased Grover's advantage by p = 0.1.
- **QML (simulated):** QNN 0.948 ± 0.024 vs RBF-SVM 0.945 ± 0.018 on moons (16 parameters, about 396k circuit runs vs none); on circles RBF 0.993 beats QNN 0.974 and kernel 0.979. Barren plateaus (Track C: gradient variance falls about 3x per qubit with a global cost) and data loading add trainability limits.
- **Parallel computing (measured, 2 cores):** 1.66x with 2 workers (efficiency 0.83), no gain from oversubscription (1.53x with 4); granularity and load balance decide whether dynamic scheduling helps; FedAvg trades communication for local work. Beyond 2 workers, results are labelled simulation.
- No quantum or parallel speedup is claimed beyond what these timings support.

## 10. Which AI tools did you use, how did their outputs differ, and which AI-generated errors did you find and fix?

- **Tools:** Claude (Claude Sonnet 5.5) generated and tested the code and documents for all tracks. Antigravity (Gemini 3.8 Flash, medium) was used for the tool-comparison task only: both tools got the same Max-Cut QUBO/Ising/annealing prompt (`TOOL_COMPARISON.md`). Both produced a correct formulation (best cut 13, 8 optimal assignments, annealing 50/50 on their own seed-7 graph). Claude's first draft had an annealer energy-update bug that an extra consistency test caught (3 of 4 tests passed, 8/50 optimum hits before the fix); Antigravity's file passed its 3 tests on its first run and again when I re-ran it. One task and one run per tool is too small a sample to say more. Per its execution log, Antigravity took 5 min 54 s from request to passing tests with 0 follow-up prompts and no edits.
- **Errors found and fixed** (full detail in `FAILURE_LOG.md`): unfair optimiser tuning (1, 2); invalid code (3); a library API written from memory (4); a wrong assumption written into a test (5); a wrong explanation for a weak annealing result (6); an invalid parameter-shift rule on a shared QAOA parameter (7); tests assuming convergence that the optimiser could not reach (8); train/test data drawn from different seeds (9); results text that did not match the numbers (10); a scheduler benchmark biased by staggered process start (11); an unfairly tuned quantum kernel versus a tuned RBF (12); a classical-search comparison that used a random marked item (13).
