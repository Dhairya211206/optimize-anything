"""Track E case study: weekly shift rostering for a manufacturing plant (SYNTHETIC data only).

Problem
-------
W workers, D days (the last window may be a partial week), S=3 shifts per day (0 morning, 1 evening, 2 night).
Decision: a[w, d] in {0..S-1} (works that shift) or S (off).

Hard constraints
  C1 coverage      : workers on shift (d, s)  >=  demand[d, s]
  C2 one shift/day : implied by the encoding a[w, d]
  C3 availability  : a[w, d] = off wherever worker w is unavailable on day d
  C4 weekly limit  : at most MAX_WEEK shifts in every 7-day window (consecutive blocks of 7 days)
  C5 rest          : no morning shift on the day after a night shift
Objective (minimise)
  sum of preference costs  +  LAM * (max shifts of any worker - min shifts of any worker)   [fairness]

Three solution methods share one instance format: greedy, simulated annealing / hill climbing
(penalty method), and an exact ILP (scipy.optimize.milp, HiGHS).
"""
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

S = 3
OFF = S
MAX_WEEK = 5
LAM = 1.0
PEN = 10.0  # penalty weight per unit of constraint violation in the local-search methods


# ------------------------------------------------------------------ instance
def nweeks(D):
    return -(-D // 7)


def make_instance(W, D, seed=0, avail_prob=0.9, demand_frac=0.5):
    """Random synthetic instance. demand is about demand_frac * W workers per day, split across shifts
    (night is lighter). Preference cost in {0..4}; nights are disliked on average."""
    rng = np.random.default_rng(seed)
    avail = rng.uniform(size=(W, D)) < avail_prob
    cost = rng.integers(0, 5, size=(W, D, S)).astype(float)
    cost[:, :, 2] += rng.uniform(0, 1.5, size=(W, 1))  # per-worker dislike of nights
    base = demand_frac * W
    split = np.array([0.45, 0.35, 0.20])
    demand = np.maximum(1, np.round(base * split * rng.uniform(0.8, 1.2, size=(D, S)))).astype(int)
    return dict(W=W, D=D, avail=avail, cost=cost, demand=demand)


# ------------------------------------------------------------------ evaluation (the single source of truth)
def evaluate(inst, a):
    """Return a dict of objective parts and violation counts for assignment a (W x D ints in 0..S)."""
    W, D = inst["W"], inst["D"]
    cost, avail, demand = inst["cost"], inst["avail"], inst["demand"]
    works = a < S
    pref = float(sum(cost[w, d, a[w, d]] for w in range(W) for d in range(D) if works[w, d]))
    cover = np.zeros((D, S), int)
    for s in range(S):
        cover[:, s] = (a == s).sum(axis=0)
    shortfall = int(np.maximum(0, demand - cover).sum())
    avail_viol = int((works & ~avail).sum())
    weekly = int(sum(max(0, int(works[w, 7 * k:7 * k + 7].sum()) - MAX_WEEK) for w in range(W) for k in range(nweeks(D))))
    rest = int(((a[:, :-1] == 2) & (a[:, 1:] == 0)).sum())
    counts = works.sum(axis=1)
    spread = int(counts.max() - counts.min())
    violations = shortfall + avail_viol + weekly + rest
    return dict(pref=pref, spread=spread, objective=pref + LAM * spread, shortfall=shortfall,
                availability_violations=avail_viol, weekly_violations=weekly, rest_violations=rest,
                violations=violations, feasible=violations == 0)


# ------------------------------------------------------------------ method 1: greedy
def greedy(inst):
    """Day by day, shift by shift (night first, it is the scarcest), take the cheapest eligible workers.
    Ties broken by fewer shifts so far. May leave coverage short; evaluate() reports that."""
    W, D = inst["W"], inst["D"]
    a = np.full((W, D), OFF, int)
    counts = np.zeros(W, int)
    for d in range(D):
        week_start = 7 * (d // 7)
        for s in (2, 0, 1):
            need = int(inst["demand"][d, s])
            elig = []
            for w in range(W):
                if a[w, d] != OFF or not inst["avail"][w, d]:
                    continue
                if (a[w, week_start:d] < S).sum() >= MAX_WEEK:
                    continue
                if s == 0 and d > 0 and a[w, d - 1] == 2:
                    continue
                elig.append((inst["cost"][w, d, s], counts[w], w))
            elig.sort()
            for _, _, w in elig[:need]:
                a[w, d] = s
                counts[w] += 1
    return a


# ------------------------------------------------------------------ method 2: simulated annealing / hill climbing
class _State:
    """Incrementally maintained penalised cost for fast local moves."""

    def __init__(self, inst, a):
        self.inst, self.a = inst, a.copy()
        W, D = inst["W"], inst["D"]
        self.cover = np.zeros((D, S), int)
        for s in range(S):
            self.cover[:, s] = (a == s).sum(axis=0)
        self.counts = (a < S).sum(axis=1)
        self.pref = sum(inst["cost"][w, d, a[w, d]] for w in range(W) for d in range(D) if a[w, d] < S)
        self.week = np.array([[(a[w, 7 * k:7 * k + 7] < S).sum() for k in range(nweeks(D))] for w in range(W)])
        self.short = int(np.maximum(0, inst["demand"] - self.cover).sum())
        self.weekx = int(np.maximum(0, self.week - MAX_WEEK).sum())
        self.rest = int(((a[:, :-1] == 2) & (a[:, 1:] == 0)).sum())

    def total(self):
        return self.pref + LAM * (self.counts.max() - self.counts.min()) + PEN * (self.short + self.weekx + self.rest)

    def _rest_local(self, w, d):
        a, n = self.a, 0
        if d > 0:
            n += int(a[w, d - 1] == 2 and a[w, d] == 0)
        if d + 1 < self.inst["D"]:
            n += int(a[w, d] == 2 and a[w, d + 1] == 0)
        return n

    def set(self, w, d, v):
        """Change a[w, d] to v and update all aggregates; returns the previous value."""
        inst, a = self.inst, self.a
        old = a[w, d]
        k = d // 7
        dem = inst["demand"]
        self.rest -= self._rest_local(w, d)
        if old < S:
            self.pref -= inst["cost"][w, d, old]
            self.short -= max(0, dem[d, old] - self.cover[d, old])
            self.cover[d, old] -= 1
            self.short += max(0, dem[d, old] - self.cover[d, old])
            self.counts[w] -= 1
            self.weekx -= max(0, self.week[w, k] - MAX_WEEK)
            self.week[w, k] -= 1
            self.weekx += max(0, self.week[w, k] - MAX_WEEK)
        a[w, d] = v
        if v < S:
            self.pref += inst["cost"][w, d, v]
            self.short -= max(0, dem[d, v] - self.cover[d, v])
            self.cover[d, v] += 1
            self.short += max(0, dem[d, v] - self.cover[d, v])
            self.counts[w] += 1
            self.weekx -= max(0, self.week[w, k] - MAX_WEEK)
            self.week[w, k] += 1
            self.weekx += max(0, self.week[w, k] - MAX_WEEK)
        self.rest += self._rest_local(w, d)
        return old


def anneal(inst, start, iters=200_000, t0=2.0, t1=0.05, seed=0):
    """Simulated annealing on the penalised objective. t0 = t1 = 0 gives pure hill climbing
    (accept only non-worsening moves). Moves: (a) change one worker-day, (b) hand one shift on a day
    to another worker who is free that day. Returns (best FEASIBLE assignment found or None, trace)."""
    rng = np.random.default_rng(seed)
    st = _State(inst, start)
    W, D = inst["W"], inst["D"]
    cur = st.total()
    best, best_val = None, np.inf
    if st.short + st.weekx + st.rest == 0:
        best, best_val = st.a.copy(), cur
    trace = []
    for it in range(iters):
        T = t0 * (t1 / t0) ** (it / iters) if t0 > 0 else 0.0
        if rng.uniform() < 0.5:
            w, d = int(rng.integers(W)), int(rng.integers(D))
            if not inst["avail"][w, d]:
                continue
            v = int(rng.integers(S + 1))
            if v == st.a[w, d]:
                continue
            old = st.set(w, d, v)
            new = st.total()
            if new <= cur or (T > 0 and rng.uniform() < np.exp((cur - new) / T)):
                cur = new
            else:
                st.set(w, d, old)
        else:
            d = int(rng.integers(D))
            w = int(rng.integers(W))
            if st.a[w, d] == OFF:
                continue
            w2 = int(rng.integers(W))
            if w2 == w or st.a[w2, d] != OFF or not inst["avail"][w2, d]:
                continue
            s = st.a[w, d]
            o1 = st.set(w, d, OFF)
            o2 = st.set(w2, d, s)
            new = st.total()
            if new <= cur or (T > 0 and rng.uniform() < np.exp((cur - new) / T)):
                cur = new
            else:
                st.set(w2, d, o2)
                st.set(w, d, o1)
        if st.short + st.weekx + st.rest == 0 and cur < best_val - 1e-9:
            best, best_val = st.a.copy(), cur
        if it % max(1, iters // 50) == 0:
            trace.append(float(cur))
    return best, trace


# ------------------------------------------------------------------ method 3: exact ILP
def ilp(inst, time_limit=30.0):
    """Exact formulation of the problem above as a 0-1 ILP (scipy.optimize.milp / HiGHS).
    Variables: x[w,d,s] binary, then Lmax, Lmin (integer). Returns (assignment or None, info dict)."""
    W, D = inst["W"], inst["D"]
    nx = W * D * S
    n = nx + 2
    idx = lambda w, d, s: (w * D + d) * S + s
    c = np.zeros(n)
    c[:nx] = inst["cost"].reshape(-1)
    c[nx], c[nx + 1] = LAM, -LAM
    rows = D * S + W * D + W * nweeks(D) + W * (D - 1) + 2 * W
    A = lil_matrix((rows, n))
    lb = np.full(rows, -np.inf)
    ub = np.full(rows, np.inf)
    r = 0
    for d in range(D):
        for s in range(S):
            for w in range(W):
                A[r, idx(w, d, s)] = 1
            lb[r] = inst["demand"][d, s]
            r += 1
    for w in range(W):
        for d in range(D):
            for s in range(S):
                A[r, idx(w, d, s)] = 1
            ub[r] = 1
            r += 1
    for w in range(W):
        for k in range(nweeks(D)):
            for d in range(7 * k, min(D, 7 * k + 7)):
                for s in range(S):
                    A[r, idx(w, d, s)] = 1
            ub[r] = MAX_WEEK
            r += 1
    for w in range(W):
        for d in range(D - 1):
            A[r, idx(w, d, 2)] = 1
            A[r, idx(w, d + 1, 0)] = 1
            ub[r] = 1
            r += 1
    for w in range(W):  # total_w - Lmax <= 0 ; Lmin - total_w <= 0
        for d in range(D):
            for s in range(S):
                A[r, idx(w, d, s)] = 1
                A[r + 1, idx(w, d, s)] = -1
        A[r, nx] = -1
        A[r + 1, nx + 1] = 1
        ub[r] = 0
        ub[r + 1] = 0
        r += 2
    lo, hi = np.zeros(n), np.ones(n)
    hi[nx:] = D
    for w in range(W):
        for d in range(D):
            if not inst["avail"][w, d]:
                hi[idx(w, d, 0):idx(w, d, 0) + S] = 0
    t0 = time.perf_counter()
    res = milp(c, constraints=LinearConstraint(A.tocsr(), lb, ub), integrality=np.ones(n),
               bounds=Bounds(lo, hi), options=dict(time_limit=time_limit, disp=False))
    info = dict(seconds=time.perf_counter() - t0, status=int(res.status), message=str(res.message))
    if res.x is None:
        return None, info
    x = np.round(res.x[:nx]).reshape(W, D, S)
    a = np.full((W, D), OFF, int)
    for s in range(S):
        a[x[:, :, s] > 0.5] = s
    info.update(objective=float(res.fun), dual_bound=float(res.mip_dual_bound) if res.mip_dual_bound is not None else None,
                gap=float(res.mip_gap) if res.mip_gap is not None else None, proven_optimal=bool(res.status == 0))
    return a, info


# ------------------------------------------------------------------ tiny exact reference (for tests)
def brute_force(inst):
    """Enumerate every assignment (only for tiny instances). Returns (best assignment, objective)."""
    import itertools
    W, D = inst["W"], inst["D"]
    best, bv = None, np.inf
    for flat in itertools.product(range(S + 1), repeat=W * D):
        a = np.array(flat).reshape(W, D)
        e = evaluate(inst, a)
        if e["feasible"] and e["objective"] < bv:
            best, bv = a.copy(), e["objective"]
    return best, bv
