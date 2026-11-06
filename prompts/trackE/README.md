# Track E: Main Case Study (Plant Shift Rostering) — Prompt Log

**Tool:** Claude (claude.ai), Claude Sonnet 5.5 | **Date:** 2026-11-04  
**Track Focus:** Real-World Operational Process Optimization, Constrained Scheduling, Strategy-Selection Framework, and Scalability

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert operations research and industrial optimization engineer. Implement Track E (Main Real-Process Case Study) of Assignment 8 following the mandatory Section 4 and Section 8 vibe-coding methodology.

1. Process Discovery & Domain Selection:
   - Domain: Weekly Shift Rostering for a Manufacturing Plant (workers, three shifts, worker availability, rest rules).
   - Process Bottleneck: A day-by-day greedy construction baseline finishes 24.5% to 26.8% above the proven optimal cost in preference-plus-fairness penalty across instances from 20 workers × 7 days up to 150 workers × 28 days.

2. Problem Formulation:
   - Decision Variables: Binary assignment tensor x[w, d, s] in {0, 1}, indicating whether worker w is assigned to shift s on day d.
   - Hard Constraints (Mandatory Feasibility):
     * Shift Coverage: Exactly required staffing R_{d, s} for each shift.
     * Single Shift per Day: sum_s x[w, d, s] <= 1 for all w, d.
     * Worker Availability: x[w, d, s] = 0 if worker w is unavailable for shift (d, s).
     * Minimum Rest: Night shift on day d prohibits morning shift on day d+1.
     * Maximum Shifts: At most 5 working shifts per 7-day rolling window.
   - Soft Constraints & Objective Function to Minimize:
     * Minimize total preference cost + lambda * (L_max - L_min), where L_max and L_min are the maximum and minimum shift counts across workers to enforce fair distribution.

3. Strategy Selection Table:
   - Provide a formal strategy-selection table:
     * Variable type: Pure binary 0-1 integer variables.
     * Problem size: Micro (4 workers x 3 days) to Large (150 workers x 28 days = 12,600 vars).
     * Solvability: NP-hard combinatorial problem with tight coupling.
     * Algorithm suitability: Exact ILP vs Greedy Construction vs Metaheuristic Annealing.

4. Algorithm Selection & Implementation:
   - Baseline: Naive Greedy Constructive Heuristic (fills shifts greedily by worker availability).
   - Local Search / Metaheuristic: Simulated Annealing with specialized neighborhood moves (shift swapping, unassigned replacement).
   - Exact Solver: Integer Linear Programming (ILP) using `scipy.optimize.milp` with linearized cost and constraint matrices.

5. Verification & Testing:
   - Write pytest tests (`test_track_e.py`):
     * Verify that ILP finds the exact global optimum on micro-instances against brute-force search.
     * Verify that constraint violation detectors reliably trigger on invalid test schedules.
     * Verify that the incremental delta evaluation used in Simulated Annealing matches full re-evaluation after 500 stochastic moves.

6. Fair Benchmarking & Critical Review:
   - Benchmark across 16 problem instances up to 150 workers × 28 days.
   - Report: Wall-clock solve time, preference cost, fairness spread (L_max - L_min), and optimality gap.
   - Findings: Exact ILP solves all instances to proven optimality in 0.04–0.73s; greedy is 24.5% to 26.8% above optimum; annealing is 6.7% to 26.8% above optimum.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `roster.py` (instance generator, constraint checker, greedy builder, simulated annealing, ILP formulation), `test_track_e.py`, `run_track_e.py`, and `TRACK_E_RESULTS.md`.
* **Revisions during session:**
  1. Simulated Annealing initially converged to the greedy baseline on large scales due to insufficient cooling iterations; extended search budget and tuned initial temperature to achieve genuine improvement.
  2. The exact ILP solved medium instances (2,100 variables) in under 1 second. Pushed scaling to a stress instance (600 employees x 28 days = 50,400 variables) to empirically determine the memory and runtime crossover point.

---

## Verification Note

* **6 pytest tests pass** (`python -m pytest trackE_case_study -q`).
* Exact solver matches exhaustive combinatorial enumeration on all 4 micro-test instances.
* Zero hard constraint violations achieved by ILP across all benchmark configurations.
* Strategy selection matrix and scaling results fully documented in `TRACK_E_RESULTS.md`.
