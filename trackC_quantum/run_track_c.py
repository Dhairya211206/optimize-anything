"""Track C: quantum optimization experiments. ALL RESULTS ARE SIMULATIONS (no quantum hardware).

Usage (from the repo root), any subset of experiments, default = all:
    python trackC_quantum/run_track_c.py qaoa grad shots noise barren vqe
Results are merged into trackC_quantum/results/results.json after each experiment.

Seeds: hyperparameters are tuned on seeds >= 100 and evaluation uses seeds 0..N-1, so tuning
and evaluation never share a random start.
"""
import json
import os
import sys
import time
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import barren as bp  # noqa: E402
import qaoa_sim as qs  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
RES_PATH = os.path.join(OUT, "results.json")
INSTANCE = os.path.join(HERE, "..", "trackB_discrete", "results", "maxcut_instance.json")


def load_results():
    return json.load(open(RES_PATH)) if os.path.exists(RES_PATH) else {}


def save(key, value):
    r = load_results()
    r[key] = value
    json.dump(r, open(RES_PATH, "w"), indent=1, default=float)


def problem():
    inst = json.load(open(INSTANCE))
    return qs.MaxCutQAOA(inst["n"], inst["edges"])


def init(p, seed):
    rng = np.random.default_rng(seed)
    return np.r_[rng.uniform(0, np.pi, p), rng.uniform(0, np.pi / 2, p)]


def stats(v):
    """For quantities where HIGHER is better (approximation ratio, probability)."""
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), best=float(np.max(v)), worst=float(np.min(v)))


def stats_err(v):
    """For quantities where LOWER is better (energy error): explicit min and max, no best/worst labels."""
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), min=float(np.min(v)), max=float(np.max(v)))


# ============================================================ E1: QAOA + optimizer comparison
def exp_qaoa(budget=4000, n_seeds=20):
    q = problem()
    out = dict(optimal_cut=q.max_cut, random_guess_ratio=float((q.m / 2) / q.max_cut),
               random_guess_prob_optimal=float(q.opt_mask.sum() / len(q.cut)), budget_circuit_evals=budget)
    # p = 1 landscape by dense grid: the true best (gamma, beta), to judge how good the optimizers get
    gs, bs = np.linspace(0, np.pi, 90), np.linspace(0, np.pi / 2, 90)
    E = np.array([[q.energy(np.array([g, b])) for b in bs] for g in gs])
    i, j = np.unravel_index(np.argmin(E), E.shape)
    out["p1_grid_best"] = dict(gamma=float(gs[i]), beta=float(bs[j]), **q.summary(np.array([gs[i], bs[j]])))
    plt.figure(figsize=(5.5, 4.5))
    plt.imshow(-E.T, origin="lower", extent=[0, np.pi, 0, np.pi / 2], aspect="auto", cmap="viridis")
    plt.colorbar(label="expected cut")
    plt.xlabel("gamma")
    plt.ylabel("beta")
    plt.title("QAOA p=1 landscape (exact simulation)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "qaoa_p1_landscape.png"), dpi=140)
    plt.close()

    for p in (1, 2, 3):
        tune_seeds = (100, 101, 102)
        adam_lr = min([0.01, 0.03, 0.1, 0.3],
                      key=lambda lr: np.mean([q.energy(qs.adam_ps(q, init(p, s), budget, lr)[0]) for s in tune_seeds]))
        spsa_a = min([0.05, 0.2, 0.5, 1.0],
                     key=lambda a: np.mean([q.energy(qs.spsa(q.energy, init(p, s), budget // 2, a=a, c=0.1, seed=s)[0]) for s in tune_seeds]))
        rows = {"Adam + parameter-shift": [], "SPSA": []}
        for s in range(n_seeds):
            x, ev = qs.adam_ps(q, init(p, s), budget, adam_lr)
            rows["Adam + parameter-shift"].append(dict(q.summary(x), evals=ev))
            x, ev = qs.spsa(q.energy, init(p, s), budget // 2, a=spsa_a, c=0.1, seed=s)
            rows["SPSA"].append(dict(q.summary(x), evals=ev))
        out[f"p={p}"] = dict(
            adam_lr=adam_lr, spsa_a=spsa_a,
            per_step_cost_param_shift=2 * q.n_angles(p) + 1, adam_steps=budget // (2 * q.n_angles(p) + 1),
            **{k: dict(approx_ratio=stats([r["approx_ratio"] for r in v]),
                       prob_optimal=stats([r["prob_optimal"] for r in v]),
                       evals_used=int(np.mean([r["evals"] for r in v])),
                       prob_find_optimum_in_100_shots=float(np.mean([1 - (1 - r["prob_optimal"]) ** 100 for r in v])))
               for k, v in rows.items()})
        print(f"QAOA p={p} done", flush=True)
    out["random_sampling_prob_find_optimum_in_100_shots"] = float(1 - (1 - out["random_guess_prob_optimal"]) ** 100)
    save("qaoa", out)

    names = ["Adam + parameter-shift", "SPSA"]
    fig, ax = plt.subplots(figsize=(6, 4))
    w = 0.35
    for k, nm in enumerate(names):
        ax.bar(np.arange(3) + k * w, [out[f"p={p}"][nm]["approx_ratio"]["mean"] for p in (1, 2, 3)], w,
               yerr=[out[f"p={p}"][nm]["approx_ratio"]["std"] for p in (1, 2, 3)], capsize=3, label=nm)
    ax.axhline(out["random_guess_ratio"], color="gray", ls="--", label="uniform random guess")
    ax.set_xticks(np.arange(3) + w / 2)
    ax.set_xticklabels(["p=1", "p=2", "p=3"])
    ax.set_ylim(0.5, 1.02)
    ax.set_ylabel("approximation ratio (expected cut / optimum)")
    ax.set_title(f"QAOA Max-Cut, {budget} circuit evaluations, 20 starts")
    ax.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "qaoa_optimizers.png"), dpi=140)
    plt.close()


# ============================================================ E2: gradient correctness
def exp_grad():
    q = problem()
    rng = np.random.default_rng(0)
    rows = {}
    for p in (1, 2):
        e_ps, e_naive = [], []
        for _ in range(20):
            prm = np.r_[rng.uniform(0, np.pi, p), rng.uniform(0, np.pi / 2, p)]
            fd = q.grad_finite_difference(prm)
            e_ps.append(float(np.max(np.abs(q.grad_param_shift(prm) - fd))))
            e_naive.append(float(np.max(np.abs(q.grad_naive_shared_shift(prm) - fd))))
        rows[f"p={p}"] = dict(per_gate_param_shift_max_abs_error=max(e_ps), naive_shared_shift_max_abs_error=max(e_naive),
                              naive_shared_shift_median_abs_error=float(np.median(e_naive)))
    save("gradient_check", rows)


# ============================================================ E3: finite shots
def exp_shots():
    q = problem()
    g = load_results()["qaoa"]["p1_grid_best"]
    prm = np.array([g["gamma"], g["beta"]])
    pr = q.probs(prm)
    exact = float(pr @ q.cost)
    sigma = float(np.sqrt(pr @ q.cost ** 2 - exact ** 2))  # std of the cost of ONE measured bitstring
    rng = np.random.default_rng(0)
    rows = []
    for S in (10, 100, 1000, 10000, 100000):
        est = [q.sample_energy(prm, S, rng) for _ in range(300)]
        rows.append(dict(shots=S, empirical_std=float(np.std(est)), predicted_std=sigma / np.sqrt(S),
                         mean_error=float(np.mean(est) - exact)))
    out = dict(exact_energy=exact, single_shot_std=sigma, estimator=rows)

    # SPSA when each function evaluation is a finite-shot estimate. Same a, c for every setting
    # (not re-tuned per shot count), 300 steps, 20 starts, final energy evaluated EXACTLY.
    steps, res = 300, {}
    for S in (10, 100, 1000, None):
        finals = []
        for s in range(20):
            srng = np.random.default_rng(10_000 + s)
            f = (lambda x: q.energy(x)) if S is None else (lambda x: q.sample_energy(x, S, srng))
            x, _ = qs.spsa(f, init(1, s), steps, a=0.2, c=0.2, seed=s)
            finals.append(-q.energy(x) / q.max_cut)
        res["exact expectation" if S is None else f"{S} shots/evaluation"] = stats(finals)
    out["spsa_with_shots_approx_ratio"] = res
    save("shots", out)

    plt.figure(figsize=(5.5, 4))
    S = [r["shots"] for r in rows]
    plt.loglog(S, [r["empirical_std"] for r in rows], "o-", label="measured (300 repeats)")
    plt.loglog(S, [r["predicted_std"] for r in rows], "k--", label=r"$\sigma/\sqrt{S}$")
    plt.xlabel("shots S")
    plt.ylabel("std of the energy estimate")
    plt.title("Finite-shot error of the QAOA energy")
    plt.legend()
    plt.grid(alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "shots.png"), dpi=140)
    plt.close()


# ============================================================ E4: hardware-style noise
def noisy_energy_pl(q, params, prob):
    """QAOA energy under single-qubit depolarizing noise after every gate (PennyLane default.mixed).
    SYNTHETIC noise model: it is NOT calibrated to any real device."""
    import pennylane as qml
    p = len(params) // 2
    n = q.n
    dev = qml.device("default.mixed", wires=n)
    H = qml.Hamiltonian([0.5] * q.m, [qml.PauliZ(i) @ qml.PauliZ(j) for i, j in q.edges])

    @qml.qnode(dev)
    def circ():
        for w in range(n):
            qml.Hadamard(w)
        for l in range(p):
            for i, j in q.edges:
                qml.IsingZZ(params[l], wires=[i, j])
                if prob > 0:
                    qml.DepolarizingChannel(prob, wires=i)
                    qml.DepolarizingChannel(prob, wires=j)
            for w in range(n):
                qml.RX(2 * params[p + l], wires=w)
                if prob > 0:
                    qml.DepolarizingChannel(prob, wires=w)
        return qml.expval(H)

    return float(circ()) - q.m / 2.0


def exp_noise():
    q = problem()
    g = load_results()["qaoa"]["p1_grid_best"]
    prm = np.array([g["gamma"], g["beta"]])
    rows = []
    for prob in (0.0, 0.001, 0.003, 0.01, 0.03, 0.1):
        t0 = time.perf_counter()
        e = noisy_energy_pl(q, prm, prob)
        rows.append(dict(depolarizing_prob_per_gate=prob, expected_cut=-e, approx_ratio=-e / q.max_cut,
                         seconds=time.perf_counter() - t0))
        print("noise", prob, rows[-1]["approx_ratio"], flush=True)
    save("noise", dict(params=prm.tolist(), exact_noiseless_ratio=g["approx_ratio"], random_guess_ratio=(q.m / 2) / q.max_cut,
                       gates_per_circuit=q.m + q.n, rows=rows))
    plt.figure(figsize=(5.5, 4))
    xs = [r["depolarizing_prob_per_gate"] for r in rows]
    plt.semilogx([max(x, 3e-4) for x in xs], [r["approx_ratio"] for r in rows], "o-", label="QAOA p=1 (noisy)")
    plt.axhline((q.m / 2) / q.max_cut, color="gray", ls="--", label="uniform random guess")
    plt.xlabel("depolarizing probability per gate (0 plotted at 3e-4)")
    plt.ylabel("approximation ratio")
    plt.title("QAOA under depolarizing noise (simulated)")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "noise.png"), dpi=140)
    plt.close()


# ============================================================ E5: barren plateaus
def exp_barren(samples=200):
    ns = [2, 4, 6, 8, 10, 12]
    out = dict(qubits=ns, samples=samples, series={})
    cfg = {"deep (L=2n)": lambda n: 2 * n, "shallow (L=2)": lambda n: 2}
    for name, Lf in cfg.items():
        vg, vl = [], []
        for n in ns:
            a, b = bp.gradient_variance(n, Lf(n), samples, seed=n)
            vg.append(a)
            vl.append(b)
            print("barren", name, n, a, b, flush=True)
        out["series"][name] = dict(global_cost=vg, local_cost=vl,
                                   log2_slope_global=float(np.polyfit(ns[1:], np.log2(vg[1:]), 1)[0]),
                                   log2_slope_local=float(np.polyfit(ns[1:], np.log2(vl[1:]), 1)[0]))
    save("barren", out)
    plt.figure(figsize=(6, 4.2))
    for name, s in out["series"].items():
        plt.semilogy(ns, s["global_cost"], "o-", label=f"{name}, global cost")
        plt.semilogy(ns, s["local_cost"], "s--", label=f"{name}, local cost")
    plt.xlabel("qubits n")
    plt.ylabel("Var[dC/dtheta]")
    plt.title("Gradient variance vs qubits (simulated)")
    plt.legend(fontsize=7)
    plt.grid(alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "barren_plateau.png"), dpi=140)
    plt.close()


# ============================================================ E6: VQE, GD vs Adam vs QNG vs SPSA
def exp_vqe(n_seeds=5, steps=80):
    import vqe
    n, L = 4, 3
    H = vqe.tfim(n)
    e0 = vqe.exact_ground_energy(H, n)
    out = dict(qubits=n, layers=L, n_params=(L + 1) * n, exact_ground_energy=e0, steps=steps, tolerance=1e-2, optimizers={})
    curves = {}
    for name, grid in (("GD", [0.03, 0.1, 0.3]), ("Adam", [0.03, 0.1, 0.3]), ("QNG", [0.03, 0.1, 0.3]), ("SPSA", [0.1, 0.3, 1.0])):
        nsteps = steps * 5 if name == "SPSA" else steps
        # tune on seeds 100, 101 with a shorter run
        def tune_score(lr):
            kw = dict(spsa_a=lr) if name == "SPSA" else dict(stepsize=lr)
            return np.mean([vqe.run_optimizer(name, n, L, H, e0, s, max(nsteps // 2, 10), **({"stepsize": 0, **kw}))["final_error"]
                            for s in (100, 101)])
        best_lr = min(grid, key=tune_score)
        runs = []
        for s in range(n_seeds):
            kw = dict(spsa_a=best_lr, stepsize=0) if name == "SPSA" else dict(stepsize=best_lr)
            runs.append(vqe.run_optimizer(name, n, L, H, e0, s, nsteps, **kw))
        reached = [r["execs_at_tol"] for r in runs if r["execs_at_tol"] is not None]
        out["optimizers"][name] = dict(
            best_hyperparameter=best_lr, steps=nsteps,
            final_error=stats_err([r["final_error"] for r in runs]),
            runs_reaching_tolerance=f"{len(reached)}/{n_seeds}",
            executions_to_tolerance_median=float(np.median(reached)) if reached else None,
            total_executions_per_run=int(np.mean([r["total_execs"] for r in runs])))
        curves[name] = np.median([r["errors"] for r in runs], axis=0)
        print("vqe", name, out["optimizers"][name], flush=True)
    save("vqe", out)
    plt.figure(figsize=(6.5, 4.2))
    for name, c in curves.items():
        plt.semilogy(np.arange(1, len(c) + 1), np.maximum(c, 1e-12), label=name)
    plt.axhline(1e-2, color="gray", ls=":")
    plt.xlabel("optimizer step (SPSA uses 2 evaluations per step, so 5x more steps)")
    plt.ylabel("energy error vs exact ground state (median of 5 starts)")
    plt.title("VQE on a 4-qubit transverse-field Ising chain (simulated)")
    plt.legend()
    plt.grid(alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "vqe.png"), dpi=140)
    plt.close()


EXPERIMENTS = dict(qaoa=exp_qaoa, grad=exp_grad, shots=exp_shots, noise=exp_noise, barren=exp_barren, vqe=exp_vqe)

if __name__ == "__main__":
    todo = sys.argv[1:] or list(EXPERIMENTS)
    for name in todo:
        t0 = time.perf_counter()
        EXPERIMENTS[name]()
        print(f"[{name}] finished in {time.perf_counter() - t0:.1f}s", flush=True)
