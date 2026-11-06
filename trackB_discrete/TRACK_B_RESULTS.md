# Track B: Discrete Optimization and QUBO/Ising, Results

All numbers come from `python trackB_discrete/run_track_b.py` (raw output in `results/results.json`). Correctness checks are in `test_track_b.py` (10 tests). Runtimes are wall-clock medians of 3 runs on a shared cloud VM, so treat them as indicative only.

## Problems and formulations

**0/1 knapsack.** Maximise `sum v_i x_i` subject to `sum w_i x_i <= C`, `x_i` binary. Capacity is 40% of total weight. Used to compare greedy, dynamic programming, branch-and-bound and ILP.

**Max-Cut as a QUBO.** For a graph with edge set E, `cut(x) = sum_{(i,j) in E} (x_i + x_j - 2 x_i x_j)`. Minimising `E(x) = x^T Q x = -cut(x)` gives `Q_ii = -deg(i)` and `Q_ij = +2` for each edge `i < j`. The Ising form uses `x_i = (1 - s_i)/2`, giving `J_ij = Q_ij/4`, `h_i = -Q_ii/2 - sum_j Q_ij/4`, plus a constant. Tests confirm that QUBO energy equals minus the cut value, and Ising energy equals QUBO energy, for all 256 assignments of the 8-node graph and for a random dense QUBO.

**Feature selection as a QUBO.** Choose exactly `k` of 12 features (4 informative, 4 noisy near-copies of the informative ones, 4 pure noise) to maximise relevance minus redundancy: `sum r_i x_i - alpha * sum_{i<j} R_ij x_i x_j`, where `r_i = |corr(feature_i, y)|` and `R_ij = |corr(feature_i, feature_j)|`. The constraint `sum x = k` is turned into the penalty `P (sum x - k)^2`. A test confirms the QUBO energy equals the penalised objective on random assignments.

## 1. Knapsack, 20 items (verified against brute force)

Optimum 682, capacity 448.

| Solver | Value | Gap to optimum | Runtime | Notes |
|---|---|---|---|---|
| Greedy (value/weight ratio) | 678 | 0.59% | 0.03 ms | no guarantee |
| Dynamic programming | 682 | 0 | 0.06 ms | 9,429 table cells |
| Branch-and-bound | 682 | 0 | 0.12 ms | 80 nodes |
| ILP (HiGHS) | 682 | 0 | 6.5 ms | |
| Brute force (2^20) | 682 | 0 | 198 ms | reference |

A two-item instance `(v, w) = (2, 1), (15, 10)`, capacity 10, shows greedy can be arbitrarily bad: it returns 2 while the optimum is 15. A test checks this.

## 2. Scaling and hardness (DP is the exact reference)

Uncorrelated instances:

| n | Optimum | Greedy gap | DP | B&B (nodes) | ILP |
|---|---|---|---|---|---|
| 50 | 1851 | 0.16% | 0.17 ms | 0.50 ms (439) | 41.6 ms |
| 100 | 3846 | 0% | 0.54 ms | 0.81 ms (174) | 7.9 ms |
| 200 | 7507 | 0% | 1.9 ms | 2.9 ms (483) | 11.1 ms |
| 400 | 14150 | 0.04% | 9.8 ms | 12.4 ms (2,093) | 146 ms |

Strongly correlated instances (`v = w + 10`, the classic hard case):

| n | Optimum | Greedy gap | DP | B&B (nodes) | ILP |
|---|---|---|---|---|---|
| 20 | 523 | 8.03% | 0.07 ms | 0.45 ms (511) | 21.7 ms |
| 30 | 824 | 4.37% | 0.09 ms | 0.69 ms (782) | 13.8 ms |
| 40 | 1077 | 0.37% | 0.14 ms | 0.44 ms (268) | 7.8 ms |
| 50 | 1345 | 3.42% | 0.17 ms | 16.4 ms (21,159) | 6.4 ms |

Reading it correctly:
- Greedy is near-optimal on random data but loses 3 to 8% on the correlated instances.
- B&B node counts vary a lot between instances (268 at n=40 versus 21,159 at n=50). The sizes tested are too small to show the exponential growth B&B can have, so no scaling law should be claimed from this table.
- ILP was slower than DP and B&B here. That is solver overhead on tiny instances, not a statement about ILP in general.

DP depends on the capacity value, not just the number of items (n = 50, uncorrelated):

| Max weight | Capacity | DP table cells | DP | B&B | ILP |
|---|---|---|---|---|---|
| 100 | 1,101 | 56,202 | 0.17 ms | 0.41 ms | 14.1 ms |
| 1,000 | 10,584 | 539,835 | 1.25 ms | 0.57 ms | 39.6 ms |
| 10,000 | 105,427 | 5,376,828 | 16.8 ms | 0.36 ms | 25.6 ms |

DP's table grows about 96 times with the weight scale, which is the pseudo-polynomial limit. B&B stayed fast on these particular instances, but that depends on the instance.

## 3. Max-Cut as QUBO/Ising

8-node graph (seed 7), 18 edges. This is the instance Track C reuses (`results/maxcut_instance.json`).

| Method | Cut value | Success rate (50 runs) |
|---|---|---|
| Exact (brute force over 256 assignments) | 14 | n/a (2 optimal assignments, a bitstring and its complement) |
| ILP | 14 | n/a |
| Hill climbing (1-flip local search) | 13.3 ± 0.9 | 50% reach 14 |
| Simulated annealing | 14.0 ± 0.0 | 100% reach 14 |

The Ising energy at the optimum is -14, matching the QUBO. On a 20-node graph (91 edges, exact cut 62, found by brute force over 2^20 and confirmed by ILP): hill climbing 59.4 ± 2.0 with 24% reaching the optimum, simulated annealing 100%. Annealing parameters were fixed, not tuned per graph, so 100% on these two small graphs does not carry over to larger ones.

## 4. Feature selection with a penalty term

Exact optimum (brute force over 4,096 subsets, penalty P = 2):

| k | Exact selection | Exact objective | Greedy forward selection | Greedy objective | Annealing reaches exact |
|---|---|---|---|---|---|
| 4 | features 0, 1, 2, 3 (all informative) | 1.6342 | 0, 1, 3, 6 | 1.6331 | 17% (30 runs) |
| 6 | 1, 2, 3, 4, 8, 11 | 1.3807 | 0, 1, 3, 6, 8, 11 | 1.3672 | 10% (30 runs) |

Greedy takes feature 6, a near-copy of feature 2, and ends 0.07% (k=4) and 1.0% (k=6) below optimal. Annealing always returned exactly k features but rarely the exact optimum at 200 sweeps. I first suspected the starting temperature was set for Max-Cut's larger energies. The sensitivity test said otherwise: with 2000 sweeps and the default start temperature, 77% of runs reached the optimum, while lowering the start temperature made things worse (down to 0% at 0.1). The shortfall is a search-budget issue, not a temperature-scale mismatch.

**Penalty sweep (exact QUBO optimum):**

| P | k=4: selected | k=6: selected |
|---|---|---|
| 0, 0.05, 0.1 | 4 (feasible) | 4, 5, 5 (infeasible) |
| 0.25 to 5 | 4 (feasible) | 6 (feasible) |

For k=6, penalties of 0.1 or less produce subsets that violate the cardinality constraint, and 0.25 or more enforce it. For k=4 even P = 0 happened to return 4 features. The threshold depends on the data and on k, and it is not a general constant.

## Limitations

- Instances are small, chosen so exact answers can be verified by brute force. Results on large problems are not claimed.
- Hardness of branch-and-bound is instance-dependent. The sizes tested do not show worst-case behaviour.
- Heuristic success rates (hill climbing, annealing) were measured on specific graphs and data with fixed settings.
- Branch-and-bound and DP here are simple Python implementations. Runtimes mostly reflect interpreter overhead and are not a speed ranking of the algorithms.
- Not covered: scheduling or portfolio formulations, which the assignment lists only as examples.
