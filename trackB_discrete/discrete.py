"""Exact and heuristic solvers for the 0/1 knapsack problem (Track B).

Problem:  maximize sum v_i x_i   subject to  sum w_i x_i <= C,  x_i in {0, 1}.
Integer weights are assumed (needed by the dynamic program).

Solvers, all with the same signature  solver(values, weights, cap) -> (best_value, chosen_indices, info):
  greedy  - take items by value/weight ratio while they fit. Fast, NO optimality guarantee.
  dp      - dynamic programming over capacity, O(n * C), exact (pseudo-polynomial).
  bnb     - depth-first branch-and-bound with the fractional (LP) relaxation as upper bound.
  ilp     - integer linear program solved by HiGHS through scipy.optimize.milp.
  brute   - enumerate all 2^n subsets (n <= 22). Used only to verify the others.
"""
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def make_instance(n, seed=0, kind="uncorrelated", max_w=100):
    """Random instance. 'strongly_correlated' (v = w + 10) is the classic hard case for B&B."""
    rng = np.random.default_rng(seed)
    w = rng.integers(5, max_w + 1, n)
    if kind == "uncorrelated":
        v = rng.integers(5, max_w + 1, n)
    elif kind == "strongly_correlated":
        v = w + 10
    else:
        raise ValueError(kind)
    cap = int(0.4 * w.sum())
    return v.astype(int), w.astype(int), cap


def _check(values, weights, cap):
    values, weights = np.asarray(values), np.asarray(weights)
    if values.shape != weights.shape or values.ndim != 1:
        raise ValueError("values and weights must be 1-D arrays of equal length")
    if np.any(weights <= 0) or cap < 0:
        raise ValueError("weights must be positive and capacity non-negative")
    return values, weights


def greedy(values, weights, cap):
    values, weights = _check(values, weights, cap)
    order = np.argsort(-(values / weights), kind="stable")
    total_w, total_v, chosen = 0, 0, []
    for i in order:
        if total_w + weights[i] <= cap:
            total_w += weights[i]
            total_v += values[i]
            chosen.append(int(i))
    return int(total_v), sorted(chosen), {}


def dp(values, weights, cap):
    values, weights = _check(values, weights, cap)
    n = len(values)
    table = np.zeros((n + 1, cap + 1), dtype=np.int64)
    for i in range(1, n + 1):
        wi, vi = int(weights[i - 1]), int(values[i - 1])
        table[i] = table[i - 1]
        if wi <= cap:
            table[i, wi:] = np.maximum(table[i - 1, wi:], table[i - 1, : cap + 1 - wi] + vi)
    chosen, c = [], cap
    for i in range(n, 0, -1):  # backtrack: item i was taken if the value changed
        if table[i, c] != table[i - 1, c]:
            chosen.append(i - 1)
            c -= int(weights[i - 1])
    return int(table[n, cap]), sorted(chosen), {"table_cells": int((n + 1) * (cap + 1))}


def bnb(values, weights, cap, time_limit=20.0):
    """Branch and bound. Items are sorted by ratio so the fractional relaxation is a valid
    upper bound on any completion of a partial solution."""
    values, weights = _check(values, weights, cap)
    n = len(values)
    order = np.argsort(-(values / weights), kind="stable")
    v = values[order].astype(float)
    w = weights[order].astype(float)
    best = {"val": 0, "set": []}
    nodes = [0]
    t0 = time.perf_counter()
    timed_out = [False]

    def bound(i, cur_v, room):
        b = cur_v
        for j in range(i, n):
            if w[j] <= room:
                room -= w[j]
                b += v[j]
            else:
                return b + v[j] * room / w[j]
        return b

    def rec(i, cur_v, room, chosen):
        nodes[0] += 1
        if time.perf_counter() - t0 > time_limit:
            timed_out[0] = True
            return
        if cur_v > best["val"]:
            best["val"], best["set"] = cur_v, list(chosen)
        if i == n or bound(i, cur_v, room) <= best["val"]:
            return  # prune: even the relaxation cannot beat the incumbent
        if w[i] <= room:  # branch 1: take item i
            chosen.append(i)
            rec(i + 1, cur_v + v[i], room - w[i], chosen)
            chosen.pop()
        rec(i + 1, cur_v, room, chosen)  # branch 2: skip item i

    rec(0, 0.0, float(cap), [])
    sel = sorted(int(order[k]) for k in best["set"])
    return int(round(best["val"])), sel, {"nodes": nodes[0], "timed_out": timed_out[0]}


def ilp(values, weights, cap):
    """Integer linear program solved by HiGHS (branch-and-cut) via scipy.optimize.milp.
    milp minimizes, so the objective is negated."""
    values, weights = _check(values, weights, cap)
    n = len(values)
    res = milp(
        c=-values.astype(float),
        constraints=LinearConstraint(weights.astype(float).reshape(1, -1), ub=float(cap)),
        integrality=np.ones(n),
        bounds=Bounds(0, 1),
    )
    if not res.success:
        raise RuntimeError(res.message)
    chosen = [i for i in range(n) if res.x[i] > 0.5]
    return int(round(-res.fun)), chosen, {}


def brute(values, weights, cap):
    values, weights = _check(values, weights, cap)
    n = len(values)
    if n > 22:
        raise ValueError("brute force limited to n <= 22")
    masks = np.arange(1 << n, dtype=np.int64)
    bits = ((masks[:, None] >> np.arange(n)) & 1).astype(np.int64)
    tw = bits @ weights
    tv = bits @ values
    tv = np.where(tw <= cap, tv, -1)
    k = int(np.argmax(tv))
    return int(tv[k]), [i for i in range(n) if bits[k, i]], {}


def is_feasible(chosen, weights, cap):
    return int(np.sum(np.asarray(weights)[list(chosen)])) <= cap if len(chosen) else True
