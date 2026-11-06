"""Index selection as an optimisation problem (Track H).

Variables   y_i in {0,1}   index i is built
            x_qi in {0,1}  query q uses index i (at most one index per query: the modelling assumption)
Objective   maximise  sum_q w_q * sum_i B[q,i] * x_qi        (B[q,i] = measured time saved for query q by index i alone)
Constraints sum_i x_qi <= 1 ;  x_qi <= y_i ;  sum_i size_i * y_i <= budget
Methods     greedy on additive benefit/size ratio, greedy with marginal gain under the model, 0/1 knapsack DP on the additive
            benefit, exact ILP (scipy.optimize.milp / HiGHS), brute force for small instances.
"""
import itertools

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


def model_benefit(B, w, chosen):
    """Predicted weighted saving if the set `chosen` is built (each query uses its best chosen index)."""
    if len(chosen) == 0:
        return 0.0
    return float(sum(w[q] * max(0.0, max(B[q, i] for i in chosen)) for q in range(B.shape[0])))


def additive_benefit(B, w):
    """Benefit of each index in isolation (sum over queries) - what a naive 'knapsack' formulation uses."""
    return (np.asarray(w)[:, None] * np.maximum(B, 0)).sum(axis=0)


def greedy_ratio(B, w, sizes, budget):
    ben = additive_benefit(B, w)
    order = np.argsort(-ben / np.maximum(sizes, 1e-12))
    chosen, used = [], 0.0
    for i in order:
        if ben[i] > 0 and used + sizes[i] <= budget:
            chosen.append(int(i))
            used += sizes[i]
    return chosen


def greedy_marginal(B, w, sizes, budget):
    chosen, used = [], 0.0
    while True:
        cur = model_benefit(B, w, chosen)
        best, bi = 0.0, None
        for i in range(B.shape[1]):
            if i in chosen or used + sizes[i] > budget:
                continue
            gain = (model_benefit(B, w, chosen + [i]) - cur) / sizes[i]
            if gain > best + 1e-12:
                best, bi = gain, i
        if bi is None:
            return chosen
        chosen.append(bi)
        used += sizes[bi]


def knapsack_dp(B, w, sizes, budget, unit):
    """Exact 0/1 knapsack on the additive benefit, with sizes rounded UP to multiples of `unit` (so the result is
    feasible for the true sizes)."""
    ben = additive_benefit(B, w)
    wt = [int(np.ceil(s / unit)) for s in sizes]
    cap = int(budget // unit)
    best = np.zeros(cap + 1)
    take = [np.zeros(cap + 1, bool) for _ in sizes]
    for i in range(len(sizes)):
        if ben[i] <= 0:
            continue
        for c in range(cap, wt[i] - 1, -1):
            v = best[c - wt[i]] + ben[i]
            if v > best[c]:
                best[c] = v
                take[i][c] = True
    chosen, c = [], cap
    for i in reversed(range(len(sizes))):
        if take[i][c]:
            chosen.append(i)
            c -= wt[i]
    return sorted(chosen)


def ilp(B, w, sizes, budget, time_limit=60.0, harm=None):
    """Exact ILP. `harm[q,i] >= 0` (optional) is the measured slow-down of query q when index i exists; the planner may pick
    a harmful index, so a harm-aware model charges w_q*harm[q,i] whenever i is built (a penalty, not part of the paper's basic model)."""
    nq, ni = B.shape
    nv = ni + nq * ni
    xi = lambda q, i: ni + q * ni + i
    c = np.zeros(nv)
    if harm is not None:
        c[:ni] = (np.asarray(w)[:, None] * harm).sum(axis=0)
    for q in range(nq):
        for i in range(ni):
            c[xi(q, i)] = -w[q] * max(0.0, B[q, i])
    rows = nq + nq * ni + 1
    A = lil_matrix((rows, nv))
    ub = np.zeros(rows)
    lb = np.full(rows, -np.inf)
    r = 0
    for q in range(nq):
        for i in range(ni):
            A[r, xi(q, i)] = 1
        ub[r] = 1
        r += 1
    for q in range(nq):
        for i in range(ni):
            A[r, xi(q, i)] = 1
            A[r, i] = -1
            ub[r] = 0
            r += 1
    for i in range(ni):
        A[r, i] = sizes[i]
    ub[r] = budget
    res = milp(c, constraints=LinearConstraint(A.tocsr(), lb, ub), integrality=np.ones(nv), bounds=Bounds(0, 1),
               options=dict(time_limit=time_limit, disp=False))
    chosen = [i for i in range(ni) if res.x[i] > 0.5]
    return chosen, dict(proven_optimal=bool(res.status == 0), predicted=-float(res.fun))


def brute_force(B, w, sizes, budget):
    best, bs = -1.0, []
    for r in range(B.shape[1] + 1):
        for s in itertools.combinations(range(B.shape[1]), r):
            if sum(sizes[i] for i in s) <= budget:
                v = model_benefit(B, w, list(s))
                if v > best:
                    best, bs = v, list(s)
    return bs, best
