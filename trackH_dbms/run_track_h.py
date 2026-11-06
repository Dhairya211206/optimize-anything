"""Track H: index selection on SQLite as a budgeted optimisation problem (greedy vs knapsack DP vs exact ILP vs the default planner).

Usage (repo root): python trackH_dbms/run_track_h.py [measure select]
  measure : build the dataset, time every query with no index and with each single candidate index (writes results/measured.json)
  select  : solve the selection problem with each method for several storage budgets, BUILD each chosen configuration and
            measure the real workload time; results in results/results.json
Data: synthetic TPC-H-like, scale factor 0.1 (15,000 customers, 150,000 orders, about 600,000 line items), see tpch_like.py.
SQLite default planner (automatic indexes ON) is the baseline. Timing = minimum of 3 runs after a warm-up, on a shared 2-core machine.
"""
import json
import os
import sqlite3
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dbutil as du  # noqa: E402
import selection as sel  # noqa: E402
import tpch_like  # noqa: E402
from workload import CANDIDATES, QUERIES  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
DB = "/tmp/tpch_like_sf01.db"
SF = float(os.environ.get("TRACK_H_SF", "0.1"))
MEASURED = os.path.join(OUT, "measured.json")
RESULTS = os.path.join(OUT, "results.json")
BUDGET_FRACTIONS = [0.05, 0.10, 0.20, 0.40]  # of the total size of all candidate indexes


def measure():
    t0 = time.perf_counter()
    counts = tpch_like.build(DB, sf=SF)
    print("built", counts, f"{time.perf_counter() - t0:.1f}s", flush=True)
    con = sqlite3.connect(DB)
    qn = list(QUERIES)
    base_t, base_h, base_plan = {}, {}, {}
    for q in qn:
        sql = QUERIES[q][0]
        t, h, to = du.measure(con, sql)
        base_t[q], base_h[q] = t, h
        base_plan[q] = du.plan(con, sql)
        print(f"  baseline {q}: {t * 1000:.1f} ms timeout={to}", flush=True)
    data_bytes = os.path.getsize(DB)
    names = list(CANDIDATES)
    sizes, single = {}, {}
    for n in names:
        du.create_indexes(con, [n], CANDIDATES)
        sizes[n] = du.index_size_bytes(con, f"ix_{n}")
        single[n] = {}
        for q in qn:
            t, h, to = du.measure(con, QUERIES[q][0], reps=2)
            assert h == base_h[q], (n, q)  # results must be identical
            single[n][q] = t
        du.drop_indexes(con, [n])
        print(f"  index {n}: {sizes[n] / 1e6:.2f} MB, best single-query saving {max(base_t[q] - single[n][q] for q in qn) * 1000:.0f} ms", flush=True)
    con.close()
    json.dump(dict(scale_factor=SF, row_counts=counts, database_bytes=data_bytes, queries=qn, weights={q: QUERIES[q][1] for q in qn},
                   baseline_seconds=base_t, baseline_hash=base_h, baseline_plan=base_plan, index_bytes=sizes, single_index_seconds=single),
              open(MEASURED, "w"), indent=1)


def workload_time(con, qn, w, reps=3):
    tot, hashes, plans = 0.0, {}, {}
    per = {}
    for q in qn:
        t, h, to = du.measure(con, QUERIES[q][0], reps=reps)
        per[q] = t
        tot += w[q] * t
        hashes[q] = h
        plans[q] = du.plan(con, QUERIES[q][0])
    return tot, per, hashes, plans


def select():
    m = json.load(open(MEASURED))
    qn, names = m["queries"], list(CANDIDATES)
    w = np.array([m["weights"][q] for q in qn], float)
    base = np.array([m["baseline_seconds"][q] for q in qn])
    B = np.array([[max(0.0, base[qi] - m["single_index_seconds"][n][q]) for n in names] for qi, q in enumerate(qn)])
    # harm: measured slow-down of a query caused by an index (ignoring noise-level changes below 3 ms and 10%)
    H = np.array([[max(0.0, m["single_index_seconds"][n][q] - base[qi]) if m["single_index_seconds"][n][q] - base[qi] > max(0.003, 0.1 * base[qi]) else 0.0
                   for n in names] for qi, q in enumerate(qn)])
    sizes = np.array([m["index_bytes"][n] for n in names], float)
    total = sizes.sum()
    con = sqlite3.connect(DB)
    # baseline: default planner, no indexes
    base_total, base_per, base_hash, base_plans = workload_time(con, qn, m["weights"])
    assert base_hash == m["baseline_hash"]
    out = dict(scale_factor=m["scale_factor"], row_counts=m["row_counts"], database_bytes=m["database_bytes"],
               candidate_indexes=len(names), total_candidate_index_bytes=total, baseline_workload_seconds=base_total,
               baseline_per_query_seconds=base_per, runs={})
    methods = {
        "greedy_ratio": lambda b: sel.greedy_ratio(B, w, sizes, b),
        "knapsack_dp": lambda b: sel.knapsack_dp(B, w, sizes, b, unit=total / 2000),
        "greedy_marginal": lambda b: sel.greedy_marginal(B, w, sizes, b),
        "ilp": lambda b: sel.ilp(B, w, sizes, b)[0],
        "ilp_harm_aware": lambda b: sel.ilp(B, w, sizes, b, harm=H)[0],
    }
    # index everything
    du.create_indexes(con, names, CANDIDATES)
    t_all, per_all, h_all, p_all = workload_time(con, qn, m["weights"])
    assert h_all == m["baseline_hash"]
    out["all_indexes"] = dict(storage_bytes=total, workload_seconds=t_all, speedup=base_total / t_all)
    du.drop_indexes(con, names)
    for frac in BUDGET_FRACTIONS:
        budget = frac * total
        for meth, fn in methods.items():
            t0 = time.perf_counter()
            chosen = fn(budget)
            solve = time.perf_counter() - t0
            cn = [names[i] for i in chosen]
            used = float(sizes[chosen].sum()) if chosen else 0.0
            assert used <= budget + 1e-6
            pred = sel.model_benefit(B, w, chosen)
            du.create_indexes(con, cn, CANDIDATES)
            t, per, h, plans = workload_time(con, qn, m["weights"])
            du.drop_indexes(con, cn)
            out["runs"][f"{frac:.2f}/{meth}"] = dict(
                budget_fraction=frac, budget_bytes=budget, method=meth, chosen=cn, storage_bytes=used, solve_seconds=solve,
                predicted_saving_seconds=pred, measured_workload_seconds=t, measured_saving_seconds=base_total - t,
                speedup=base_total / t, results_identical=bool(h == m["baseline_hash"]), per_query_seconds=per,
                plans_changed=int(sum(plans[q] != m["baseline_plan"][q] for q in qn)),
                plans=plans if (frac == 0.20 and meth == "ilp") else None)
            print(f"budget {frac:.2f} {meth}: {len(cn)} idx, {used / 1e6:.1f} MB, predicted {pred:.2f}s, measured saving {base_total - t:.2f}s, "
                  f"speedup {base_total / t:.2f}x, identical={h == m['baseline_hash']}", flush=True)
    con.close()
    # ILP solve-time check on a bigger synthetic benefit matrix (does the exact method scale?)
    rng = np.random.default_rng(0)
    scal = []
    for ni, nq in ((25, 12), (100, 40), (300, 100)):
        Bs = rng.uniform(0, 5, (nq, ni)) * (rng.uniform(size=(nq, ni)) < 0.2)
        ss = rng.uniform(1, 10, ni)
        ws = rng.integers(1, 20, nq).astype(float)
        t0 = time.perf_counter()
        _, info = sel.ilp(Bs, ws, ss, ss.sum() * 0.2, time_limit=60)
        scal.append(dict(candidates=ni, queries=nq, seconds=time.perf_counter() - t0, proven_optimal=info["proven_optimal"]))
    out["ilp_scaling_synthetic"] = scal
    json.dump(out, open(RESULTS, "w"), indent=1, default=float)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for meth in methods:
        ax.plot([100 * f for f in BUDGET_FRACTIONS], [out["runs"][f"{f:.2f}/{meth}"]["speedup"] for f in BUDGET_FRACTIONS], "o-", label=meth)
    ax.axhline(out["all_indexes"]["speedup"], color="k", ls=":", label="all 25 indexes")
    ax.axhline(1.0, color="gray", ls="--", label="default planner, no indexes")
    ax.set_xlabel("storage budget (% of the size of all candidate indexes)")
    ax.set_ylabel("measured workload speedup")
    ax.set_title("Index selection on SQLite, TPC-H-like SF 0.1")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "index_selection.png"), dpi=140)
    plt.close()


if __name__ == "__main__":
    for step in sys.argv[1:] or ["measure", "select"]:
        t0 = time.perf_counter()
        {"measure": measure, "select": select}[step]()
        print(f"[{step}] finished in {time.perf_counter() - t0:.1f}s", flush=True)
