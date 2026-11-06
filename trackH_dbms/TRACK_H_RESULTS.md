# Track H: Database Optimization (Index Selection), Results

**Data are synthetic.** `tpch_like.py` generates a TPC-H-*like* schema (region, nation, supplier, customer, part, orders, lineitem) at scale factor 0.1 with a fixed seed. It is not the official TPC-H dbgen output and results are not comparable to published TPC-H numbers. DBMS: SQLite (version of the Python standard library), default planner with automatic indexes on. Timing = minimum of 3 runs after warm-up on a shared 2-core machine, so differences of about 0.03 s on the whole workload are noise (a repeat of the selection step reproduced every speedup within that). Numbers come from `python trackH_dbms/run_track_h.py` (about 3 minutes) and are in `results/`.

## Dataset and workload

| Item | Value |
|---|---|
| Rows | region 5, nation 25, supplier 1,000, customer 15,000, part 20,000, orders 150,000, lineitem 600,487 |
| Database file | 36.8 MB |
| Workload | 12 weighted queries: 8 TPC-H-style analytical queries (Q1, Q3, Q4, Q5, Q6, Q10, Q12, Q14, weights 1 to 3) and 4 frequent point queries (weights 10 to 20) |
| Candidate indexes | 25 (single and composite), total size 101.7 MB if all are built |
| Baseline workload time (weighted, no indexes) | about 0.74 to 0.75 s |

## Formulation

- Variables: `y_i` = index i is built; `x_qi` = query q uses index i.
- Parameters: `B[q,i]` = measured time saved on query q when only index i exists (clipped at 0 in the base model); `w_q` query weight; `size_i` measured bytes (SQLite `dbstat`).
- Objective: maximise `sum_q w_q sum_i B[q,i] x_qi`.
- Constraints: each query uses at most one index (`sum_i x_qi <= 1`), `x_qi <= y_i`, storage `sum_i size_i y_i <= budget`.
- Budgets: 5, 10, 20, 40% of the total candidate size (5, 10, 20, 41 MB).
- **Modelling assumption:** benefits are measured one index at a time and the best index wins per query. Real planners choose plans by their own cost estimates, and indexes interact.

## Methods compared (Chapter 6 techniques plus the default optimizer)

| Method | What it is |
|---|---|
| Default planner, no indexes | the baseline (speedup 1.00) |
| Greedy by benefit/size ratio | additive benefit per byte (knapsack greedy) |
| 0/1 knapsack DP | exact for the additive-benefit approximation, sizes rounded up to 1/2000 of the total |
| Greedy with marginal gain | re-evaluates the model benefit after each pick |
| Exact ILP | HiGHS via `scipy.optimize.milp` on the formulation above |
| ILP, harm-aware (our extension) | same ILP plus a penalty `w_q * harm[q,i]` for each built index that slowed query q by more than 3 ms and 10% when measured alone |
| All 25 indexes (control) | storage 101.7 MB |

## Measured results (workload speedup over no indexes; results identical in every case)

| Budget | Greedy ratio | Knapsack DP | Greedy marginal | ILP | ILP harm-aware |
|---|---|---|---|---|---|
| 5% (5 MB) | 1.50x | 1.47x | 1.52x | 1.47x | 1.48x |
| 10% (10 MB) | 1.51x | 1.41x | 1.13x | 1.48x | 1.43x |
| 20% (20 MB) | 1.26x | 1.25x | **0.47x** | **0.38x** | 1.55x |
| 40% (41 MB) | 0.92x | 0.92x | **0.52x** | **0.52x** | 1.47x |
| All 25 indexes | 0.93x | | | | |

(Values are from the second run of the selection step; the first run gave the same picture within about 0.05x, for example ILP 0.40x at 20%.)

- **Identical results:** every configuration returns the same result hash as the no-index run for all 12 queries (float values normalised before hashing). Also covered by a test that checks random index sets.
- **Gain is modest and has a sweet spot.** The best measured speedup is about 1.5x, reached already at 5 MB (5% of the candidate size). More storage does not help.
- **Building every index makes the workload slower (0.93x),** which shows that more indexes is not better.

## The main finding: the exact ILP is optimal for the model, not for the database

Predicted saving for the ILP at the 20% budget was 0.38 s, but the measured workload was about 1.1 s *slower*. The model's solution is exactly optimal (confirmed against brute force on small instances and proven optimal by HiGHS), but its assumptions failed:

- **Q1** (full aggregate on lineitem): with `li_shipmode_shipdate` present, the plan changed from `SCAN lineitem` to a non-covering index search followed by row lookups, which took 872 ms vs 152 ms. **Q6** went from 34 ms to 135 ms the same way. **Q5** went from 27 ms to 459 ms after the planner switched join order using `o_custkey_orderdate` and `s_nationkey` and an automatic customer index.
- The base model clips measured regressions at 0 and assumes each query uses the *best* index. A real planner can choose a bad plan when a new index looks attractive to its cost estimate. Greedy-ratio and knapsack DP happened to avoid the harmful index; greedy-marginal and the ILP optimised the model more tightly and walked into it.
- The harm-aware ILP charges for measured regressions and recovers (1.47x to 1.55x at all budgets, 4 indexes, 3 MB). It needs the single-index regression measurements, which cost one extra measurement run, and it is a fix for this workload, not a guarantee: pairs of indexes can still interact in ways single-index measurements miss.
- Predicted vs measured: for budgets up to 10% the model prediction (0.32 to 0.34 s) is close to the measured saving (0.22 to 0.25 s, and it over-predicts by about 30%). At larger budgets the model is wrong, as above.

Plans before and after (EXPLAIN QUERY PLAN) for every run are stored in `results/results.json`; the ILP at 20% budget is saved in full under `runs["0.20/ilp"]["plans"]`.

## Solver cost (synthetic benefit matrices)

| Candidates x queries | ILP time | Proven optimal |
|---|---|---|
| 25 x 12 | 0.01 s | yes |
| 100 x 40 | 0.4 s | yes |
| 300 x 100 | 2.2 s | yes |

At the real instance the solve times were 0.01 to 0.19 s for ILP, under 6 ms for greedy and DP. Solve time is negligible next to measuring benefits (about 100 s here), and the measurement is the real cost of the whole approach.

## Caveats

- Synthetic data, one scale factor (0.1), one machine, SQLite only. SQLite has no hypothetical-index feature, so benefits were obtained by actually building each index, not by an optimizer cost model.
- Timings are minimum of 3 runs; effects under about 0.03 s on the workload are noise.
- Candidate set and weights were chosen by us; another workload would give different numbers.
- The storage budget counts index bytes only.
- SQLite builds automatic indexes at query time when it sees fit; they are still present in the baseline, which makes the baseline stronger than a planner that cannot do this.
- Views and joins selection (named in the track brief) are not implemented; the problem solved is index selection.

## Files

`tpch_like.py`, `workload.py`, `selection.py`, `dbutil.py`, `run_track_h.py`, `test_track_h.py` (8 tests), `results/` (measured.json, results.json, index_selection.png).
