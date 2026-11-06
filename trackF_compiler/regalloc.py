"""Register allocation as an optimisation problem (Track F).

Model (deliberately simple, stated so the results are not over-read):
  * every variable gets a live interval [first, last] over instruction indices (a conservative hull);
  * a variable is either kept in one of K registers for its whole interval or SPILLED to memory for its whole
    life (no live-range splitting); every reference to a spilled variable then costs one memory access;
  * the kept intervals must never overlap more than K at once. Interval graphs are perfect, so that is exactly
    the condition for a K-register assignment to exist (checked by `assign_registers`).
Objective: minimise the total weight of spilled variables, where a variable's weight is the sum over its
references of an execution-frequency estimate. Two estimates are used:
  static  : 10 ** (loop nesting depth of the reference)       (what a compiler can know without running)
  dynamic : the reference's measured execution count from a VM profile (profile-guided)
Methods: linear scan (Poletto and Sarkar style, spill the furthest end), greedy by weight, exact ILP.
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from opt import dst, liveness_by_instr, uses


def intervals_and_refs(code):
    la = liveness_by_instr(code)
    iv, refs = {}, {}
    prev_after = set()
    live_before = []
    # live-before of instruction i equals live_after[i] minus defs plus uses
    for i, ins in enumerate(code):
        d = dst(ins)
        lb = (la[i] - ({d} if d is not None else set())) | set(uses(ins))
        live_before.append(lb)
    for i, ins in enumerate(code):
        here = set(la[i]) | live_before[i] | set(uses(ins))
        if dst(ins) is not None:
            here.add(dst(ins))
        for v in here:
            s, e = iv.get(v, (i, i))
            iv[v] = (min(s, i), max(e, i))
        for v in set(uses(ins)) | ({dst(ins)} if dst(ins) is not None else set()):
            refs.setdefault(v, []).append(i)
    return iv, refs


def loop_depths(code):
    lab = {ins[1]: i for i, ins in enumerate(code) if ins[0] == "label"}
    depth = [0] * len(code)
    for j, ins in enumerate(code):
        if ins[0] == "jmp" and lab.get(ins[1], j + 1) < j:
            for i in range(lab[ins[1]], j + 1):
                depth[i] += 1
    return depth


def weights(code, refs, counts=None):
    """static weights (counts=None) or dynamic weights from a VM profile."""
    depth = loop_depths(code)
    w = {}
    for v, idx in refs.items():
        w[v] = float(sum((counts[i] if counts is not None else 10 ** depth[i]) for i in idx))
    return w


def max_pressure(iv, kept):
    n = max((e for _, e in iv.values()), default=0) + 1
    occ = np.zeros(n + 1, int)
    for v in kept:
        s, e = iv[v]
        occ[s:e + 1] += 1
    return int(occ.max())


def linear_scan(iv, K):
    active, spilled = [], set()
    for v, (s, e) in sorted(iv.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        active = [(ae, av) for ae, av in active if ae >= s]
        if len(active) >= K:
            ae, av = max(active)
            if ae > e:
                spilled.add(av)
                active.remove((ae, av))
                active.append((e, v))
            else:
                spilled.add(v)
        else:
            active.append((e, v))
    return spilled


def greedy_weight(iv, w, K):
    n = max((e for _, e in iv.values()), default=0) + 1
    occ = np.zeros(n + 1, int)
    spilled = set()
    for v in sorted(iv, key=lambda v: (-w[v], iv[v][1] - iv[v][0])):
        s, e = iv[v]
        if occ[s:e + 1].max() < K:
            occ[s:e + 1] += 1
        else:
            spilled.add(v)
    return spilled


def ilp_alloc(iv, w, K, time_limit=30.0):
    names = sorted(iv)
    n = len(names)
    starts = sorted({s for s, _ in iv.values()})
    rows = []
    seen = set()
    for p in starts:
        cover = tuple(i for i, v in enumerate(names) if iv[v][0] <= p <= iv[v][1])
        if len(cover) > K and cover not in seen:
            seen.add(cover)
            rows.append(cover)
    if not rows:
        return set(), dict(proven_optimal=True, seconds=0.0)
    A = lil_matrix((len(rows), n))
    for r, cover in enumerate(rows):
        for i in cover:
            A[r, i] = 1
    c = -np.array([w[v] for v in names])
    res = milp(c, constraints=LinearConstraint(A.tocsr(), -np.inf, K), integrality=np.ones(n),
               bounds=Bounds(0, 1), options=dict(time_limit=time_limit, disp=False))
    kept = {names[i] for i in range(n) if res.x[i] > 0.5}
    return set(names) - kept, dict(proven_optimal=bool(res.status == 0), status=int(res.status))


def assign_registers(iv, kept, K):
    """Sweep by start point and give each kept interval a free register; returns {var: reg}.
    Raises if more than K are live at once (which would mean the kept set was invalid)."""
    free = list(range(K))
    active = []
    out = {}
    for v in sorted(kept, key=lambda v: iv[v]):
        s, e = iv[v]
        for ae, av in [x for x in active if x[0] < s]:
            free.append(out[av])
            active.remove((ae, av))
        if not free:
            raise RuntimeError("more than K simultaneously live")
        out[v] = free.pop(0)
        active.append((e, v))
    return out


def spill_cost(spilled, w):
    return float(sum(w[v] for v in spilled))
