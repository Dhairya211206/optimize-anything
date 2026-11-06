"""Track G: measure two xv6 kernel changes against the stock kernel, under QEMU.

  feature 1: per-CPU physical-page free lists with batch stealing  (kernel variant `opt` vs `base`)
  feature 2: lottery scheduler with a settickets() system call     (kernel variant `lottery` vs `base_t`)

Usage: python trackG_xv6/run_track_g.py [build correctness feature1 feature2]   (all steps by default, about 25 minutes; results are merged into results/results.json)
IMPORTANT: QEMU runs the guest on this machine's 2 host cores with software emulation. Timer ticks are
guest timer ticks (10 MHz) driven by host time, so timing is noisy and is NOT real-hardware performance.
The spin counts (failed lock attempts) are a more direct measure of lock contention.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from xv6drive import run  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
# (workload name, command prefix, args)
WORKLOADS = [("membench", "membench", [(1, 300, 64), (3, 300, 64), (8, 100, 64)]),
             ("forkbench", "forkbench", [(3, 40), (8, 20)]),
             ("pipebench", "pipebench", [(3, 400), (8, 150)])]
REPS, SESSIONS = 5, 4
RES = re.compile(r"RESULT procs=(\d+) rounds=(\d+) pages=(\d+) ticks=(-?\d+) spins=(\d+) bad=(\d+)")
SHARE = re.compile(r"SHARE (\d+) (\d+) (\d+) permille (\d+) (\d+) (\d+)")
SCHED_CONFIGS = [(1, 1, 1), (1, 2, 4), (10, 20, 70)]


def ms(v):
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), n=len(v))


def load():
    p = os.path.join(OUT, "results.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def main(steps):
    if "build" in steps:
        subprocess.run(["bash", os.path.join(HERE, "build.sh")], check=True)
    res = load()
    res["note"] = "QEMU TCG on a 2-core host; ticks are noisy emulated-time values, not hardware timings"
    # ---- correctness: usertests -q on every variant, plus the memory-capacity check for feature 1
    corr = res.get("correctness", {})
    for v in (("base", "opt", "base_t", "lottery") if "correctness" in steps else ()):
        log = run(["usertests -q"], f"/tmp/xv6-{v}", 3, 1500)
        open(os.path.join(OUT, f"usertests_{v}.log"), "w").write(log)
        corr[v] = dict(usertests_all_passed="ALL TESTS PASSED" in log)
        if v in ("base", "opt"):
            corr[v]["memfull_pages"] = [int(x) for x in re.findall(r"RESULT pages=(\d+)", run(["memfull", "memfull"], f"/tmp/xv6-{v}", 3, 120))]
        print(v, corr[v], flush=True)
    res["correctness"] = corr
    # ---- feature 1 benchmarks
    data = {}
    for s in range(SESSIONS if "feature1" in steps else 0):
        for v in ("base", "opt"):  # interleaved so host drift hits both variants
            cmds = [f"{cmd} " + " ".join(map(str, a)) for (_, cmd, args) in WORKLOADS for a in args for _ in range(REPS)]
            out = run(cmds, f"/tmp/xv6-{v}", 3, 120)
            # attribute each RESULT line to its command by order
            rows = RES.findall(out)
            assert len(rows) == len(cmds), (len(rows), len(cmds))
            for c, (p, r, g, t, sp, bad) in zip(cmds, rows):
                data.setdefault((c.split()[0], " ".join(c.split()[1:]), v), []).append((int(t), int(sp), int(bad)))
            print(f"feature1 session={s} {v} done", flush=True)
    # one more control: a single CPU (no contention possible)
    for s in range(2 if "feature1" in steps else 0):
        for v in ("base", "opt"):
            out = run([f"membench 3 300 64" for _ in range(REPS)], f"/tmp/xv6-{v}", 1, 120)
            for (p, r, g, t, sp, bad) in RES.findall(out):
                data.setdefault(("membench(1 CPU)", "3 300 64", v), []).append((int(t), int(sp), int(bad)))
    f1 = {}
    for (name, args, v), rows in sorted(data.items()):
        f1.setdefault(f"{name} {args}", {})[v] = dict(runs=len(rows), ticks=ms([r[0] for r in rows]), spins=ms([r[1] for r in rows]),
                                                       failures=int(sum(r[2] for r in rows)))
    if "feature1" in steps:
        res["feature1_per_cpu_allocator"] = f1
    # ---- feature 2 benchmarks
    sd = {}
    for s in range(3 if "feature2" in steps else 0):
        for v in ("base_t", "lottery"):
            cmds = [f"schedbench {a} {b} {c} 500" for (a, b, c) in SCHED_CONFIGS for _ in range(REPS)]
            out = run(cmds, f"/tmp/xv6-{v}", 1, 120)
            for a, b, c, x, y, z in SHARE.findall(out):
                sd.setdefault(((int(a), int(b), int(c)), v), []).append((int(x), int(y), int(z)))
            print(f"feature2 session={s} {v} done", flush=True)
    f2 = {}
    for ((tk, v), rows) in sorted(sd.items()):
        rows = np.array(rows) / 10.0  # percent
        ideal = 100 * np.array(tk) / sum(tk)
        err = np.abs(rows - ideal).mean(axis=1)
        f2.setdefault(str(tk), {})[v] = dict(ideal_percent=ideal.tolist(), mean_share_percent=rows.mean(axis=0).tolist(),
                                              std_share_percent=rows.std(axis=0).tolist(), mean_abs_error_points=ms(err), runs=len(rows))
    if "feature2" in steps:
        res["feature2_lottery_scheduler"] = f2
    json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    for k, d in res.get("feature1_per_cpu_allocator", {}).items():
        b, o = d["base"], d["opt"]
        print(f"{k}: ticks base {b['ticks']['mean']:.0f}+-{b['ticks']['std']:.0f} opt {o['ticks']['mean']:.0f}+-{o['ticks']['std']:.0f}  "
              f"spins base {b['spins']['mean']:.0f} opt {o['spins']['mean']:.0f}")
    for k, d in res.get("feature2_lottery_scheduler", {}).items():
        print(k, {v: (np.round(x["mean_share_percent"], 1).tolist(), round(x["mean_abs_error_points"]["mean"], 1)) for v, x in d.items()})
    print(res.get("correctness"))


if __name__ == "__main__":
    main(sys.argv[1:] or ["build", "correctness", "feature1", "feature2"])
