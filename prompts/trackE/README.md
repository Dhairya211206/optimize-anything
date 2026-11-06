# Track E: Main Case Study (Workforce Shift Rostering) — Prompt Log

**Tool:** Claude (claude.ai), Claude 3.5 Sonnet | **Date:** 2026-11-04  
**Track Focus:** Real-World Operational Process Optimization, Constrained Scheduling, Strategy-Selection Framework, and Scalability

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert operations research and industrial optimization engineer. Implement Track E (Main Real-Process Case Study) of Assignment 8 following the mandatory Section 4 and Section 8 vibe-coding methodology.

1. Process Discovery & Domain Selection:
   - Domain: Healthcare / Emergency Service Workforce Shift Rostering.
   - Process Bottleneck: Manual scheduling consumes significant administrative hours and frequently produces suboptimal schedules with unfair overtime distribution, nurse fatigue, and hard constraint violations.

2. Problem Formulation:
   - Decision Variables: Binary assignment tensor x_{e, d, s} in {0, 1}, indicating whether employee e is assigned to shift s on day d.
   - Hard Constraints (Mandatory Feasibility):
     * Coverage: Exactly required staffing R_{d, s} for each shift.
     * Single Shift per Day: sum_s x_{e, d, s} <= 1 for all e, d.
     * Minimum Rest: Night shift on day d prohibits morning shift on day d+1.
     * Maximum Consecutive Shifts: No more than 6 consecutive working days.
   - Soft Constraints (Objective Function to Minimize):
     * Overtime Penalties: Quadratic penalty for total hours exceeding standard weekly quotas.
     * Weekend Imbalance: Deviation in weekend shifts across staff.
     * Employee Preference Violations: Negative penalty for assigning disliked shifts.

3. Strategy Selection Table:
   - Provide a formal strategy-selection table:
     * Variable type: Pure binary integer variables.
     * Problem size: Small (15x7x3 = 315 vars), Medium (50x14x3 = 2,100 vars), Large (150x28x3 = 12,600 vars).
     * Solvability: NP-hard combinatorial problem with tight coupling.
     * Algorithm suitability: Exact ILP vs Greedy Construction vs Metaheuristic Annealing.

4. Algorithm Selection & Implementation:
   - Baseline: Naive Greedy Constructive Heuristic (fills shifts greedily by availability).
   - Local Search / Metaheuristic: Simulated Annealing with specialized neighborhood moves (shift swapping, unassigned replacement).
   - Exact Solver: Integer Linear Programming (ILP) using `scipy.optimize.milp` with linearized cost and constraint matrices.

5. Verification & Testing:
   - Write pytest tests (`test_track_e.py`):
     * Verify that ILP finds the exact global optimum on micro-instances against brute-force search.
     * Verify that constraint violation detectors reliably trigger on invalid test schedules.
     * Verify that the incremental delta evaluation used in Simulated Annealing matches full re-evaluation after 500 stochastic moves.

6. Fair Benchmarking & Critical Review:
   - Benchmark across Small, Medium, and Large problem instances.
   - Report: Wall-clock solve time, hard constraint violation count, soft objective penalty score.
   - Discuss computational limits: analyze the scale threshold where exact ILP becomes intractable compared to Simulated Annealing.
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
