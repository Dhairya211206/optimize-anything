# Track D: Submodular, Parallel, and Distributed Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude 3.5 Sonnet | **Date:** 2026-11-04  
**Track Focus:** Submodularity Guarantees, Parallel Scaling & Overhead (Amdahl's/Gustafson's Laws), Federated Learning (FedAvg), and Multi-Task Gradient Balancing (MGDA/GradNorm)

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert distributed systems and optimization researcher. Implement Track D (Submodular, Parallel, and Distributed Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Problem Formulation:
   - Part 1 (Submodular Optimization):
     * Formulate a sensor placement / maximum coverage problem.
     * Objective: f(S) = Area covered by set S of candidate sensors.
     * Prove/verify submodularity: diminishing marginal returns f(A U {e}) - f(A) >= f(B U {e}) - f(B) for A subset B.
     * Cardinality constraint: |S| <= k.
   - Part 2 (Parallel Computing Scaling):
     * Benchmark multi-core execution across varying core counts.
     * Measure speedup S(p) = T_1 / T_p and parallel efficiency E(p) = S(p) / p.
     * Fit and contrast Amdahl's Law (fixed workload) and Gustafson's Law (scaled workload).
   - Part 3 (Distributed Optimization - Federated Learning):
     * Formulate distributed training across K clients using Federated Averaging (FedAvg).
     * Decision variables: Global model parameter vector w.
     * Hyperparameters to sweep: local epochs E in [1, 10], client participation fraction C, and communication rounds R.
   - Part 4 (Multi-Task Optimization):
     * Formulate a multi-objective / two-task learning problem with competing losses L_1(w), L_2(w).
     * Implement Multiple Gradient Descent Algorithm (MGDA) using Frank-Wolfe / min-norm point algorithm on the convex hull of gradients.
     * Implement GradNorm dynamically balancing gradient norms across tasks.

2. Algorithm Selection (Chapter 6 Syllabus):
   - Submodular: Standard Greedy and Accelerated Lazy Greedy (using max-heaps). Compare against Brute-Force to verify the theoretical (1 - 1/e) ~ 63.2% approximation bound.
   - Parallel: Data parallelism, model parallelism, and task scheduling with work stealing.
   - Distributed: FedAvg vs centralized SGD.
   - Multi-Task: MGDA and GradNorm vs naive static scalarization (equal weighting).

3. Implementation Details:
   - Modular structure: `submodular.py`, `parallel_exp.py`, `federated.py`, `multitask.py`, `test_track_d.py`, `run_track_d.py`.
   - Distinguish real hardware measurements (on local CPU cores) from simulated scaling curves for large worker counts.

4. Verification & Testing:
   - Write pytest tests (`test_track_d.py`):
     * Verify submodularity diminishing returns property mathematically on random subset pairs.
     * Verify that Lazy Greedy produces identical solutions to Standard Greedy while using fewer objective evaluations.
     * Verify that parallel implementations produce numerically identical results to serial execution.
     * Verify MGDA closed-form solution matches 1D grid search on two-task gradients.

5. Fair Benchmarking & Critical Review:
   - Report honest results, including negative findings:
     * Note that model parallelism on small neural networks incurs inter-process communication overhead exceeding compute savings (negative speedup).
     * Note cases where MGDA starves one task to reach a trivial Pareto stationary point.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `submodular.py`, `parallel_exp.py`, `federated.py`, `multitask.py`, `test_track_d.py`, `run_track_d.py`, and `TRACK_D_RESULTS.md`.
* **Revisions during session:**
  1. Cleaned up redundant multiprocessing wrappers to eliminate inter-process serialization overheads.
  2. Fixed multi-task synthetic data generator where uncentered regression targets caused gradient instability (Failure Log #8).
  3. Fixed a seed synchronization mismatch between train and test splits across federated clients (Failure Log #9).
  4. Explicitly documented the limits of parallel scaling, confirming that communication overhead dominates on small model sizes.

---

## Verification Note

* **16 pytest tests pass** (`python -m pytest trackD_submodular_parallel -q`).
* Lazy Greedy achieves identical objective value to Standard Greedy with $> 70\%$ fewer function evaluations.
* Greedy approximation ratio satisfies the $(1 - 1/e)$ theoretical lower bound on all tested instances.
* Real multi-core timings accurately reflect machine physical limits; simulated cluster runs clearly designated.
