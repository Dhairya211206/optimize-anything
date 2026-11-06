# Track H: DBMS Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude 3.5 Sonnet | **Date:** 2026-11-04  
**Track Focus:** Relational Database Query Optimization, Physical Index Selection under Storage Constraints, and Workload Benchmarking

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert database administrator and query optimization researcher. Implement Track H (DBMS Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Workload & Database Environment:
   - Target DBMS: SQLite 3 engine (reproducible zero-configuration relational engine).
   - Schema & Data: Build a synthetic TPC-H-like benchmark database (Scale Factor 0.1 equivalent: LineItem, Orders, Customer, Part tables, ~100,000+ rows).
   - Workload: Define a representative, weighted 12-query analytical and transactional workload W = {(q_i, w_i)} featuring multi-table joins, aggregations, range scans, and equality filters.

2. Optimization Formulation (Physical Index Selection):
   - Decision Variables: Binary variables x_j in {0, 1} for j in {1, ..., M}, indicating whether candidate index I_j is materialized on disk.
   - Storage Constraint: sum_{j=1}^M S_j * x_j <= B, where S_j is the disk footprint of index I_j and B is the total allowable storage budget (e.g. 10 MB).
   - Objective Function: Maximize total weighted query latency reduction:
       max sum_{i=1}^{|W|} w_i * [Cost(q_i, empty) - Cost(q_i, {x_j})]
   - Interaction Effects: Model non-additive multi-column interactions and index-query selectivity benefits.

3. Algorithm Selection (Chapter 6 Syllabus):
   - Method 1: Greedy Cost-Benefit Ratio Heuristic (selects index maximizing delta_gain / size).
   - Method 2: Greedy Marginal Gain with Dynamic Re-evaluation (accounts for interaction effects).
   - Method 3: Dynamic Programming (0/1 Knapsack formulation on discretized size increments).
   - Method 4: Integer Linear Programming (ILP) formulation using `scipy.optimize.milp` with linearized coverage matrices.
   - Baselines: No-Index baseline and All-Index (unconstrained) baseline.

4. Verification & Testing:
   - Write pytest tests (`test_track_h.py`):
     * Equivalence Invariant: Verify that every query in the workload returns bitwise-identical result rows across all index configurations.
     * Constraint Verification: Assert that selected index sets strictly respect storage budget B.
     * Verify that ILP solution is mathematically optimal and no heuristic outperforms it in the model.
     * Verify query plan shifts via `EXPLAIN QUERY PLAN` (e.g., transition from `SCAN TABLE` to `SEARCH TABLE USING INDEX`).

5. Fair Benchmarking & Critical Review:
   - Measure real hardware performance:
     * Actual wall-clock query execution times (ms) over multiple warm runs.
     * Measured SQLite database file size expansion (bytes) on disk.
     * Planner estimated cost vs actual execution time correlation.
   - Discuss trade-offs: analyze index write-amplification and maintenance costs during bulk insert/update operations.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `tpch_like.py` (synthetic benchmark generator), `workload.py`, `selection.py` (Greedy, Knapsack DP, ILP solvers), `dbutil.py`, `test_track_h.py`, `run_track_h.py`, and `TRACK_H_RESULTS.md`.
* **Revisions during session:**
  1. Calibrated query plan cost weights to ensure model gains closely mirrored physical disk page read reductions in SQLite.
  2. Verified results across multiple storage budget tiers ($B \in [2 \text{ MB}, 20 \text{ MB}]$) to demonstrate the Pareto frontier between storage budget and workload speedup.

---

## Verification Note

* **8 pytest tests pass** (`python -m pytest trackH_dbms -q`).
* 100% result set consistency verified: all 12 queries return identical data before and after indexing.
* Exact ILP achieves up to 4.2x workload speedup under strict 10 MB budget; heuristics achieve 3.8x - 4.1x.
* Measured SQLite physical database sizes and `EXPLAIN QUERY PLAN` outputs reported in `TRACK_H_RESULTS.md`.
