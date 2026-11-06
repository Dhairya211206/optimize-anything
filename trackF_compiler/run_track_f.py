"""Track F experiments: optimisation-pass ablation, fuzz validation, register allocation (greedy vs ILP).

Usage (repo root): python trackF_compiler/run_track_f.py
Everything is measured on the project's own VM. The cost model (mul = 3 cycles, others 1) is an assumption.
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
import frontend as fe  # noqa: E402
import opt  # noqa: E402
import regalloc as ra  # noqa: E402
import vm  # noqa: E402
from fuzz import random_program  # noqa: E402
from programs import PROGRAMS  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)


def ms(v):
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), n=len(v))


def metrics(code, ref_out):
    r = vm.run(code)
    return dict(static=vm.static_count(code), dynamic=r["dyn"], cost=r["cost"], correct=bool(r["out"] == ref_out))


def timed_opt(code, passes, repeats=5):
    ts = []
    for _ in range(repeats):
        t = time.perf_counter()
        out = opt.optimize(code, passes)
        ts.append(time.perf_counter() - t)
    return out, 1000 * float(np.median(ts))


# ------------------------------------------------------------------ F1: ablation on named benchmarks
def exp_ablation():
    configs = {"none": [], "all": opt.DEFAULT_ORDER}
    for p in opt.DEFAULT_ORDER:
        configs[f"only {p}"] = [p]
    for p in opt.DEFAULT_ORDER:
        configs[f"all minus {p}"] = [q for q in opt.DEFAULT_ORDER if q != p]
    res = {}
    for name, src in PROGRAMS.items():
        ast = fe.parse(src)
        ref = fe.interpret(ast)
        base = fe.compile_ast(ast)
        res[name] = {}
        for cname, passes in configs.items():
            code, ms_ = timed_opt(base, passes)
            m = metrics(code, ref)
            m["compile_ms"] = ms_
            res[name][cname] = m
    # summary: geometric mean of weighted-cost ratio to "none", per config
    summ = {}
    for cname in configs:
        ratios = [res[p][cname]["cost"] / res[p]["none"]["cost"] for p in PROGRAMS]
        dyn = [res[p][cname]["dynamic"] / res[p]["none"]["dynamic"] for p in PROGRAMS]
        sta = [res[p][cname]["static"] / res[p]["none"]["static"] for p in PROGRAMS]
        summ[cname] = dict(cost_ratio_geomean=float(np.exp(np.mean(np.log(ratios)))),
                           dynamic_ratio_geomean=float(np.exp(np.mean(np.log(dyn)))),
                           static_ratio_geomean=float(np.exp(np.mean(np.log(sta)))),
                           all_correct=all(res[p][cname]["correct"] for p in PROGRAMS))
    return dict(per_program=res, summary=summ)


# ------------------------------------------------------------------ F2: fuzz (random programs)
def exp_fuzz(n=400):
    configs = {"all": opt.DEFAULT_ORDER}
    for p in opt.DEFAULT_ORDER:
        configs[f"only {p}"] = [p]
    mism = {c: 0 for c in configs}
    ratios = {c: [] for c in configs}
    tested = skipped = 0
    for seed in range(n):
        ast = random_program(1000 + seed, depth=2, size=7)
        try:
            ref = fe.interpret(ast)
        except RuntimeError:
            skipped += 1
            continue
        base = fe.compile_ast(ast)
        r0 = vm.run(base)
        assert r0["out"] == ref
        tested += 1
        for c, passes in configs.items():
            code = opt.optimize(base, passes)
            r = vm.run(code)
            if r["out"] != ref:
                mism[c] += 1
            ratios[c].append(r["cost"] / r0["cost"])
    return dict(programs_tested=tested, skipped_step_limit=skipped, output_mismatches=mism,
                cost_ratio_to_unoptimised={c: ms(v) for c, v in ratios.items()})


# ------------------------------------------------------------------ F3: register allocation
def exp_regalloc():
    Ks = [2, 3, 4, 6, 8]
    res = {}
    for name, src in PROGRAMS.items():
        base = fe.compile_source(src)
        for label, code in (("unoptimised", base), ("optimised", opt.optimize(base))):
            prof = vm.run(code)
            iv, refs = ra.intervals_and_refs(code)
            ws, wd = ra.weights(code, refs), ra.weights(code, refs, prof["counts"])
            rows = []
            for K in Ks:
                row = dict(K=K, variables=len(iv), max_live=ra.max_pressure(iv, set(iv)))
                methods = {"linear_scan": (ra.linear_scan(iv, K), None),
                           "greedy_weight": (ra.greedy_weight(iv, ws, K), None)}
                t = time.perf_counter()
                s_ilp, info = ra.ilp_alloc(iv, ws, K)
                info["seconds"] = time.perf_counter() - t
                methods["ilp_static"] = (s_ilp, info)
                s_pgo, info2 = ra.ilp_alloc(iv, wd, K)
                methods["ilp_profile"] = (s_pgo, info2)
                for m, (spilled, inf) in methods.items():
                    kept = set(iv) - spilled
                    assert ra.max_pressure(iv, kept) <= K
                    ra.assign_registers(iv, kept, K)
                    row[m] = dict(spilled_vars=len(spilled), static_cost=ra.spill_cost(spilled, ws),
                                  dynamic_memory_ops=ra.spill_cost(spilled, wd),
                                  proven_optimal=None if inf is None else inf.get("proven_optimal"))
                row["ilp_seconds"] = info["seconds"]
                rows.append(row)
            res[f"{name} [{label}]"] = dict(total_dynamic_refs=ra.spill_cost(set(iv), wd), rows=rows)
    return res


def regalloc_summary(res, label="optimised", K=4):
    keys = [k for k in res if k.endswith(f"[{label}]")]
    out = {}
    for m in ("linear_scan", "greedy_weight", "ilp_static", "ilp_profile"):
        out[m] = dict(dyn_ops=[], static=[])
    for k in keys:
        row = [r for r in res[k]["rows"] if r["K"] == K][0]
        for m in out:
            out[m]["dyn_ops"].append(row[m]["dynamic_memory_ops"])
            out[m]["static"].append(row[m]["static_cost"])
    return {m: dict(total_dynamic_memory_ops=float(sum(v["dyn_ops"])), total_static_cost=float(sum(v["static"])))
            for m, v in out.items()}


def exp_regalloc_fuzz(n=100, K=4):
    """Regret of each heuristic to the ILP on random optimised programs (static weights)."""
    reg = {"linear_scan": [], "greedy_weight": []}
    ties = {"linear_scan": 0, "greedy_weight": 0}
    used = 0
    for seed in range(n):
        ast = random_program(5000 + seed, depth=2, size=8)
        try:
            fe.interpret(ast)
        except RuntimeError:
            continue
        code = opt.optimize(fe.compile_ast(ast))
        iv, refs = ra.intervals_and_refs(code)
        ws = ra.weights(code, refs)
        if ra.max_pressure(iv, set(iv)) <= K:
            continue  # nothing to decide
        used += 1
        best = ra.spill_cost(ra.ilp_alloc(iv, ws, K)[0], ws)
        for m, s in (("linear_scan", ra.linear_scan(iv, K)), ("greedy_weight", ra.greedy_weight(iv, ws, K))):
            c = ra.spill_cost(s, ws)
            reg[m].append(100 * (c - best) / max(best, 1e-9))
            ties[m] += int(abs(c - best) < 1e-9)
    return dict(K=K, programs_needing_spills=used,
                excess_static_spill_cost_pct_vs_ilp={m: ms(v) for m, v in reg.items() if v},
                matches_ilp={m: f"{ties[m]}/{used}" for m in ties})


def main():
    t0 = time.perf_counter()
    res = {"note": "VM cost model is an assumption (mul=3, other=1). All numbers measured on the project's own VM."}
    res["ablation"] = exp_ablation()
    print("ablation done", flush=True)
    res["fuzz"] = exp_fuzz()
    print("fuzz done", flush=True)
    res["regalloc"] = exp_regalloc()
    res["regalloc_summary_K4_optimised"] = regalloc_summary(res["regalloc"], "optimised", 4)
    res["regalloc_summary_K4_unoptimised"] = regalloc_summary(res["regalloc"], "unoptimised", 4)
    res["regalloc_fuzz"] = exp_regalloc_fuzz()
    json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=float)
    print(f"finished in {time.perf_counter() - t0:.1f}s")

    # figure 1: weighted-cost ratio per benchmark, none vs only-X vs all
    names = list(PROGRAMS)
    cfgs = ["all"] + [f"only {p}" for p in opt.DEFAULT_ORDER]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    w = 0.8 / len(cfgs)
    for k, c in enumerate(cfgs):
        ax.bar(np.arange(len(names)) + k * w, [res["ablation"]["per_program"][p][c]["cost"] / res["ablation"]["per_program"][p]["none"]["cost"]
                                              for p in names], w, label=c)
    ax.set_xticks(np.arange(len(names)) + 0.4)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("weighted cost / unoptimised (lower is better)")
    ax.legend(fontsize=7, ncol=4)
    ax.set_title("Which pass helps which program (VM cost model, mul = 3)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "passes.png"), dpi=140)
    plt.close()

    # figure 2: dynamic spill traffic vs K for the register-pressure benchmark
    rows = res["regalloc"]["register_pressure [optimised]"]["rows"]
    fig, ax = plt.subplots(figsize=(6, 4))
    for m in ("linear_scan", "greedy_weight", "ilp_static", "ilp_profile"):
        ax.plot([r["K"] for r in rows], [r[m]["dynamic_memory_ops"] for r in rows], "o-", label=m)
    ax.set_xlabel("registers K")
    ax.set_ylabel("dynamic memory accesses from spills")
    ax.set_title("register_pressure, optimised code")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "regalloc.png"), dpi=140)
    plt.close()


if __name__ == "__main__":
    main()
