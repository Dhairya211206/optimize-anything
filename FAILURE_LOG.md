# Failure Log

Record at least three cases where AI-generated code was wrong, unsafe, inefficient or misleading. Only record failures that actually happened in this project. Do not invent entries.

## Entry template

- **Track:**
- **Tool / model:**
- **Prompt (short):**
- **What went wrong:**
- **How it was detected:**
- **Fix (commit link):**
- **Lesson:**

---

## Entries

Candidates from Track A. Confirm each in your own words and with your own commit link before keeping it. These happened in the Claude session on 2026-11-04.

### Candidate 1: unfair optimizer comparison

- **Track:** A
- **Tool / model:** Claude Sonnet 5.5
- **What went wrong:** The first MLP experiment used hand-picked learning rates, so GD looked clearly worse than Adam, RMSProp and AdaGrad. The comparison was misleading because only GD was poorly tuned.
- **How it was detected:** Review against the assignment's fairness rules (same tuning rule for every method).
- **Fix:** Tune every method on one shared learning-rate grid, then compare. After tuning, the full-batch methods are essentially tied (train loss 0.1117 to 0.1126).
- **Lesson:** An optimizer ranking is only meaningful if each optimizer is tuned the same way.

### Candidate 2: tuning that favoured one start point

- **Track:** A
- **What went wrong:** The tuner chose AdaGrad lr = 3.0 on the quadratic, giving a final f of about 1e-224. That value came from a lucky first step from one start point, not from a better algorithm.
- **How it was detected:** The value was below any meaningful precision.
- **Fix:** Added an iterations-to-tolerance metric and wrote the caveat into `TRACK_A_RESULTS.md`.
- **Lesson:** Do not rank methods on final values already at float precision.

### Candidate 3: invalid code

- **Track:** A
- **What went wrong:** The generated metric edit used `iters_to_1e-6=` as a keyword argument, which is a syntax error. The first rerun silently produced no new results, and stale results from the previous run were still on disk.
- **How it was detected:** A KeyError when reading the results, then reading the run output.
- **Fix:** Renamed to `iters_to_tol_1e6`.
- **Lesson:** Check that a run actually succeeded before reading its output files.

### Candidate 4: library API written from memory (Track B)

- **Track:** B
- **Tool / model:** Claude Sonnet 5.5
- **What went wrong:** The first ILP code used the PuLP/CBC API as remembered (`LpVariable(..., cat="Binary")`). The installed PuLP 4.2.0 has a different constructor and reported no available solver, so the code raised a TypeError.
- **How it was detected:** Test run (`test_exact_knapsack_solvers_agree_with_brute_force` failed).
- **Fix:** Switched all ILPs to `scipy.optimize.milp` (HiGHS), which is already installed.
- **Lesson:** Check the installed version's API before using it.

### Candidate 5: wrong assumption written into a test (Track B)

- **Track:** B
- **What went wrong:** The test asserted that with penalty 0 the QUBO optimum would break the "exactly k features" constraint. For k=4 it does not (the optimum happens to have 4 features).
- **How it was detected:** The test failed.
- **Fix:** The test now asserts only that a large penalty enforces the constraint. The penalty sweep measures the real behaviour: for k=6, penalties of 0.1 or less violate it and 0.25 or more satisfy it.
- **Lesson:** Do not assert an expected failure that depends on the data. Measure it.

### Candidate 6: wrong explanation for a weak result (Track B)

- **Track:** B
- **What went wrong:** Simulated annealing reached the feature-selection optimum in only 10 to 17% of runs, and the first explanation was a temperature-scale mismatch. A sensitivity test contradicted this: lowering the start temperature made it worse, and 2000 sweeps at the default temperature reached 77%.
- **How it was detected:** Running the sensitivity test before writing the claim.
- **Fix:** The write-up says the cause is search budget, not temperature scale.
- **Lesson:** Test an explanation before reporting it.

### Candidate 7: invalid parameter-shift on a shared parameter (Track C)

- **Track:** C
- **What this is:** A known pitfall, implemented on purpose as a negative control. In QAOA, `gamma` drives 18 gates at once. Shifting it by plus or minus pi/2 as a whole (the "naive" rule) gives a wrong gradient (error 4 to 5 against finite differences), while shifting each gate and summing matches finite differences to 4e-9. `test_track_c.py` checks both.
- **Only keep this entry if it fits your own story:** if you did not make this mistake yourself, list it as a verification result instead, not as an AI failure.

### Candidate 8: tests assumed convergence that the optimizer could not reach (Track D)

- **Track:** D
- **Tool / model:** Claude Sonnet 5.5
- **What went wrong:** The multi-task training test failed. The generated data had a target mean of about 15 for task 2, and Adam moves a bias by at most the learning rate per step, so 200 steps could never fit it. The first guess (a bug in the weighting code) was wrong.
- **How it was detected:** The test failed; checking the relative error per task showed the problem was in the data scale.
- **Fix:** Centred the targets in `make_data` (keeping the 25x scale difference between tasks) and used 400 steps.
- **Lesson:** When a test fails, check the data and the optimizer's limits before blaming the algorithm under test.

### Candidate 9: train and test data drawn with different seeds (Track D)

- **Track:** D
- **What went wrong:** The first draft of the multi-task experiment drew the test set with a different seed than the training set. In `make_data` the seed also sets the two tasks' hidden directions, so test data would have come from a different problem. The dead lines were overwritten by a correct split before use, so no reported number was affected.
- **How it was detected:** Re-reading the experiment code before trusting its output.
- **Fix:** Train and test now come from one draw split in half.
- **Lesson:** Read generated experiment code for data leakage and mismatch, even when the numbers look reasonable.

### Candidate 10: results text that did not match the numbers (Track F)

- **Track:** F
- **What went wrong:** The first draft of `TRACK_F_RESULTS.md` said linear scan was "28% to 4 times worse" than the ILP on `nested_loops`. The measured values are 22% worse at K=2 and 12 times worse at K=8.
- **How it was detected:** Recomputing every ratio in the text from `results.json` before delivering.
- **Fix:** Corrected the sentence.
- **Lesson:** Check each sentence in a results write-up against the raw numbers.

### Candidate 11: biased scheduler benchmark (Track G)

- **Track:** G
- **What went wrong:** The first `schedbench` forked its children from a 1-ticket parent, so the last (70-ticket) child started much later than the others. The lottery scheduler appeared to give it only 61.9% instead of about 70%, and the 3-way error looked like 6.1 points.
- **How it was detected:** The 1:2:4 case matched the ideal but 10:20:70 did not, which pointed at the benchmark rather than the scheduler; reading the startup order confirmed the stagger.
- **Fix:** Children now block on a pipe and are released together with a shared absolute deadline. The corrected share is 69.6% (error 2.6 points). The first run is kept in `results/results_first_run.json`.
- **Lesson:** When a benchmark disagrees with theory, check the harness before blaming the algorithm.

### Candidate 12: unfair quantum-vs-classical comparison (Track I)

- **Track:** I
- **What went wrong:** The first quantum-kernel SVM used a fixed feature scale and C while the classical RBF SVM was tuned over a grid. The quantum kernel scored about 0.77 on moons and circles, roughly 15 points below the RBF, which would have been reported as "quantum is worse".
- **How it was detected:** The gap was suspiciously large and the setups were not symmetric in tuning effort.
- **Fix:** Tuned the feature scale (5 values) and C with the same 3-fold cross-validation budget as the RBF grid. The gap shrank to within about 2 points (moons 0.927 vs 0.945).
- **Lesson:** Give the quantum and classical models the same tuning budget before comparing them.

### Candidate 13: classical-search comparison used a random marked item (Track I)

- **Track:** I
- **What went wrong:** The Grover scaling run searched a randomly placed marked item, so the classical scan count in one run (e.g. 9 vs 8.5 expected) varied with luck, and the reported call ratio was noisy.
- **How it was detected:** Reading the first table: the classical call count was not the expected (N+1)/2.
- **Fix:** Put the marked item at N/2 for both searches and report the expected classical count (N+1)/2 and worst case N alongside.
- **Lesson:** Compare expected cost, not one lucky draw.

### Candidate 14: annealer energy update off by a factor (tool-comparison task)

- **Track:** B (tool comparison, `tool_comparison/claude/`)
- **Tool / model:** Claude Sonnet 5.5
- **What went wrong:** In the first draft of the Max-Cut annealer, the incremental energy change for a bit flip used `Q_kk * d^2` instead of `Q_kk * d` (d = ±1), so the tracked energy drifted away from the true energy and the search was misled (8 of 50 runs reached the optimum instead of 50 of 50). The comment above the formula was also muddled.
- **How it was detected:** An extra test that the annealer's reported energy equals the QUBO energy of the vector it returns failed (−6122 vs −8).
- **Fix:** Corrected the delta formula and rewrote the comment; all 4 tests pass and 50/50 runs reach the optimum.
- **Lesson:** When using incremental updates, test them against a full recomputation.

