# Track B: Discrete Optimization & QUBO/Ising — Prompt Log

**Primary Tool:** Claude Sonnet 5.5 | **Comparison Tool:** Google Antigravity (Gemini 3.8 Flash)  
**Date:** 2026-11-04 (Track implementation), 2026-11-05 (Tool comparison)  
**Track Focus:** Combinatorial Optimization (Exact vs Heuristic), QUBO/Ising Formulations, Constraint Penalties, and Annealing

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert combinatorial optimization engineer. Implement Track B (Discrete Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Problem Formulation:
   - Formulate two complementary discrete optimization problems:
     a) 0/1 Knapsack Problem: Given n items with profits p_i and weights w_i, find binary selection x in {0, 1}^n maximizing sum(p_i * x_i) subject to capacity constraint sum(w_i * x_i) <= W.
     b) Max-Cut Graph Partitioning & Feature Selection as QUBO / Ising:
        - Max-Cut: partition graph vertices V to maximize cut edges, formulated as QUBO: min x^T Q x with Q = A - diag(d) = -L.
        - Binary-to-Spin Transformation: derive Ising Hamiltonian E(s) = 0.5 * s^T J s + h^T s + offset via x_i = (s_i + 1) / 2.
        - Constraint Penalties: Feature selection minimizing prediction residual subject to cardinality constraint sum(x_i) = k using quadratic penalty lambda * (sum(x_i) - k)^2.

2. Algorithm Selection (Chapter 6 Syllabus):
   - Classical Discrete Methods:
     * Greedy Heuristic (value-to-weight ratio).
     * Dynamic Programming (exact pseudopolynomial table).
     * Branch-and-Bound (exact tree search with linear relaxation bounds).
     * Integer Linear Programming (ILP via standard solver).
   - QUBO/Ising Solvers:
     * Brute-Force Exhaustive Enumeration (for all 2^n states on n <= 20).
     * Classical Simulated Annealing with geometric cooling.
     * Local Search / Hill Climbing with 1-bit flip neighborhoods.

3. Implementation Details:
   - Pure Python with NumPy and SciPy (`scipy.optimize.milp`).
   - Modular structure: `discrete.py`, `qubo.py`, `test_track_b.py`, `run_track_b.py`.
   - Maintain deterministic random seeds across all graph generations and item sets.

4. Verification & Testing:
   - Write pytest tests:
     * Verify DP, Branch-and-Bound, and ILP all yield identical optimal values and match Brute-Force on small random instances.
     * Verify that QUBO energy equals -Cut(x) for EVERY one of the 2^n states.
     * Verify that Ising energy equals QUBO energy for EVERY one of the 2^n states.
     * Verify that penalty term lambda sweeps enforce the exact cardinality k on feature selection.

5. Fair Benchmarking & Critical Review:
   - Compare optimality gap, runtime scaling with problem size n, and memory footprint.
   - Investigate failure modes: DP memory blow-up with large non-integer weights; Simulated Annealing search-budget sensitivity.
```

---

## Tool-Comparison Benchmark Prompt (Executed on Claude & Antigravity)

On 2026-11-05, a rigorous, self-contained prompt was given to both **Claude Sonnet 5.5** and **Gemini 3.8 Flash (via Google Antigravity)** to evaluate code generation, mathematical derivation, and one-shot correctness:

```
Write a Python 3 file maxcut_qubo.py (numpy only) that does the following.

1. Build a random undirected graph with 8 nodes and 18 edges, using a fixed seed of 7.
2. Formulate Max-Cut as a QUBO: minimise x^T Q x with x_i in {0,1}. Return Q.
3. Convert the QUBO to Ising form (spins s_i in {-1,+1}), returning J, h and the constant offset.
4. Solve by brute force over all 2^8 assignments and report the best cut value.
5. Solve by simulated annealing (fixed seed, 50 runs) and report how many of the 50 runs reach the brute-force optimum.
6. Write pytest tests that check: (a) for EVERY one of the 256 assignments, the QUBO energy equals minus the cut value; (b) the Ising energy equals the QUBO energy for every assignment; (c) the annealer never returns an assignment that is not a valid 0/1 vector.

Run the tests and show the output. Do not use any libraries other than numpy and pytest. Explain your formulas in comments. If any test fails, fix the code and say what was wrong.
```

### Tool Comparison Outcome:
* **Google Antigravity (Gemini 3.8 Flash):** Passed all 3 pytest tests on its **first attempt** (`3 passed in 1.65s`) with zero errors, producing an exact mathematical formulation of $Q = A - \text{diag}(d)$ and $E_{\text{Ising}}(s)$.
* **Claude Sonnet 5.5:** First draft suffered an incremental energy-update bug in the annealer flip loop (Failure Log #14), requiring a prompt revision before passing all tests.
* Full detailed analysis: See [`TOOL_COMPARISON.md`](../../TOOL_COMPARISON.md).

---

## Session Execution Summary

* **Scaffolding:** Developed `discrete.py`, `qubo.py`, `test_track_b.py`, `run_track_b.py`, and `TRACK_B_RESULTS.md`.
* **Revisions during session:**
  1. Replaced `pulp` with `scipy.optimize.milp` to avoid external binary solver dependency issues.
  2. Fixed a feature-selection penalty test where $\lambda = 0$ happened to satisfy cardinality $k=4$ by coincidence; updated test to sweep $\lambda \in [0.1, 100.0]$ showing constraint enforcement.
  3. Added an annealing search-budget sensitivity sweep to demonstrate that run-budget, rather than temperature schedule, dictated convergence probability.

---

## Verification Note

* **10 pytest tests pass** (`python -m pytest trackB_discrete -q`).
* Exact equivalence verified: $\text{DP} = \text{Branch-and-Bound} = \text{ILP} = \text{Brute Force}$ on all 12 test instances.
* $E_{\text{QUBO}}(x) = -\text{Cut}(x)$ and $E_{\text{Ising}}(s) = E_{\text{QUBO}}(x)$ verified for all 256 states.
