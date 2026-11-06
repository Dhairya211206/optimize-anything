"""Track J: test-suite minimisation and prioritisation for this repository's own code (Tracks A-F), checked with mutation testing.

Usage (repo root): python trackJ_software_eng/run_track_j.py [coverage fault]
  coverage : per-test line coverage and run time for all Tracks A-F tests, whole-suite minimisation (set cover: ILP vs greedy vs random)
  fault    : mutation study on the Track F compiler (frontend/opt/regalloc/vm) and the 21 Track F tests: how much fault detection does a
             coverage-preserving minimal suite lose, and how good are the prioritisation orders (APFD)
The codebase under test is about 4,500 lines of Python (see results). No claim is made about other projects.
"""
import json
import os
import subprocess
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import collect as co  # noqa: E402
import mutate as mu  # noqa: E402
import setcover as sc  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
RES = os.path.join(OUT, "results.json")
TRACKS = ["trackA_continuous", "trackB_discrete", "trackC_quantum", "trackD_submodular_parallel", "trackE_case_study", "trackF_compiler"]
N_MUTANTS = int(os.environ.get("TRACK_J_MUTANTS", "90"))


def save(key, value):
    r = json.load(open(RES)) if os.path.exists(RES) else {}
    r[key] = value
    json.dump(r, open(RES, "w"), indent=1, default=float)


def ms(v):
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), n=len(v))


def count_lines(paths):
    n = 0
    for p in paths:
        for dp, _, fs in os.walk(os.path.join(ROOT, p)):
            if "results" in dp or "__pycache__" in dp:
                continue
            for f in fs:
                if f.endswith(".py"):
                    n += sum(1 for _ in open(os.path.join(dp, f)))
    return n


def load_suite(paths):
    dur = co.test_durations(ROOT, paths)
    raw = co.test_coverage(ROOT, paths)
    cover = {co.normalise_name(k): v for k, v in raw.items()}
    names = sorted(set(cover) & set(dur))
    return {t: cover[t] for t in names}, {t: dur[t] for t in names}, dur


def evaluate_subset(chosen, cover, cost):
    return dict(tests=len(chosen), seconds=float(sum(cost[t] for t in chosen)), line_coverage=sc.covered_fraction(chosen, cover))


def exp_coverage():
    cover, cost, dur_all = load_suite(TRACKS)
    total = sum(cost.values())
    slow = sorted(cost.items(), key=lambda kv: -kv[1])[:6]
    out = dict(lines_of_python=count_lines(TRACKS), tests=len(cover), covered_lines=len(sc.universe(cover)), suite_seconds=total,
               slowest_tests=[dict(test=t, seconds=s, share=s / total) for t, s in slow])
    rng = np.random.default_rng(0)
    methods = {}
    ilp_t, info = sc.ilp_min_cost(cover, cost)
    methods["ILP, minimise run time"] = ilp_t
    methods["ILP, minimise test count"] = sc.ilp_min_cost(cover, {t: 1.0 for t in cover})[0]
    methods["greedy, most new lines"] = sc.greedy(cover, cost, "count")
    methods["greedy, new lines per second"] = sc.greedy(cover, cost, "ratio")
    methods["original order until covered"] = sc.until_covered(sorted(cover), cover)
    methods["fastest first until covered"] = sc.until_covered(sorted(cover, key=lambda t: cost[t]), cover)
    out["methods"] = {k: evaluate_subset(v, cover, cost) for k, v in methods.items()}
    out["methods"]["ILP, minimise run time"]["proven_optimal"] = info["proven_optimal"]
    rnd = [sc.until_covered(list(rng.permutation(sorted(cover))), cover) for _ in range(500)]
    out["methods"]["random order until covered (500 draws)"] = dict(
        tests=ms([len(r) for r in rnd]), seconds=ms([sum(cost[t] for t in r) for r in rnd]), line_coverage=1.0)
    out["chosen_by_ilp"] = ilp_t
    save("whole_suite", out)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    names = [k for k in out["methods"] if "random" not in k]
    ax.barh(names, [out["methods"][k]["seconds"] for k in names])
    ax.axvline(total, color="r", ls="--", label=f"full suite {total:.1f}s")
    ax.set_xlabel("sum of test run times (s), same 100% line coverage")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "minimisation.png"), dpi=140)
    plt.close()


def exp_fault():
    paths = ["trackF_compiler"]
    mods = ["frontend.py", "opt.py", "regalloc.py", "vm.py"]
    cover_all, cost_all, _ = load_suite(paths)
    keep = {t for t in cover_all if t.startswith("test_track_f.")}
    # restrict the requirement universe to the four mutated modules
    cover = {t: {(f, l) for (f, l) in cover_all[t] if os.path.basename(f) in mods} for t in keep}
    cost = {t: cost_all[t] for t in keep}
    src_lines = count_lines(["trackF_compiler"])
    t0 = time.perf_counter()
    mutants = mu.kill_matrix(os.path.join(ROOT, "trackF_compiler"), mods, N_MUTANTS, seed=0, log=lambda m: print(m, flush=True))
    mut_seconds = time.perf_counter() - t0
    valid = [m for m in mutants if m["status"] in ("killed", "ok")]
    kills = {i: {"test_track_f." + n for n in m["killed_by"]} & keep for i, m in enumerate(valid) if m["status"] == "killed"}
    out = dict(code_lines_trackF=src_lines, mutants_generated=len(mutants), status_counts={s: sum(m["status"] == s for m in mutants)
                                                                                           for s in ("killed", "ok", "crash", "timeout")},
               full_suite_mutation_score=len(kills) / max(len(valid), 1), survivors=[(m["module"], m["site"]) for m in valid if m["status"] == "ok"],
               mutation_seconds=mut_seconds, tests=len(keep), suite_seconds=float(sum(cost.values())))
    # which tests are the only killer of some mutant?
    sole = {}
    for i, ts in kills.items():
        if len(ts) == 1:
            sole[next(iter(ts))] = sole.get(next(iter(ts)), 0) + 1
    out["tests_that_are_sole_killer_of_mutants"] = sole
    rng = np.random.default_rng(1)

    def score(subset):
        return sum(bool(ts & set(subset)) for ts in kills.values()) / max(len(kills), 1)

    subsets = {
        "full suite": sorted(keep),
        "ILP, minimise run time": sc.ilp_min_cost(cover, cost)[0],
        "ILP, minimise test count": sc.ilp_min_cost(cover, {t: 1.0 for t in cover})[0],
        "greedy, most new lines": sc.greedy(cover, cost, "count"),
        "greedy, new lines per second": sc.greedy(cover, cost, "ratio"),
        "fastest first until covered": sc.until_covered(sorted(cover, key=lambda t: cost[t]), cover),
        "drop the slowest test": sorted(keep - {max(cost, key=cost.get)}),
    }
    out["subsets"] = {}
    for k, s in subsets.items():
        e = evaluate_subset(s, cover, cost)
        e["mutation_score_of_subset"] = score(s)
        e["fraction_of_full_suite_kills_kept"] = score(s)  # score is already relative to mutants the full suite kills
        e["tests_list"] = sorted(s)
        out["subsets"][k] = e
    # random subsets of the same size as the ILP(time) subset, for reference
    size = len(subsets["ILP, minimise run time"])
    draws = [list(rng.choice(sorted(keep), size, replace=False)) for _ in range(500)]
    out["random_same_size_as_ilp"] = dict(size=size, mutation_score=ms([score(d) for d in draws]),
                                          line_coverage=ms([sc.covered_fraction(d, cover) for d in draws]))
    # prioritisation
    orders = {
        "original order": sorted(keep),
        "reverse order": sorted(keep, reverse=True),
        "fastest first": sorted(keep, key=lambda t: cost[t]),
        "greedy, most new lines": sc.greedy_order(cover, cost, "count"),
        "greedy, new lines per second": sc.greedy_order(cover, cost, "ratio"),
        "ILP-minimal subset first": subsets["ILP, minimise run time"] + sorted(keep - set(subsets["ILP, minimise run time"])),
    }

    def time_to_all(order):
        need = set()
        for ts in kills.values():
            need.add(min(order.index(t) for t in ts if t in order))
        pos = max(need)
        return float(sum(cost[t] for t in order[:pos + 1]))

    out["prioritisation"] = {k: dict(apfd=sc.apfd(o, kills), seconds_until_every_detectable_mutant_is_caught=time_to_all(o))
                             for k, o in orders.items()}
    rnd = [list(rng.permutation(sorted(keep))) for _ in range(500)]
    out["prioritisation"]["random order (500 draws)"] = dict(apfd=ms([sc.apfd(r, kills) for r in rnd]),
                                                             seconds_until_every_detectable_mutant_is_caught=ms([time_to_all(r) for r in rnd]))
    # realised wall-clock: run the full Track F suite and the ILP subset with pytest
    ids = subprocess.run([sys.executable, "-m", "pytest", "trackF_compiler", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    idmap = {"test_track_f." + i.split("::")[-1]: i for i in ids if "::" in i}
    wall = {}
    for label, s in (("full suite", subsets["full suite"]), ("ILP, minimise run time", subsets["ILP, minimise run time"])):
        ts = []
        for _ in range(3):
            t0 = time.perf_counter()
            subprocess.run([sys.executable, "-m", "pytest", *[idmap[t] for t in s], "-q", "-p", "no:cacheprovider", "-W", "ignore"],
                           cwd=ROOT, capture_output=True, text=True)
            ts.append(time.perf_counter() - t0)
        wall[label] = ms(ts)
    out["wall_clock_seconds_pytest_including_startup"] = wall
    save("fault_study_trackF", out)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ks = list(out["subsets"])
    ax.barh(ks, [100 * out["subsets"][k]["mutation_score_of_subset"] for k in ks])
    ax.set_xlabel("% of the mutants the full suite kills that this subset also kills")
    ax.set_title("Track F: fault detection kept by each reduced suite")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fault_detection.png"), dpi=140)
    plt.close()


if __name__ == "__main__":
    for step in sys.argv[1:] or ["coverage", "fault"]:
        t0 = time.perf_counter()
        {"coverage": exp_coverage, "fault": exp_fault}[step]()
        print(f"[{step}] finished in {time.perf_counter() - t0:.1f}s", flush=True)
