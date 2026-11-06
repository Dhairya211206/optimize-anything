# Track J: Software-Engineering Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude Sonnet 5.5 | **Date:** 2026-11-04  
**Track Focus:** Test-Suite Minimization (Weighted Set-Cover ILP & Greedy), Fault-Detection Prioritization (APFD), and AST Mutation Testing

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert software engineering and optimization researcher. Implement Track J (Software-Engineering Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Realistic Codebase & Target Process:
   - Target System: This assignment's own Python test and experiment repository (> 2,500 lines of non-trivial code across Tracks A through F).
   - Problem Bottleneck: Running comprehensive test suites repeatedly during development and Continuous Integration (CI) incurs high compute and time costs. Redundant test cases increase execution duration without providing incremental statement or branch coverage.

2. Optimization Formulation 1 (Test-Suite Minimization):
   - Formulation: Weighted Set-Cover Problem.
   - Decision Variables: Binary variables x_t in {0, 1} for each test case t in T, where x_t = 1 indicates test t is retained in the minimized suite.
   - Objective: Minimize total suite execution time: min sum_{t in T} c_t * x_t, where c_t is the execution duration of test t.
   - Constraints: Full Statement Coverage: sum_{t in T: e in Cov(t)} x_t >= 1 for every covered program statement e in E.
   - Algorithms to Compare:
     * Exact ILP Solver: Formulated via `scipy.optimize.milp`.
     * Greedy Set-Cover Heuristic: Iteratively picks the test case maximizing marginal statement coverage per millisecond (Chvátal heuristic).
     * Random Reduction Baseline: Randomly samples subsets of tests.

3. Optimization Formulation 2 (Test-Suite Prioritization):
   - Objective: Reorder tests to detect regressions and faults as early as possible.
   - Prioritization Heuristics:
     * Total Statement Coverage Prioritization.
     * Additional Statement Coverage Prioritization (feedback-driven dynamic coverage update).
     * Baselines: Random Ordering and Reversed Ordering.
   - Quantitative Evaluation Metric:
     * Average Percentage of Faults Detected (APFD) across AST-synthesized mutants:
       APFD = 1 - (sum_{i=1}^m TF_i) / (n * m) + 1 / (2 * n)
       where n is test count, m is detected mutant count, and TF_i is the index of the first test detecting mutant i.

4. AST Mutation Testing Harness:
   - Build a custom Python AST mutant generator (`mutate.py`):
     * Operator Replacement (+ <-> -, * <-> /).
     * Relational Inversion (< <-> <=, == <-> !=).
     * Boundary & Constant Value Mutations.
   - Execute test orderings against all synthesized mutants to evaluate empirical fault detection curves.

5. Verification & Testing:
   - Write pytest tests (`test_track_j.py`):
     * Verify that the minimized test suite retains exactly 100.0% of the statement coverage of the original test suite.
     * Verify that ILP produces a mathematically optimal minimal-duration subset.
     * Verify that Additional Coverage Prioritization strictly achieves higher APFD than Reversed Ordering on non-trivial mutation sets.

6. Fair Benchmarking & Critical Review:
   - Measure: Original vs Minimized suite duration (seconds), reduction ratio (%), retained statement coverage (%), and APFD scores.
   - Trade-Off Analysis: Discuss trade-offs between coverage retention and fault masking; discuss the computational overhead of computing coverage matrices vs CI time saved.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `collect.py` (tracing coverage and execution time), `setcover.py` (Weighted Set-Cover ILP and Greedy algorithms), `mutate.py` (AST mutation testing framework), `test_track_j.py`, `run_track_j.py`, and `TRACK_J_RESULTS.md`.
* **Revisions during session:**
  1. Automated coverage matrix collection directly via Python's `sys.settrace` to avoid external heavyweight tracer dependencies.
  2. Synthesized 50+ diverse semantic mutants across optimizer and data-structure modules to ensure high statistical confidence in APFD rankings.

---

## Verification Note

* **6 pytest tests pass** (`python -m pytest trackJ_software_eng -q`).
* Exact ILP reduces summed test suite execution time by **55%** while preserving **100.0%** statement coverage; the minimized suites lost **4% to 10%** of the mutants they could kill.
* Additional Coverage Prioritization achieves an APFD of **0.89** (most-new-lines order), significantly outperforming Random (**0.81**) and Reversed (**0.23**) orderings.
* Results and APFD fault-detection progression curves detailed in `TRACK_J_RESULTS.md`.
