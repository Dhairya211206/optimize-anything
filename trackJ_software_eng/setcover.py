"""Test-suite minimisation and prioritisation as optimisation problems (Track J).

Minimisation  variables y_t in {0,1} (keep test t); minimise sum_t cost_t y_t  s.t.  for every requirement r (a source line):
              sum_{t covers r} y_t >= 1.   This is the weighted set-cover problem (NP-hard).
Methods       exact ILP (scipy.optimize.milp / HiGHS), greedy by additional requirements covered, greedy by additional
              requirements per unit cost, random order until covered, original order until covered.
Prioritisation orders the tests; APFD (average percentage of faults detected) scores an order against a kill matrix.
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


def universe(cover):
    u = set()
    for s in cover.values():
        u |= s
    return u


def ilp_min_cost(cover, cost, time_limit=60.0):
    tests = sorted(cover)
    reqs = sorted(universe(cover))
    ridx = {r: i for i, r in enumerate(reqs)}
    A = lil_matrix((len(reqs), len(tests)))
    for j, t in enumerate(tests):
        for r in cover[t]:
            A[ridx[r], j] = 1
    c = np.array([cost[t] for t in tests], float)
    res = milp(c, constraints=LinearConstraint(A.tocsr(), 1, np.inf), integrality=np.ones(len(tests)), bounds=Bounds(0, 1),
               options=dict(time_limit=time_limit, disp=False))
    chosen = [t for j, t in enumerate(tests) if res.x[j] > 0.5]
    return chosen, dict(proven_optimal=bool(res.status == 0))


def greedy(cover, cost, by="count"):
    """Repeatedly add the test with the most uncovered requirements (by='count') or most per unit cost (by='ratio')."""
    left = universe(cover)
    chosen = []
    pool = dict(cover)
    while left:
        best, bt = 0.0, None
        for t, s in pool.items():
            g = len(s & left)
            if g == 0:
                continue
            score = g if by == "count" else g / max(cost[t], 1e-9)
            if score > best:
                best, bt = score, t
        if bt is None:
            break
        chosen.append(bt)
        left -= pool.pop(bt)
    return chosen


def until_covered(order, cover):
    left = universe(cover)
    chosen = []
    for t in order:
        if not left:
            break
        if cover[t] & left:
            chosen.append(t)
            left -= cover[t]
    return chosen


def covered_fraction(chosen, cover):
    u = universe(cover)
    got = set()
    for t in chosen:
        got |= cover[t]
    return len(got) / max(len(u), 1)


def greedy_order(cover, cost, by="count"):
    """Prioritisation: full ordering by additional coverage (ties and the tail by cost)."""
    first = greedy(cover, cost, by)
    rest = sorted(set(cover) - set(first), key=lambda t: cost[t])
    return first + rest


def apfd(order, kills):
    """kills: dict fault -> set of tests that detect it. Faults detected by no test are ignored.
    APFD = 1 - (sum of first-detecting positions) / (n_tests * n_faults) + 1 / (2 n_tests)."""
    n = len(order)
    pos = {t: i + 1 for i, t in enumerate(order)}
    firsts = [min(pos[t] for t in ts if t in pos) for ts in kills.values() if any(t in pos for t in ts)]
    if not firsts:
        return float("nan")
    return 1 - sum(firsts) / (n * len(firsts)) + 1 / (2 * n)
