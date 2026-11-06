"""Submodular optimization (Track D).

A set function f is submodular if it has diminishing returns:
    f(A + e) - f(A)  >=  f(B + e) - f(B)    for all A subset of B and e not in B.
It is monotone if f(A + e) >= f(A). The classic guarantee (Nemhauser, Wolsey, Fisher 1978) is
    f(greedy_k) >= (1 - 1/e) * f(OPT_k)   ONLY when f is monotone, submodular and f(empty) >= 0,
with a cardinality constraint |S| <= k. This module therefore TESTS those conditions before any
guarantee is claimed.
"""
import heapq
import itertools
import os
import sys

import numpy as np


# ------------------------------------------------------------------ objectives
class FacilityLocation:
    """f(S) = sum over clients of the best similarity to any chosen facility. Monotone submodular."""

    def __init__(self, n_clients=300, n_candidates=40, seed=0):
        rng = np.random.default_rng(seed)
        pts = rng.uniform(0, 1, (n_clients, 2))
        fac = rng.uniform(0, 1, (n_candidates, 2))
        d = np.linalg.norm(pts[:, None, :] - fac[None, :, :], axis=2)
        self.sim = np.exp(-4 * d)
        self.n = n_candidates
        self.calls = 0

    def __call__(self, S):
        self.calls += 1
        S = list(S)
        return float(self.sim[:, S].max(axis=1).sum()) if S else 0.0


class PenalisedSelection:
    """f(S) = sum_{i in S} r_i - alpha * sum_{i<j in S} R_ij with R_ij >= 0 (relevance minus redundancy,
    the Track B feature-selection objective). Submodular (marginal gain r_e - alpha sum_{j in S} R_ej only
    shrinks as S grows) but NOT monotone: adding an item can lower f."""

    def __init__(self, r, R, alpha=1.0):
        self.r, self.R, self.alpha = np.asarray(r, float), np.asarray(R, float), alpha
        self.n = len(self.r)
        self.calls = 0

    def __call__(self, S):
        self.calls += 1
        S = list(S)
        if not S:
            return 0.0
        sub = self.R[np.ix_(S, S)]
        return float(self.r[S].sum() - self.alpha * 0.5 * (sub.sum() - np.trace(sub)))


class SynergySelection(PenalisedSelection):
    """f(S) = sum r_i + alpha sum_{i<j in S} R_ij. Pairwise SYNERGY makes marginal gains GROW with S, so
    this is supermodular, NOT submodular. Greedy has no guarantee here."""

    def __call__(self, S):
        self.calls += 1
        S = list(S)
        if not S:
            return 0.0
        sub = self.R[np.ix_(S, S)]
        return float(self.r[S].sum() + self.alpha * 0.5 * (sub.sum() - np.trace(sub)))


# ------------------------------------------------------------------ condition checks
def check_conditions(f, n, trials=3000, seed=0):
    """Randomised test of diminishing returns and monotonicity.
    Returns counts of violations over `trials` random (A subset B, e not in B) triples.
    A violation found PROVES the property fails; zero violations does not prove it holds."""
    rng = np.random.default_rng(seed)
    dr_viol = mono_viol = 0
    worst = 0.0
    for _ in range(trials):
        size_b = int(rng.integers(1, n))
        B = list(rng.choice(n, size=size_b, replace=False))
        size_a = int(rng.integers(0, size_b + 1))
        A = B[:size_a]
        rest = [i for i in range(n) if i not in B]
        if not rest:
            continue
        e = int(rng.choice(rest))
        gain_a = f(A + [e]) - f(A)
        gain_b = f(B + [e]) - f(B)
        if gain_a < gain_b - 1e-9:
            dr_viol += 1
            worst = max(worst, gain_b - gain_a)
        if gain_b < -1e-9:
            mono_viol += 1
    return dict(trials=trials, diminishing_returns_violations=dr_viol,
                monotonicity_violations=mono_viol, worst_dr_violation=worst)


# ------------------------------------------------------------------ algorithms
def greedy(f, n, k):
    """Standard greedy: add the element with the largest marginal gain, k times."""
    S, cur = [], f([])
    for _ in range(k):
        best, be = -np.inf, None
        for e in range(n):
            if e in S:
                continue
            g = f(S + [e]) - cur
            if g > best:
                best, be = g, e
        S.append(be)
        cur += best
    return S, cur


def lazy_greedy(f, n, k):
    """Lazy greedy (Minoux): marginal gains can only shrink for a submodular f, so a stale gain is an
    upper bound. Re-evaluate only the top of a heap. Same result as greedy when f is submodular;
    NOT valid otherwise."""
    S, cur = [], f([])
    heap = [(-(f([e]) - cur), e, 0) for e in range(n)]
    heapq.heapify(heap)
    for it in range(k):
        while True:
            neg, e, stamp = heapq.heappop(heap)
            if stamp == it:
                S.append(e)
                cur += -neg
                break
            heapq.heappush(heap, (-(f(S + [e]) - cur), e, it))
    return S, cur


def brute_force(f, n, k):
    best, bs = -np.inf, None
    for S in itertools.combinations(range(n), k):
        v = f(list(S))
        if v > best:
            best, bs = v, list(S)
    return bs, best


def load_trackb_objective(alpha=1.0):
    """Relevance and redundancy from the Track B feature-selection data."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "trackB_discrete"))
    import qubo as qb
    X, y = qb.make_feature_data(400, seed=0)
    _, r, R = qb.feature_selection_qubo(X, y, 4, alpha=alpha, penalty=0.0)
    R = R - np.eye(len(r))  # no self-redundancy
    return r, R
