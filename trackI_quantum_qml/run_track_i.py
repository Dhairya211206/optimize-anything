"""Track I experiments. Usage (repo root): python trackI_quantum_qml/run_track_i.py [algorithms qml]
All quantum results are classical SIMULATIONS. The only 'hardware-like' result is a synthetic depolarizing-noise
model; no real quantum hardware was used.
"""
import json
import math
import os
import sys
import time
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qalgs as qa  # noqa: E402
import qml_sim as qm  # noqa: E402
import qsim as qs  # noqa: E402

OUT = os.path.join(HERE, "results")
os.makedirs(OUT, exist_ok=True)
RES = os.path.join(OUT, "results.json")


def save(key, value):
    r = json.load(open(RES)) if os.path.exists(RES) else {}
    r[key] = value
    json.dump(r, open(RES, "w"), indent=1, default=float)


def ms(v):
    return dict(mean=float(np.mean(v)), std=float(np.std(v)), n=len(v))


# =============================================================== algorithms
def exp_dj_bv():
    out = {}
    rows = []
    rng = np.random.default_rng(0)
    for n in (2, 4, 6, 8, 10):
        okc = deutsch_ok = True
        const = qa.deutsch_jozsa(n, np.zeros(2 ** n))
        f = np.zeros(2 ** n)
        f[rng.permutation(2 ** n)[: 2 ** (n - 1)]] = 1
        bal = qa.deutsch_jozsa(n, f)
        s = int(rng.integers(1, 2 ** n))
        got, p = qa.bernstein_vazirani(n, s)
        rows.append(dict(n=n, dj_p0_constant=const, dj_p0_balanced=bal, quantum_queries=1,
                         classical_deterministic_worst_case_dj=2 ** (n - 1) + 1, bv_secret_found=bool(got == s), bv_probability=p,
                         bv_quantum_queries=1, bv_classical_queries=n))
    out["rows"] = rows
    out["note"] = ("One oracle query suffices in the ideal simulation. Classical randomized DJ needs only a few queries with "
                   "tiny error probability, so the advantage over randomized algorithms is much smaller than over deterministic ones.")
    save("dj_bv", out)


def exp_grover():
    out = {}
    # success probability vs iterations (simulated and theory), with overshoot
    n = 6
    ks = list(range(0, 18))
    out["success_vs_iterations_n6"] = dict(k=ks, simulated=[qa.grover_success(n, 7, k) for k in ks],
                                           theory=[qa.grover_theory(n, 1, k) for k in ks], optimal_k=qa.optimal_iterations(n))
    # scaling: oracle queries and wall-clock, simulated Grover vs classical linear search
    rows = []
    rng = np.random.default_rng(0)
    for n in range(4, 21, 2):
        N = 2 ** n
        marked = N // 2  # same instance for both searches; the classical scan then needs N/2 + 1 calls (its average)
        k = qa.optimal_iterations(n)
        t0 = time.perf_counter()
        psi = qa.grover_fast(n, marked, k)
        tq = time.perf_counter() - t0
        f = np.zeros(N, dtype=bool)
        f[marked] = True
        t0 = time.perf_counter()
        calls = 0
        for i in range(N):
            calls += 1
            if f[i]:
                break
        tc = time.perf_counter() - t0
        rows.append(dict(n=n, N=N, quantum_oracle_calls=k, success_prob=float(abs(psi[marked]) ** 2),
                         classical_calls_this_run=calls, classical_expected_calls=(N + 1) / 2, classical_worst_case=N,
                         query_ratio_expected=((N + 1) / 2) / k, simulation_seconds=tq, classical_python_loop_seconds=tc))
    out["scaling"] = rows
    # gate-level cost per Grover iteration (logical gates, before decomposing the n-qubit controlled-Z)
    out["gates_per_iteration"] = "oracle (1 query) + 2n Hadamards + 2n X + one n-qubit controlled-Z; "\
                                 "an n-qubit controlled-Z needs O(n) elementary gates with ancillas or O(n^2) without"
    save("grover", out)


def exp_qft_qpe():
    out = {"qft_matches_dft_max_abs_error": {}}
    for m in (1, 2, 3, 4, 5):
        out["qft_matches_dft_max_abs_error"][m] = float(np.abs(qa.qft_matrix_from_circuit(m) - qa.dft_matrix(m)).max())
    out["qft_gate_counts"] = {m: qs.qft_gate_count(m) for m in (4, 8, 16)}
    qpe = []
    for phi in (5 / 16, 0.3):
        for t in (3, 4, 5, 6, 8, 10):
            p = qa.qpe_distribution(phi, t)
            est = np.argmax(p) / 2 ** t
            near = float(sum(p[y] for y in range(2 ** t) if abs(y / 2 ** t - phi) <= 1 / 2 ** t))
            qpe.append(dict(phi=phi, t=t, best_estimate=float(est), abs_error=abs(est - phi), prob_best=float(p.max()),
                            prob_within_2_pow_minus_t=near))
    out["qpe"] = qpe
    save("qft_qpe", out)


def exp_shor():
    rows = []
    rng = np.random.default_rng(0)
    for N in (15, 21, 35, 77):
        L = N.bit_length()
        per_a = []
        t_total = 0.0
        for a in range(2, N):
            if math.gcd(a, N) != 1:
                continue
            r = qa.true_order(a, N)
            t0 = time.perf_counter()
            p, t = qa.order_finding_distribution(a, N)
            t_total += time.perf_counter() - t0
            ys = rng.choice(len(p), size=500, p=p / p.sum())
            ok_order = ok_factor = 0
            for y in ys:
                rr = qa.order_from_measurement(int(y), t, a, N)
                ok_order += rr == r
                ok_factor += qa.factors_from_order(a, rr, N) is not None
            per_a.append(dict(a=a, order=r, p_order=ok_order / 500, p_factor=ok_factor / 500))
        rows.append(dict(N=N, counting_qubits=2 * L, target_qubits=L, total_qubits=3 * L, statevector_entries=2 ** (3 * L),
                         bases_tried=len(per_a), mean_p_factor_per_shot=float(np.mean([x["p_factor"] for x in per_a])),
                         fraction_of_bases_with_p_factor_gt_0=float(np.mean([x["p_factor"] > 0 for x in per_a])),
                         simulation_seconds_all_bases=t_total))
    # classical comparison: trial division steps for the same N
    for r_ in rows:
        N = r_["N"]
        steps = next(d for d in range(2, N) if N % d == 0)
        r_["classical_trial_division_steps"] = steps - 1
    save("shor", dict(rows=rows, note=("Modular exponentiation is applied as an oracle permutation, not compiled to gates. "
                                       "The simulation costs 2^(3L) memory, so it is exponentially more expensive than the "
                                       "classical algorithm it imitates; no speed-up can be observed.")))


def _grover_noisy(p, k, n=3, marked=(1, 0, 1)):
    import pennylane as qml
    dev = qml.device("default.mixed", wires=n)

    def noise(wires):
        if p > 0:
            for w in wires:
                qml.DepolarizingChannel(p, wires=w)

    @qml.qnode(dev)
    def circ():
        for w in range(n):
            qml.Hadamard(w); noise([w])
        for _ in range(k):
            for w in range(n):  # oracle: flip the sign of |marked>
                if marked[w] == 0:
                    qml.PauliX(w); noise([w])
            qml.CCZ(wires=range(n)); noise(range(n))
            for w in range(n):
                if marked[w] == 0:
                    qml.PauliX(w); noise([w])
            for w in range(n):  # diffusion
                qml.Hadamard(w); noise([w])
                qml.PauliX(w); noise([w])
            qml.CCZ(wires=range(n)); noise(range(n))
            for w in range(n):
                qml.PauliX(w); noise([w])
                qml.Hadamard(w); noise([w])
        return qml.probs(wires=range(n))
    return float(circ()[int("".join(map(str, marked)), 2)])


def exp_noise():
    rows = []
    for p in (0.0, 0.001, 0.003, 0.01, 0.03, 0.1):
        rows.append(dict(p=p, k1=_grover_noisy(p, 1), k2=_grover_noisy(p, 2)))
    save("grover_noise", dict(rows=rows, ideal_k2=qa.grover_theory(3, 1, 2), random_guess=1 / 8,
                              classical_two_query_success=2 / 8,
                              note=("Synthetic model: depolarizing channel of probability p on each qubit a gate touches, one 3-qubit CCZ "
                                    "counted as a single gate (real hardware needs about 6 CNOTs for it, so real noise would be worse). "
                                    "Not a measurement on real hardware.")))
    fig, ax = plt.subplots(figsize=(6, 4))
    ps = [r["p"] for r in rows]
    ax.semilogx([max(p, 3e-4) for p in ps], [r["k2"] for r in rows], "o-", label="Grover, 2 iterations")
    ax.semilogx([max(p, 3e-4) for p in ps], [r["k1"] for r in rows], "s-", label="Grover, 1 iteration")
    ax.axhline(0.25, color="r", ls="--", label="classical: 2 random queries")
    ax.axhline(1 / 8, color="gray", ls=":", label="random guess")
    ax.set_xlabel("depolarizing probability per gate and qubit (p=0 drawn at 3e-4)")
    ax.set_ylabel("probability of the marked item")
    ax.set_title("Grover on 3 qubits under synthetic noise")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "grover_noise.png"), dpi=140)
    plt.close()


def exp_algorithms():
    for f in (exp_dj_bv, exp_grover, exp_qft_qpe, exp_shor, exp_noise):
        t0 = time.perf_counter()
        f()
        print(f"[{f.__name__}] {time.perf_counter() - t0:.1f}s", flush=True)
    g = json.load(open(RES))["grover"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(g["success_vs_iterations_n6"]["k"], g["success_vs_iterations_n6"]["simulated"], "o-", label="simulated")
    ax[0].plot(g["success_vs_iterations_n6"]["k"], g["success_vs_iterations_n6"]["theory"], "--", label="sin^2((2k+1)theta)")
    ax[0].set_xlabel("Grover iterations k")
    ax[0].set_ylabel("success probability")
    ax[0].set_title("Grover, n=6: too many iterations hurt")
    ax[0].legend()
    n = [r["n"] for r in g["scaling"]]
    ax[1].semilogy(n, [r["quantum_oracle_calls"] for r in g["scaling"]], "o-", label="Grover oracle calls")
    ax[1].semilogy(n, [r["classical_expected_calls"] for r in g["scaling"]], "s-", label="classical expected calls")
    ax[1].semilogy(n, [r["simulation_seconds"] for r in g["scaling"]], "^--", label="Grover simulation time (s)")
    ax[1].semilogy(n, [r["classical_python_loop_seconds"] for r in g["scaling"]], "v--", label="classical loop time (s)")
    ax[1].set_xlabel("qubits n (N = 2^n items)")
    ax[1].set_title("Queries fall, simulated wall-clock does not")
    ax[1].legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "grover.png"), dpi=140)
    plt.close()


# =============================================================== QML
def make_data(kind, seed, n_train=100, n_test=300):
    from sklearn.datasets import make_circles, make_moons
    if kind == "moons":
        X, y = make_moons(n_samples=n_train + n_test, noise=0.2, random_state=seed)
    else:
        X, y = make_circles(n_samples=n_train + n_test, noise=0.1, factor=0.5, random_state=seed)
    Xtr, ytr, Xte, yte = X[:n_train], y[:n_train], X[n_train:], y[n_train:]
    lo, hi = Xtr.min(0), Xtr.max(0)
    sc = lambda A: np.clip((A - lo) / (hi - lo), 0, 1) * np.pi
    return sc(Xtr), ytr, sc(Xte), yte


def cv_svm_precomputed(K, y, Cs=(0.1, 1, 10, 100)):
    from sklearn.model_selection import StratifiedKFold
    from sklearn.svm import SVC
    best, bc = -1, None
    for C in Cs:
        sc = []
        for tr, va in StratifiedKFold(3, shuffle=True, random_state=0).split(K, y):
            m = SVC(kernel="precomputed", C=C).fit(K[np.ix_(tr, tr)], y[tr])
            sc.append(m.score(K[np.ix_(va, tr)], y[va]))
        if np.mean(sc) > best:
            best, bc = np.mean(sc), C
    return bc, best


SCALES = (0.1, 0.25, 0.5, 1.0, 2.0)


def exp_qml(n_seeds=5):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GridSearchCV
    from sklearn.neural_network import MLPClassifier
    from sklearn.svm import SVC
    out = {}
    shots_rows = []
    for kind in ("moons", "circles"):
        res = {m: dict(acc=[], seconds=[], params=None, circuits=[]) for m in ("qnn", "quantum_kernel_svm", "rbf_svm", "mlp", "logistic")}
        for seed in range(n_seeds):
            Xtr, ytr, Xte, yte = make_data(kind, seed)
            ypm = 2.0 * ytr - 1
            # QNN
            t0 = time.perf_counter()
            w, hist, runs = qm.train_qnn(Xtr, ypm, layers=4, epochs=120, lr=0.1, seed=seed)
            dt = time.perf_counter() - t0
            acc = float(np.mean((qm.qnn_expval(Xte, w) > 0) == (yte == 1)))
            res["qnn"]["acc"].append(acc); res["qnn"]["seconds"].append(dt); res["qnn"]["params"] = int(w.size)
            res["qnn"]["circuits"].append(runs + len(Xte))
            if seed < 3 and kind == "moons":
                f = qm.qnn_expval(Xte, w)
                rng = np.random.default_rng(seed)
                for shots in (1, 5, 25, 125, 625):
                    accs = []
                    for _ in range(30):
                        est = np.where(rng.uniform(size=(len(f),) + (shots,)) < (1 + f)[:, None] / 2, 1, -1).mean(axis=1)
                        accs.append(np.mean((est > 0) == (yte == 1)))
                    shots_rows.append(dict(seed=seed, shots=shots, acc=float(np.mean(accs))))
            # quantum kernel SVM
            # same tuning budget as the RBF grid (20 combinations): 5 feature scales x 4 values of C, chosen by 3-fold CV on the training set
            t0 = time.perf_counter()
            best = (-1, None, None)
            for scale in SCALES:
                K = qm.kernel_matrix(Xtr * scale, Xtr * scale)
                C, cvs = cv_svm_precomputed(K, ytr)
                if cvs > best[0]:
                    best = (cvs, scale, C)
            _, scale, C = best
            K = qm.kernel_matrix(Xtr * scale, Xtr * scale)
            svm = SVC(kernel="precomputed", C=C).fit(K, ytr)
            dt = time.perf_counter() - t0
            Kte = qm.kernel_matrix(Xte * scale, Xtr * scale)
            res["quantum_kernel_svm"]["acc"].append(float(svm.score(Kte, yte)))
            res["quantum_kernel_svm"]["seconds"].append(dt)
            res["quantum_kernel_svm"]["params"] = int(len(svm.support_))  # number of support vectors (dual coefficients)
            res["quantum_kernel_svm"].setdefault("scales", []).append(scale)
            res["quantum_kernel_svm"]["circuits"].append(len(SCALES) * len(Xtr) * (len(Xtr) - 1) // 2 + len(Xte) * len(svm.support_))
            # classical models
            t0 = time.perf_counter()
            g = GridSearchCV(SVC(kernel="rbf"), {"C": [0.1, 1, 10, 100], "gamma": [0.1, 0.3, 1, 3, 10]}, cv=3).fit(Xtr, ytr)
            res["rbf_svm"]["seconds"].append(time.perf_counter() - t0)
            res["rbf_svm"]["acc"].append(float(g.score(Xte, yte)))
            res["rbf_svm"]["params"] = int(len(g.best_estimator_.support_))
            t0 = time.perf_counter()
            mlp = MLPClassifier((8,), activation="tanh", solver="lbfgs", max_iter=2000, random_state=seed).fit(Xtr, ytr)
            res["mlp"]["seconds"].append(time.perf_counter() - t0)
            res["mlp"]["acc"].append(float(mlp.score(Xte, yte)))
            res["mlp"]["params"] = int(2 * 8 + 8 + 8 + 1)
            t0 = time.perf_counter()
            lr = LogisticRegression().fit(Xtr, ytr)
            res["logistic"]["seconds"].append(time.perf_counter() - t0)
            res["logistic"]["acc"].append(float(lr.score(Xte, yte)))
            res["logistic"]["params"] = 3
            print(kind, seed, {m: round(res[m]["acc"][-1], 3) for m in res}, flush=True)
        out[kind] = {m: dict(test_accuracy=ms(v["acc"]), train_seconds=ms(v["seconds"]), parameters_or_support_vectors=v["params"],
                             circuit_executions=ms(v["circuits"]) if v["circuits"] else 0,
                             **({"chosen_feature_scales": v["scales"]} if "scales" in v else {})) for m, v in res.items()}
    out["qnn_finite_shots_moons"] = shots_rows
    out["note"] = ("Circuit executions count exact-expectation runs (shots = infinity in simulation); on hardware every run would need many "
                   "shots. Quantum training times are simulator times and say nothing about hardware. Parameter counts for SVMs are "
                   "numbers of support vectors.")
    save("qml", out)
    fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for a, kind in zip(ax, ("moons", "circles")):
        names = list(out[kind])
        a.bar(names, [out[kind][m]["test_accuracy"]["mean"] for m in names], yerr=[out[kind][m]["test_accuracy"]["std"] for m in names], capsize=3)
        a.set_title(f"{kind}, test accuracy (5 seeds)")
        a.tick_params(axis="x", rotation=25)
        a.set_ylim(0.4, 1.0)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "qml.png"), dpi=140)
    plt.close()


EXPERIMENTS = dict(algorithms=exp_algorithms, qml=exp_qml)

if __name__ == "__main__":
    for name in sys.argv[1:] or list(EXPERIMENTS):
        t0 = time.perf_counter()
        EXPERIMENTS[name]()
        print(f"[{name}] finished in {time.perf_counter() - t0:.1f}s", flush=True)
