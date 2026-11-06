"""Track D experiments: submodular greedy, parallel computing, FedAvg, multi-task weighting.

Usage (from the repo root):  python trackD_submodular_parallel/run_track_d.py [submodular parallel fedavg multitask]
Results are merged into trackD_submodular_parallel/results/results.json after each experiment.

Honesty notes:
  * This machine has 2 CPU cores, so real (measured) speedups cannot exceed about 2.
  * Anything with more workers than 2 comes from a discrete-event SIMULATION and is labelled so.
  * Federated clients are simulated on one machine; "communication" is counted in rounds, not measured.
"""
import os

# One BLAS thread per process so numpy does not parallelise behind our back and distort the speedups.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import federated as fd  # noqa: E402
import multitask as mt  # noqa: E402
import parallel_exp as pe  # noqa: E402
import submodular as sm  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
RES = os.path.join(OUT, "results.json")


def save(key, value):
    r = json.load(open(RES)) if os.path.exists(RES) else {}
    r[key] = value
    json.dump(r, open(RES, "w"), indent=1, default=float)


def ms(v):
    return dict(mean=float(np.mean(v)), std=float(np.std(v)))


# ======================================================================== submodular
def exp_submodular():
    out = {"guarantee": "greedy >= (1 - 1/e) OPT = 0.632 OPT requires monotone + submodular + f(empty) >= 0"}
    # (1) check the conditions for each objective BEFORE trusting any guarantee
    r, R = sm.load_trackb_objective()
    objs = {
        "facility location": sm.FacilityLocation(100, 15, seed=0),
        "relevance - redundancy (Track B)": sm.PenalisedSelection(r, R),
        "relevance + synergy": sm.SynergySelection(r, R),
    }
    out["conditions"] = {k: sm.check_conditions(f, f.n) for k, f in objs.items()}
    # (2) greedy against the exact optimum (n small enough for exhaustive search)
    ratios = {}
    fl = []
    for seed in range(10):
        f = sm.FacilityLocation(150, 16, seed=seed)
        _, g = sm.greedy(f, f.n, 4)
        _, opt = sm.brute_force(f, f.n, 4)
        fl.append(g / opt)
    ratios["facility location (n=16, k=4, 10 instances)"] = dict(min=float(min(fl)), mean=float(np.mean(fl)),
                                                              meets_guarantee=bool(min(fl) >= 1 - 1 / np.e))
    for name, cls in (("relevance - redundancy (Track B)", sm.PenalisedSelection), ("relevance + synergy", sm.SynergySelection)):
        row = []
        for k in (3, 4, 5, 6):
            f = cls(r, R)
            _, g = sm.greedy(f, f.n, k)
            _, opt = sm.brute_force(cls(r, R), len(r), k)
            row.append(dict(k=k, greedy=g, optimum=opt, ratio=g / opt))
        ratios[name + " (n=12)"] = row
    out["greedy_vs_optimum"] = ratios
    # (3) lazy greedy: same answer, far fewer function evaluations (valid only because f is submodular)
    f1, f2 = sm.FacilityLocation(400, 500, seed=1), sm.FacilityLocation(400, 500, seed=1)
    t0 = time.perf_counter()
    _, v1 = sm.greedy(f1, f1.n, 20)
    t1 = time.perf_counter()
    _, v2 = sm.lazy_greedy(f2, f2.n, 20)
    t2 = time.perf_counter()
    out["lazy_greedy"] = dict(n=500, k=20, standard_calls=f1.calls, lazy_calls=f2.calls,
                              standard_seconds=t1 - t0, lazy_seconds=t2 - t1, same_value=bool(abs(v1 - v2) < 1e-9))
    save("submodular", out)


# ======================================================================== parallel
def exp_parallel():
    out = {"cpu_cores": os.cpu_count(), "note": "measured with real processes; only 2 cores, so speedup <= ~2"}
    tasks = [200_000] * 64
    # --- strong scaling (fixed problem) ---
    base = None
    rows = []
    for p in (1, 2, 4):
        _, t = pe.timed(lambda: pe.run_data_parallel(tasks, p), repeats=3)
        base = base or t
        rows.append(dict(workers=p, seconds=t, speedup=base / t, efficiency=base / t / p))
    s2 = pe.serial_fraction_from_speedup(rows[1]["speedup"], 2)
    for r in rows:
        r["amdahl_prediction_from_p2"] = pe.amdahl_speedup(s2, r["workers"])
    out["strong_scaling"] = dict(rows=rows, serial_fraction_estimated_from_p2=s2,
                                 caveat="serial fraction inferred from the p=2 point; p=4 exceeds the 2 physical cores")
    # --- weak scaling / Gustafson (problem grows with workers) ---
    t1 = rows[0]["seconds"]
    weak = []
    for p in (1, 2, 4):
        big = [200_000] * (64 * p)
        _, tp = pe.timed(lambda: pe.run_data_parallel(big, p), repeats=2)
        weak.append(dict(workers=p, seconds=tp, scaled_speedup=p * t1 / tp, scaled_efficiency=t1 / tp))
    out["weak_scaling"] = weak
    # --- real load balancing on skewed task sizes, 2 workers ---
    rng = np.random.default_rng(0)
    sizes = (rng.lognormal(0, 1.2, 60) * 150_000).astype(int) + 1000
    # The static strategies get the worst-case-ish ordering: sorted so one block holds the big tasks.
    ordered = sorted(sizes.tolist(), reverse=True)
    _, t_serial = pe.timed(lambda: [pe.work(n) for n in ordered], repeats=1)
    lb = max(t_serial / 2, max(ordered) / sum(ordered) * t_serial)
    lbal = {"serial_seconds": t_serial, "ideal_makespan_2_workers": lb}
    for name, fn in (("static blocks", lambda: pe.run_static_blocks(ordered, 2)),
                     ("static round-robin", lambda: pe.run_static_round_robin(ordered, 2)),
                     ("dynamic (shared queue)", lambda: pe.run_dynamic(ordered, 2)),
                     ("dynamic, longest first", lambda: pe.run_dynamic(ordered, 2, lpt=True))):
        _, t = pe.timed(fn, repeats=3)
        lbal[name] = dict(seconds=t, ratio_to_ideal=t / lb)
    out["load_balancing_measured_2_workers"] = lbal
    # --- SIMULATED scheduling with many workers ---
    costs = np.random.default_rng(1).lognormal(0, 1.0, 1000)
    costs = costs / costs.mean()
    sim = []
    for p in (4, 8, 16, 32):
        lb = max(costs.sum() / p, costs.max())
        row = dict(workers=p, lower_bound=float(lb))
        for s in ("static_block", "round_robin", "dynamic", "lpt"):
            row[s] = float(pe.simulate_schedule(costs, p, s)[0] / lb)
        ws, steals = pe.simulate_schedule(costs, p, "work_stealing", steal_cost=0.02, steal_locality_penalty=0.2)
        row["work_stealing"] = float(ws / lb)
        row["steals"] = int(steals)
        sim.append(row)
    out["scheduling_simulated_ratio_to_lower_bound"] = sim
    # --- SIMULATED overhead vs task granularity (8 workers, 2000 tasks) ---
    over = []
    base_costs = np.random.default_rng(2).lognormal(0, 1.0, 2000)
    base_costs = base_costs / base_costs.mean()
    for mean_cost in (0.02, 0.1, 0.5, 2.0, 10.0):
        c = base_costs * mean_cost
        lb = max(c.sum() / 8, c.max())
        over.append(dict(
            mean_task_cost=mean_cost,
            static_block=float(pe.simulate_schedule(c, 8, "static_block")[0] / lb),
            dynamic_with_dispatch_cost=float(pe.simulate_schedule(c, 8, "dynamic", dispatch_cost=0.05)[0] / lb),
            work_stealing=float(pe.simulate_schedule(c, 8, "work_stealing", steal_cost=0.05, steal_locality_penalty=0.2)[0] / lb)))
    out["overhead_vs_granularity_simulated"] = dict(dispatch_or_steal_cost=0.05, rows=over)
    # --- pipeline parallelism (real processes; stage work simulated with sleep) ---
    pipe = []
    for label, st in (("balanced 3 x 30 ms", [0.03, 0.03, 0.03]), ("unbalanced 20/60/20 ms", [0.02, 0.06, 0.02])):
        m = 30
        measured, got = pe.run_pipeline(st, m)
        seq = m * sum(st)
        ideal = sum(st) + (m - 1) * max(st)
        pipe.append(dict(stages=label, microbatches=m, sequential_seconds=seq, ideal_pipeline_seconds=ideal,
                         measured_seconds=measured, measured_speedup=seq / measured, ideal_speedup=seq / ideal))
    out["pipeline_parallelism"] = dict(note="stage work is time.sleep, so this measures overlap and queue overhead, not compute", rows=pipe)
    # --- model parallelism: one layer split across 2 processes ---
    mp_rows = []
    rngm = np.random.default_rng(0)
    x = rngm.normal(size=(256, 2048))
    for h in (512, 2048, 8192):
        w = rngm.normal(size=(2048, h)).astype(float)
        single, par = pe.run_model_parallel(x, w, repeats=3)
        mp_rows.append(dict(hidden=h, single_process_s=single, two_process_s=par, speedup=single / par))
    out["model_parallelism"] = dict(note="x batch is sent to both workers on every call, so communication is included", rows=mp_rows)
    save("parallel", out)

    # figures
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ps = [r["workers"] for r in rows]
    ax[0].plot(ps, [r["speedup"] for r in rows], "o-", label="measured")
    ax[0].plot(ps, [r["amdahl_prediction_from_p2"] for r in rows], "s--", label="Amdahl (s fitted at p=2)")
    ax[0].plot(ps, ps, "k:", label="ideal")
    ax[0].set_xlabel("workers (machine has 2 cores)")
    ax[0].set_ylabel("speedup")
    ax[0].set_title("Strong scaling (measured)")
    ax[0].legend(fontsize=8)
    names = ["static_block", "round_robin", "dynamic", "lpt", "work_stealing"]
    for s in names:
        ax[1].plot([r["workers"] for r in sim], [r[s] for r in sim], "o-", label=s)
    ax[1].set_xlabel("workers (SIMULATED)")
    ax[1].set_ylabel("makespan / lower bound")
    ax[1].set_title("Scheduling, 1000 skewed tasks (simulated)")
    ax[1].legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "parallel.png"), dpi=140)
    plt.close()


# ======================================================================== FedAvg
def exp_fedavg(n_seeds=5, rounds=40):
    out = {}
    curves = {}
    for dist in ("iid", "non_iid"):
        res = {}
        for E in (1, 5, 20):
            finals, at10, evals = [], [], None
            hs = []
            for s in range(n_seeds):
                clients, test = fd.make_clients(10, 200, 20, non_iid=(dist == "non_iid"), seed=s)
                _, hist, evals = fd.fedavg(clients, test, rounds, E, lr=0.1, batch=20, seed=s)
                finals.append(hist[-1])
                at10.append(hist[9])
                hs.append([h[1] for h in hist])
            res[f"FedAvg E={E}"] = dict(
                rounds=rounds, communication_rounds=rounds, sample_gradients=evals,
                test_acc_round10=ms([x[1] for x in at10]), test_acc_final=ms([x[1] for x in finals]),
                test_loss_final=ms([x[0] for x in finals]))
            curves[(dist, E)] = np.mean(hs, axis=0)
        for label, steps in (("centralized SGD, same number of sequential steps as FedAvg E=5", rounds * 5),
                             ("centralized SGD, same total gradient work as FedAvg E=5", rounds * 5 * 10)):
            finals = []
            for s in range(n_seeds):
                clients, test = fd.make_clients(10, 200, 20, non_iid=(dist == "non_iid"), seed=s)
                _, hist, ev = fd.centralized_sgd(clients, test, steps, lr=0.1, batch=20, seed=s)
                finals.append(hist[-1])
            res[label] = dict(steps=steps, sample_gradients=steps * 20,
                              communication_rounds_if_distributed=steps,
                              test_acc_final=ms([x[1] for x in finals]), test_loss_final=ms([x[0] for x in finals]))
        out[dist] = res
    save("fedavg", out)
    fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for k, dist in enumerate(("iid", "non_iid")):
        for E in (1, 5, 20):
            ax[k].plot(np.arange(1, rounds + 1), curves[(dist, E)], label=f"E={E}")
        ax[k].set_title(f"FedAvg, {dist.replace('_', '-')} clients")
        ax[k].set_xlabel("communication round")
        ax[k].grid(alpha=0.3)
    ax[0].set_ylabel("test accuracy (mean of 5 seeds)")
    ax[0].legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fedavg.png"), dpi=140)
    plt.close()


# ======================================================================== multi-task
def exp_multitask(n_seeds=5):
    res = {m: dict(t1=[], t2=[], w=[]) for m in ("equal", "mgda", "gradnorm")}
    for s in range(n_seeds):
        # make_data draws new random task directions per seed, so train and test come from one draw, split in half.
        X, Y = mt.make_data(1200, 8, seed=s)
        Xtr, Ytr, Xte, Yte = X[:600], Y[:600], X[600:], Y[600:]
        for m in res:
            net, wh = mt.train(m, Xtr, Ytr, steps=1500, lr=0.01, seed=s)
            rel = mt.relative_mse(net, Xte, Yte)
            res[m]["t1"].append(rel[0])
            res[m]["t2"].append(rel[1])
            res[m]["w"].append(wh[-1])
    out = {m: dict(task1_rel_mse=ms(v["t1"]), task2_rel_mse=ms(v["t2"]),
                   mean_rel_mse=ms((np.array(v["t1"]) + np.array(v["t2"])) / 2),
                   final_task_weights=np.mean(v["w"], axis=0).tolist()) for m, v in res.items()}
    out["note"] = "test relative MSE = MSE / variance of that task's targets (0 = perfect, 1 = no better than the mean)"
    save("multitask", out)
    fig, ax = plt.subplots(figsize=(6, 4))
    w = 0.25
    for k, m in enumerate(("equal", "mgda", "gradnorm")):
        ax.bar(np.arange(2) + k * w, [out[m]["task1_rel_mse"]["mean"], out[m]["task2_rel_mse"]["mean"]], w,
               yerr=[out[m]["task1_rel_mse"]["std"], out[m]["task2_rel_mse"]["std"]], capsize=3, label=m)
    ax.set_xticks(np.arange(2) + w)
    ax.set_xticklabels(["task 1 (small scale)", "task 2 (25x scale)"])
    ax.set_ylabel("test relative MSE (lower is better)")
    ax.legend()
    ax.set_title("Two-task model, 5 seeds")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "multitask.png"), dpi=140)
    plt.close()


EXPERIMENTS = dict(submodular=exp_submodular, parallel=exp_parallel, fedavg=exp_fedavg, multitask=exp_multitask)

if __name__ == "__main__":
    for name in sys.argv[1:] or list(EXPERIMENTS):
        t0 = time.perf_counter()
        EXPERIMENTS[name]()
        print(f"[{name}] finished in {time.perf_counter() - t0:.1f}s", flush=True)
