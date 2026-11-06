"""Track B: discrete optimization experiments.

Run from the repo root:  python trackB_discrete/run_track_b.py
Writes results/results.json and results/maxcut_instance.json (reused by Track C).

Fairness: every knapsack solver gets the same instance; runtime is the median of 3 runs
(wall-clock, single thread). Stochastic heuristics (hill climbing, annealing) use seeds 0..49
and report the fraction of runs reaching the exact optimum, plus mean +- std of the value.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import discrete as dc  # noqa: E402
import qubo as qb  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT, exist_ok=True)
R = {}


def timed(fn, repeats=3):
    ts, out = [], None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t0)
    return out, float(np.median(ts))


# ------------------------------------------------------------ 1. knapsack, verified small case
def exp_knapsack_small():
    v, w, cap = dc.make_instance(20, seed=0)
    ref, _, _ = dc.brute(v, w, cap)
    rows = {}
    for name in ("greedy", "dp", "bnb", "ilp", "brute"):
        (val, chosen, info), rt = timed(lambda: getattr(dc, name)(v, w, cap))
        assert dc.is_feasible(chosen, w, cap)
        rows[name] = dict(value=val, runtime_ms=rt * 1e3, gap_pct=100 * (ref - val) / ref, **{k: info[k] for k in info})
    R["knapsack_n20"] = dict(capacity=cap, optimum=ref, solvers=rows)
    # classic instance where ratio-greedy is far from optimal
    vv, ww, cc = np.array([2, 15]), np.array([1, 10]), 10
    R["greedy_counterexample"] = dict(greedy=dc.greedy(vv, ww, cc)[0], optimum=dc.dp(vv, ww, cc)[0])


# ------------------------------------------------------------ 2. scaling and hardness
def exp_knapsack_scaling():
    out = {}
    for kind, sizes in (("uncorrelated", [20, 50, 100, 200, 400]), ("strongly_correlated", [20, 30, 40, 50])):
        rows = []
        for n in sizes:
            v, w, cap = dc.make_instance(n, seed=1, kind=kind)
            opt, _, _ = dc.dp(v, w, cap)  # DP is the reference (exact, verified against brute force in tests)
            row = dict(n=n, capacity=cap, optimum=opt)
            for name in ("greedy", "dp", "bnb", "ilp"):
                (val, chosen, info), rt = timed(lambda: getattr(dc, name)(v, w, cap))
                row[name] = dict(value=val, runtime_ms=rt * 1e3, gap_pct=100 * (opt - val) / opt,
                                 nodes=info.get("nodes"), timed_out=info.get("timed_out", False))
            rows.append(row)
        out[kind] = rows
    R["knapsack_scaling"] = out


def exp_dp_weight_magnitude():
    """DP cost grows with the capacity VALUE (pseudo-polynomial); B&B and ILP do not depend on it directly."""
    rows = []
    for max_w in (100, 1000, 10000):
        v, w, cap = dc.make_instance(50, seed=2, max_w=max_w)
        opt, _, info = dc.dp(v, w, cap)
        row = dict(max_weight=max_w, capacity=cap, dp_table_cells=info["table_cells"], optimum=opt)
        for name in ("dp", "bnb", "ilp"):
            (val, _, inf), rt = timed(lambda: getattr(dc, name)(v, w, cap))
            assert val == opt
            row[name + "_ms"] = rt * 1e3
        rows.append(row)
    R["dp_weight_magnitude"] = rows


# ------------------------------------------------------------ 3. Max-Cut as QUBO / Ising
def exp_maxcut():
    g = qb.maxcut_graph(8, 0.5, 7)
    Q = qb.maxcut_qubo(g)
    E_opt, x_opt, E_all = qb.brute_force_qubo(Q)
    cut_opt = -E_opt
    ilp_cut, _ = qb.maxcut_ilp(g)
    h, J, c = qb.qubo_to_ising(Q)
    s_opt = 1 - 2 * x_opt.astype(float)
    ising_gs = qb.ising_energy(h, J, c, s_opt)
    hc = [-qb.hill_climb(Q, seed=s)[0] for s in range(50)]
    sa = [-qb.simulated_annealing(Q, seed=s)[0] for s in range(50)]
    R["maxcut_n8"] = dict(
        nodes=8, edges=g.number_of_edges(), exact_cut=float(cut_opt), ilp_cut=ilp_cut,
        optimal_assignment=x_opt.tolist(), ising_energy_at_optimum=ising_gs,
        n_optimal_assignments=int(np.sum(E_all == E_opt)),
        hill_climb=dict(mean=float(np.mean(hc)), std=float(np.std(hc)), success_rate=float(np.mean(np.array(hc) == cut_opt))),
        annealing=dict(mean=float(np.mean(sa)), std=float(np.std(sa)), success_rate=float(np.mean(np.array(sa) == cut_opt))),
    )
    with open(os.path.join(OUT, "maxcut_instance.json"), "w") as fh:
        json.dump(dict(n=8, p=0.5, seed=7, edges=[list(e) for e in g.edges()], optimal_cut=int(cut_opt),
                       optimal_assignment=x_opt.tolist()), fh, indent=1)

    # larger graph where exhaustive search is still possible, to see whether heuristics start to miss
    g2 = qb.maxcut_graph(20, 0.5, 3)
    Q2 = qb.maxcut_qubo(g2)
    E2, _, _ = qb.brute_force_qubo(Q2)
    hc2 = [-qb.hill_climb(Q2, seed=s)[0] for s in range(50)]
    sa2 = [-qb.simulated_annealing(Q2, seed=s)[0] for s in range(50)]
    R["maxcut_n20"] = dict(
        edges=g2.number_of_edges(), exact_cut=float(-E2), ilp_cut=qb.maxcut_ilp(g2)[0],
        hill_climb=dict(mean=float(np.mean(hc2)), std=float(np.std(hc2)), success_rate=float(np.mean(np.array(hc2) == -E2))),
        annealing=dict(mean=float(np.mean(sa2)), std=float(np.std(sa2)), success_rate=float(np.mean(np.array(sa2) == -E2))),
    )


# ------------------------------------------------------------ 4. feature selection with penalty
def exp_feature_selection():
    X, y = qb.make_feature_data(400, seed=0)
    n = X.shape[1]
    out = {}
    for k in (4, 6):
        Q, r, Rm = qb.feature_selection_qubo(X, y, k, penalty=2.0)
        E, x_opt, E_all = qb.brute_force_qubo(Q)
        g = qb.greedy_forward_selection(r, Rm, k)
        sa = [qb.simulated_annealing(Q, seed=s, sweeps=200)[1] for s in range(30)]
        sa_obj = [qb.fs_objective(x, r, Rm) for x in sa]
        sa_card_ok = [int(x.sum()) == k for x in sa]
        out[f"k={k}"] = dict(
            exact_selected=np.flatnonzero(x_opt).tolist(), exact_objective=qb.fs_objective(x_opt, r, Rm),
            greedy_selected=np.flatnonzero(g).tolist(), greedy_objective=qb.fs_objective(g, r, Rm),
            sa_objective_mean=float(np.mean(sa_obj)), sa_objective_std=float(np.std(sa_obj)),
            sa_reaches_exact=float(np.mean([np.array_equal(x, x_opt) for x in sa])),
            sa_cardinality_ok=float(np.mean(sa_card_ok)),
        )
    R["feature_selection"] = out

    # Annealing sensitivity: the default temperatures were chosen for Max-Cut energies (integers of
    # size ~10). This QUBO has energies of size ~1, so check whether the low success rate is just that.
    Q, r, Rm = qb.feature_selection_qubo(X, y, 4, penalty=2.0)
    _, x_opt, _ = qb.brute_force_qubo(Q)
    sens = []
    for t0 in (2.0, 0.5, 0.1):
        for sweeps in (200, 2000):
            xs = [qb.simulated_annealing(Q, seed=s, sweeps=sweeps, t0=t0, t1=0.001)[1] for s in range(30)]
            sens.append(dict(t0=t0, sweeps=sweeps, reaches_exact=float(np.mean([np.array_equal(x, x_opt) for x in xs]))))
    R["sa_sensitivity_fs_k4"] = sens

    # Penalty sweep: how large must P be for the exact QUBO optimum to have exactly k ones?
    sweep = {}
    for k in (4, 6):
        rows = []
        for P in (0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0):
            Q, r, Rm = qb.feature_selection_qubo(X, y, k, penalty=P)
            _, x, _ = qb.brute_force_qubo(Q)
            rows.append(dict(penalty=P, n_selected=int(x.sum()), feasible=bool(x.sum() == k)))
        sweep[f"k={k}"] = rows
    R["penalty_sweep"] = sweep


def main():
    exp_knapsack_small()
    exp_knapsack_scaling()
    exp_dp_weight_magnitude()
    exp_maxcut()
    exp_feature_selection()
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(R, fh, indent=1, default=float)
    print(json.dumps(R["knapsack_n20"], indent=1))
    print(json.dumps(R["greedy_counterexample"]))
    for kind, rows in R["knapsack_scaling"].items():
        print("\n", kind)
        for row in rows:
            s = f"  n={row['n']:4d} opt={row['optimum']:6d} "
            for name in ("greedy", "dp", "bnb", "ilp"):
                d = row[name]
                s += f"| {name}: {d['runtime_ms']:8.2f}ms gap={d['gap_pct']:.2f}%" + (f" nodes={d['nodes']}" if d["nodes"] else "") + (" TIMEOUT" if d["timed_out"] else "") + " "
            print(s)
    print(json.dumps(R["maxcut_n8"], indent=1))
    print(json.dumps(R["maxcut_n20"], indent=1))
    print(json.dumps(R["feature_selection"], indent=1))
    print(json.dumps(R["penalty_sweep"]))


if __name__ == "__main__":
    main()
