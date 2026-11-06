"""Track E experiments: shift rostering with greedy, hill climbing, simulated annealing and exact ILP.

Usage (repo root): python trackE_case_study/run_track_e.py
All data are SYNTHETIC. Every method gets the same instances. Stochastic methods use 3 seeds per instance.
"""
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import roster as R  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)

SIZES = [(20, 7, 100_000, 5), (40, 14, 200_000, 5), (80, 14, 300_000, 3), (150, 28, 400_000, 3)]  # W, D, SA iters, instances
ILP_LIMIT = 30.0


def ms(v):
    v = [x for x in v if x is not None]
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), n=len(v)) if v else None


def run_size(W, D, iters, n_inst):
    rows = []
    for seed in range(n_inst):
        inst = R.make_instance(W, D, seed=seed)
        rec = dict(seed=seed)
        t = time.perf_counter()
        g = R.greedy(inst)
        eg = R.evaluate(inst, g)
        rec["greedy"] = dict(seconds=time.perf_counter() - t, **eg)
        a, info = R.ilp(inst, ILP_LIMIT)
        rec["ilp"] = dict(info, **(R.evaluate(inst, a) if a is not None else {"feasible": False}))
        # local search starting from the greedy roster (which may be infeasible; the penalty drives repair)
        for name, t0, t1 in (("hill_climb", 0.0, 0.0), ("annealing", 2.0, 0.05)):
            objs, secs, feas = [], [], 0
            for s in range(3):
                t = time.perf_counter()
                best, _ = R.anneal(inst, g, iters=iters, t0=t0, t1=t1, seed=s)
                secs.append(time.perf_counter() - t)
                if best is not None:
                    objs.append(R.evaluate(inst, best)["objective"])
                    feas += 1
            rec[name] = dict(feasible_runs=feas, of=3, objective=ms(objs), seconds=float(np.mean(secs)))
        rows.append(rec)
        print(f"  W={W} D={D} seed={seed}: greedy feasible={eg['feasible']} obj={eg['objective']:.1f} "
              f"ilp obj={rec['ilp'].get('objective')} gap={rec['ilp'].get('gap')} t={rec['ilp']['seconds']:.1f}s", flush=True)
    return rows


def summarise(rows):
    """Gap to ILP is computed against the ILP incumbent; it is only a true optimality gap if proven_optimal."""
    out = {}
    ilp_obj = [r["ilp"].get("objective") for r in rows]
    out["ilp"] = dict(objective=ms(ilp_obj), seconds=ms([r["ilp"]["seconds"] for r in rows]),
                      proven_optimal=sum(bool(r["ilp"].get("proven_optimal")) for r in rows), of=len(rows),
                      reported_gap=ms([r["ilp"].get("gap") for r in rows]))
    out["greedy"] = dict(feasible=sum(r["greedy"]["feasible"] for r in rows), of=len(rows),
                         shortfall_total=int(sum(r["greedy"]["shortfall"] for r in rows)),
                         seconds=ms([r["greedy"]["seconds"] for r in rows]),
                         objective_when_feasible=ms([r["greedy"]["objective"] for r in rows if r["greedy"]["feasible"]]))
    for m in ("hill_climb", "annealing"):
        gaps = []
        for r in rows:
            o, io = r[m]["objective"], r["ilp"].get("objective")
            if o and io:
                gaps.append(100 * (o["mean"] - io) / io)
        out[m] = dict(feasible_runs=sum(r[m]["feasible_runs"] for r in rows), of=3 * len(rows),
                      seconds=ms([r[m]["seconds"] for r in rows]),
                      objective=ms([r[m]["objective"]["mean"] for r in rows if r[m]["objective"]]),
                      gap_to_ilp_pct=ms(gaps))
    # greedy gap on instances where it is feasible
    gg = [100 * (r["greedy"]["objective"] - r["ilp"]["objective"]) / r["ilp"]["objective"]
          for r in rows if r["greedy"]["feasible"] and r["ilp"].get("objective")]
    out["greedy"]["gap_to_ilp_pct_when_feasible"] = ms(gg)
    return out


def main():
    res = {"note": "synthetic instances; ILP via scipy milp/HiGHS with a %.0f s limit; annealing/hill climbing start from the greedy roster" % ILP_LIMIT}
    per_size = {}
    for W, D, iters, n in SIZES:
        print(f"size W={W}, D={D}", flush=True)
        rows = run_size(W, D, iters, n)
        per_size[f"{W}x{D}"] = dict(workers=W, days=D, sa_iterations=iters, instances=n, summary=summarise(rows), raw=rows)
    res["sizes"] = per_size

    # fairness-weight sensitivity: how much preference cost does fairness buy, on one size, with exact ILP
    sens = []
    inst = R.make_instance(40, 14, seed=0)
    for lam in (0.0, 1.0, 3.0, 10.0):
        R.LAM = lam
        a, info = R.ilp(inst, ILP_LIMIT)
        e = R.evaluate(inst, a)
        sens.append(dict(lam=lam, preference_cost=e["pref"], spread=e["spread"], proven_optimal=info["proven_optimal"],
                         seconds=info["seconds"]))
    R.LAM = 1.0
    res["fairness_sensitivity_40x14"] = sens
    json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=float)

    # figure: objective by method and size (relative to ILP) and runtime
    labels = list(per_size)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for m, c in (("annealing", "C0"), ("hill_climb", "C1")):
        ax[0].plot(labels, [per_size[k]["summary"][m]["gap_to_ilp_pct"]["mean"] if per_size[k]["summary"][m]["gap_to_ilp_pct"] else np.nan
                            for k in labels], "o-", color=c, label=m.replace("_", " "))
    ax[0].axhline(0, color="k", lw=0.8)
    ax[0].set_ylabel("objective gap to ILP incumbent (%)")
    ax[0].set_xlabel("workers x days")
    ax[0].set_title("Local search vs exact ILP (feasible runs only)")
    ax[0].legend()
    for key, lab in (("ilp", "ILP"), ("annealing", "annealing"), ("hill_climb", "hill climb"), ("greedy", "greedy")):
        ax[1].plot(labels, [per_size[k]["summary"][key]["seconds"]["mean"] for k in labels], "o-", label=lab)
    ax[1].set_yscale("log")
    ax[1].set_ylabel("seconds per solve (mean)")
    ax[1].set_xlabel("workers x days")
    ax[1].set_title("Runtime (ILP capped at %.0f s)" % ILP_LIMIT)
    ax[1].legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "roster_comparison.png"), dpi=140)
    plt.close()


if __name__ == "__main__":
    main()
