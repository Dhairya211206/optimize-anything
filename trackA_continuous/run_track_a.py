"""Track A: continuous optimization experiments.

Run from the repo root:  python trackA_continuous/run_track_a.py
Writes figures and tables to trackA_continuous/results/.

Fairness rules used throughout:
  * every method gets the same start point and the same iteration budget on a given problem
  * each first-order method's learning rate is tuned on the SAME grid, best final value kept
  * runtime = median of 5 repeats (single-threaded numpy, wall-clock, this machine)
  * stochastic experiments use seeds 0..9 and report mean +- std
"""
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import curvature as cv  # noqa: E402
import objectives as ob  # noqa: E402
import optimizers as op  # noqa: E402
from mlp import MLP, make_moons  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT, exist_ok=True)
RESULTS = {}

LR_GRID = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0, 3.0, 10.0]


def timed(fn, repeats=5):
    ts = []
    out = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t0)
    return out, float(np.median(ts))


def iters_to_tol(f, traj, tol=1e-6):
    """First iteration with f(x) < tol, or None. More meaningful than comparing final values
    that are already at 1e-13 or below, where only float rounding differs."""
    for i, x in enumerate(traj):
        if f(x) < tol:
            return i
    return None


def first_order_methods(grad):
    """name -> function(x0, steps, lr) so a single lr grid can tune all of them."""
    return {
        "GD": lambda x0, s, lr: op.gd(grad, x0, s, lr=lr),
        "Momentum": lambda x0, s, lr: op.momentum(grad, x0, s, lr=lr, beta=0.9),
        "NAG": lambda x0, s, lr: op.nag(grad, x0, s, lr=lr, beta=0.9),
        "AdaGrad": lambda x0, s, lr: op.adagrad(grad, x0, s, lr=lr),
        "RMSProp": lambda x0, s, lr: op.rmsprop(grad, x0, s, lr=lr),
        "Adam": lambda x0, s, lr: op.adam(grad, x0, s, lr=lr),
    }


def tune_and_run(name, steps):
    o = ob.OBJECTIVES[name]
    f = o["f"]
    table = {}
    trajs = {}
    for m, fn in first_order_methods(o["grad"]).items():
        best = (np.inf, None)
        sens = {}
        with np.errstate(all="ignore"):
            for lr in LR_GRID:
                tr = fn(o["x0"], steps, lr)
                val = f(tr[-1])
                if not np.isfinite(val):
                    val = np.inf
                sens[lr] = float(val)
                if val < best[0]:
                    best = (val, lr)
        lr = best[1]
        tr, rt = timed(lambda: fn(o["x0"], steps, lr))
        trajs[m] = tr
        table[m] = dict(best_lr=lr, final_f=float(f(tr[-1])), runtime_s=rt, lr_sensitivity=sens,
                        iters_to_tol_1e6=iters_to_tol(f, tr))
    # Newton (no learning rate; one Hessian solve per iteration)
    nsteps = 30
    tr, rt = timed(lambda: op.newton(o["grad"], o["hess"], o["x0"], nsteps))
    trajs["Newton"] = tr
    table["Newton"] = dict(best_lr=None, final_f=float(f(tr[-1])), runtime_s=rt, iterations=nsteps,
                           iters_to_tol_1e6=iters_to_tol(f, tr))
    return table, trajs


def plot_convergence(trajs, f, title, fname, floor=1e-16):
    plt.figure(figsize=(7, 4.5))
    for m, tr in trajs.items():
        vals = np.array([f(x) for x in tr])
        plt.semilogy(np.maximum(vals, floor), label=m)  # floor keeps exact zeros on the log axis
    plt.xlabel("iteration")
    plt.ylabel("f(x)")
    plt.title(title)
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, fname), dpi=140)
    plt.close()


# ---------------------------------------------------------------- 1. convex
def exp_convex():
    table, trajs = tune_and_run("quadratic", steps=200)
    RESULTS["convex_quadratic"] = table
    plot_convergence(trajs, ob.quad_f, "Strongly convex quadratic (kappa = 20), 200 iterations", "convex_quadratic.png")

    # Convergence-rate check: GD with lr = 1/L contracts f by at most (1 - mu/L)^2 per step.
    L, mu = 20.0, 1.0
    tr = op.gd(ob.quad_grad, ob.OBJECTIVES["quadratic"]["x0"], 60, lr=1.0 / L)
    f = np.array([ob.quad_f(x) for x in tr])
    bound = f[0] * (1 - mu / L) ** (2 * np.arange(len(f)))
    RESULTS["convex_rate_check"] = dict(bound_holds=bool(np.all(f <= bound * (1 + 1e-9))), kappa=L / mu)


# ---------------------------------------------------------------- 2. non-convex
def exp_rosenbrock():
    table, trajs = tune_and_run("rosenbrock", steps=5000)
    RESULTS["nonconvex_rosenbrock"] = table
    plot_convergence(trajs, ob.rosen_f, "Rosenbrock (non-convex valley), 5000 iterations", "rosenbrock.png")

    xs = np.linspace(-2, 2, 300)
    ys = np.linspace(-1, 3, 300)
    Z = np.array([[ob.rosen_f(np.array([x, y])) for x in xs] for y in ys])
    plt.figure(figsize=(6.5, 5))
    plt.contour(xs, ys, np.log10(Z + 1e-9), 25, cmap="gray", alpha=0.6)
    for m in ["GD", "Momentum", "Adam", "Newton"]:
        tr = trajs[m]
        plt.plot(tr[:300, 0], tr[:300, 1], label=m, lw=1.3)
    plt.plot(1, 1, "r*", ms=12)
    plt.legend(fontsize=8)
    plt.title("Rosenbrock paths (first 300 iterations)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "rosenbrock_paths.png"), dpi=140)
    plt.close()


# ---------------------------------------------------------------- 3. minima and saddles
def exp_local_minima_and_saddle():
    o = ob.OBJECTIVES["himmelblau"]
    rng = np.random.default_rng(0)
    starts = rng.uniform(-5, 5, size=(200, 2))
    landing = {m: np.zeros(4, dtype=int) for m in ["GD", "Momentum", "Adam", "Newton"]}
    for s in starts:
        res = {
            "GD": op.gd(o["grad"], s, 3000, lr=0.005)[-1],
            "Momentum": op.momentum(o["grad"], s, 3000, lr=0.002, beta=0.9)[-1],
            "Adam": op.adam(o["grad"], s, 3000, lr=0.05)[-1],
            "Newton": op.newton(o["grad"], o["hess"], s, 60, damping=1e-3)[-1],
        }
        for m, x in res.items():
            if not np.all(np.isfinite(x)):
                continue
            d = np.linalg.norm(ob.HIMMELBLAU_MINIMA - x, axis=1)
            if d.min() < 0.05:
                landing[m][int(np.argmin(d))] += 1
    RESULTS["himmelblau_basins"] = {m: v.tolist() for m, v in landing.items()}

    # Saddle: f = x^2 - y^2. Start with tiny y so gradient methods drift away slowly.
    so = ob.OBJECTIVES["saddle"]
    out = {}
    gd_tr = op.gd(so["grad"], so["x0"], 40, lr=0.1)
    out["GD_after_40_steps"] = gd_tr[-1].tolist()  # x -> 0 but |y| grows: escapes along y
    nw_tr = op.newton(so["grad"], so["hess"], so["x0"], 5)
    out["Newton_after_5_steps"] = nw_tr[-1].tolist()  # lands ON the saddle (attracted to any stationary point)
    exact = op.gd(so["grad"], np.array([1.0, 0.0]), 40, lr=0.1)
    out["GD_exactly_on_axis_y0"] = exact[-1].tolist()  # y stays 0: converges to the saddle
    RESULTS["saddle"] = out

    xs = np.linspace(-5, 5, 200)
    X, Y = np.meshgrid(xs, xs)
    Z = np.array([[ob.him_f(np.array([a, b])) for a in xs] for b in xs])
    plt.figure(figsize=(6, 5))
    plt.contour(X, Y, np.log10(Z + 1), 30, cmap="viridis")
    plt.plot(ob.HIMMELBLAU_MINIMA[:, 0], ob.HIMMELBLAU_MINIMA[:, 1], "r*", ms=11)
    plt.title("Himmelblau: four minima (red stars)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "himmelblau.png"), dpi=140)
    plt.close()


# ---------------------------------------------------------------- 4. learning-rate sensitivity
def exp_sensitivity():
    plt.figure(figsize=(7, 4.5))
    table = RESULTS["convex_quadratic"]
    for m in ["GD", "Momentum", "NAG", "AdaGrad", "RMSProp", "Adam"]:
        sens = table[m]["lr_sensitivity"]
        lrs = sorted(sens)
        vals = [min(sens[l], 1e6) for l in lrs]
        plt.loglog(lrs, np.maximum(vals, 1e-20), "o-", label=m, ms=4)
    plt.xlabel("learning rate")
    plt.ylabel("final f after 200 its (capped at 1e6)")
    plt.title("Learning-rate sensitivity (convex quadratic)")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "lr_sensitivity.png"), dpi=140)
    plt.close()


# ---------------------------------------------------------------- 5. ML as optimization + backprop
def exp_ml():
    X, y = make_moons(n=300, noise=0.2, seed=0)
    Xte, yte = make_moons(n=300, noise=0.2, seed=99)
    model = MLP(hidden=8, lam=1e-3)
    steps = 1500
    n = X.shape[0]

    def full_grad(p):
        return model.grad(p, X, y)

    def batch_grad(bs):
        def g(p, rng):
            idx = rng.choice(n, size=bs, replace=False)
            return model.grad(p, X[idx], y[idx])
        return g

    makers = {
        "GD": lambda lr: (lambda p0, s: op.gd(full_grad, p0, steps, lr=lr)),
        "SGD (bs=1)": lambda lr: (lambda p0, s: op.sgd(batch_grad(1), p0, steps, lr=lr, seed=s)),
        "Mini-batch SGD (bs=32)": lambda lr: (lambda p0, s: op.sgd(batch_grad(32), p0, steps, lr=lr, seed=s)),
        "Momentum": lambda lr: (lambda p0, s: op.momentum(full_grad, p0, steps, lr=lr, beta=0.9)),
        "NAG": lambda lr: (lambda p0, s: op.nag(full_grad, p0, steps, lr=lr, beta=0.9)),
        "AdaGrad": lambda lr: (lambda p0, s: op.adagrad(full_grad, p0, steps, lr=lr)),
        "RMSProp": lambda lr: (lambda p0, s: op.rmsprop(full_grad, p0, steps, lr=lr)),
        "Adam": lambda lr: (lambda p0, s: op.adam(full_grad, p0, steps, lr=lr)),
    }
    # Same tuning rule as the toy problems: pick the lr on the shared grid that gives the
    # lowest final TRAIN loss on seed 0, then evaluate over seeds 0..9 with that lr.
    methods, chosen_lr = {}, {}
    for name, mk in makers.items():
        best = (np.inf, None)
        with np.errstate(all="ignore"):
            for lr in LR_GRID:
                val = model.loss(mk(lr)(model.init(0), 0)[-1], X, y)
                if np.isfinite(val) and val < best[0]:
                    best = (val, lr)
        chosen_lr[name] = best[1]
        methods[name] = mk(best[1])
    res = {}
    curves = {}
    for name, fn in methods.items():
        losses, accs, tes, rts = [], [], [], []
        for seed in range(10):
            p0 = model.init(seed)
            tr, rt = timed(lambda: fn(p0, seed), repeats=1)
            p = tr[-1]
            losses.append(model.loss(p, X, y))
            accs.append(model.accuracy(p, X, y))
            tes.append(model.accuracy(p, Xte, yte))
            rts.append(rt)
            if seed == 0:
                idx = np.linspace(0, steps, 60).astype(int)
                curves[name] = [model.loss(tr[i], X, y) for i in idx]
        res[name] = dict(
            train_loss_mean=float(np.mean(losses)), train_loss_std=float(np.std(losses)),
            train_acc_mean=float(np.mean(accs)), test_acc_mean=float(np.mean(tes)),
            test_acc_std=float(np.std(tes)), runtime_s=float(np.median(rts)),
            chosen_lr=chosen_lr[name],
        )
    RESULTS["mlp_moons"] = res

    plt.figure(figsize=(7, 4.5))
    idx = np.linspace(0, steps, 60)
    for name, c in curves.items():
        plt.plot(idx, c, label=name)
    plt.yscale("log")
    plt.xlabel("iteration (SGD counts one mini-batch per iteration)")
    plt.ylabel("training loss (BCE + L2)")
    plt.title("MLP on two-moons, backprop gradients (seed 0)")
    plt.legend(fontsize=7)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "mlp_training.png"), dpi=140)
    plt.close()

    # Regularization effect: weight norm and test accuracy for lam in a small grid
    reg = {}
    for lam in [0.0, 1e-3, 1e-2, 1e-1]:
        mm = MLP(hidden=8, lam=lam)
        p = op.adam(lambda q: mm.grad(q, X, y), mm.init(0), steps, lr=0.02)[-1]
        W1, _, W2, _ = mm.unpack(p)
        reg[str(lam)] = dict(weight_norm=float(np.sqrt(np.sum(W1 ** 2) + np.sum(W2 ** 2))),
                             test_acc=mm.accuracy(p, Xte, yte))
    RESULTS["regularization"] = reg
    return model, X, y, op.adam(full_grad, model.init(0), steps, lr=0.02)[-1]


# ---------------------------------------------------------------- 6. Gauss-Newton vs GD on nonlinear least squares
def exp_gauss_newton():
    rng = np.random.default_rng(0)
    t = np.linspace(0, 2, 40)
    true = np.array([2.0, 1.3])
    data = true[0] * np.exp(-true[1] * t) + rng.normal(0, 0.01, t.size)

    def resid(x):
        return x[0] * np.exp(-x[1] * t) - data

    def jac(x):
        return np.c_[np.exp(-x[1] * t), -x[0] * t * np.exp(-x[1] * t)]

    def f(x):
        r = resid(x)
        return 0.5 * r @ r

    def g(x):
        return jac(x).T @ resid(x)

    x0 = np.array([1.0, 0.5])
    gn = op.gauss_newton(resid, jac, x0, 15)
    gd_ = op.gd(g, x0, 15, lr=0.02)
    gd_long = op.gd(g, x0, 2000, lr=0.02)
    RESULTS["gauss_newton"] = dict(
        gn_final_f=float(f(gn[-1])), gn_params=gn[-1].tolist(),
        gd_15its_final_f=float(f(gd_[-1])), gd_2000its_final_f=float(f(gd_long[-1])),
        true_params=true.tolist(),
    )


# ---------------------------------------------------------------- 7. noisy objectives
def exp_noisy():
    o = ob.OBJECTIVES["quadratic"]
    sigma = 1.0
    steps = 2000
    out = {}
    methods = {
        "GD constant lr": lambda g, s: op.sgd(g, o["x0"], steps, lr=0.05, seed=s),
        "GD small lr": lambda g, s: op.sgd(g, o["x0"], steps, lr=0.005, seed=s),
        "Adam": None,
    }

    def noisy_grad(x, rng):
        return o["grad"](x) + rng.normal(0, sigma, size=2)

    for name in ["GD constant lr", "GD small lr"]:
        vals = [o["f"](methods[name](noisy_grad, s)[-1]) for s in range(10)]
        out[name] = (float(np.mean(vals)), float(np.std(vals)))
    # Adam with noisy gradients needs its own rng handle
    vals = []
    for s in range(10):
        rng = np.random.default_rng(s)
        tr = op.adam(lambda x: o["grad"](x) + rng.normal(0, sigma, size=2), o["x0"], steps, lr=0.05)
        vals.append(o["f"](tr[-1]))
    out["Adam lr=0.05"] = (float(np.mean(vals)), float(np.std(vals)))
    # SGD with decaying step 0.05/(1+t/100)
    vals = []
    for s in range(10):
        rng = np.random.default_rng(s)
        x = o["x0"].copy()
        for t in range(steps):
            x = x - 0.05 / (1 + t / 100.0) * (o["grad"](x) + rng.normal(0, sigma, size=2))
        vals.append(o["f"](x))
    out["SGD decaying lr"] = (float(np.mean(vals)), float(np.std(vals)))
    RESULTS["noisy_quadratic"] = dict(sigma=sigma, steps=steps, final_f_mean_std=out)

    plt.figure(figsize=(6.5, 4))
    names = list(out)
    plt.bar(names, [out[n][0] for n in names], yerr=[out[n][1] for n in names], capsize=4)
    plt.ylabel("final f (mean +- std, 10 seeds)")
    plt.title("Noisy gradients (sigma = 1): constant step leaves a noise floor")
    plt.xticks(rotation=15, fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "noisy.png"), dpi=140)
    plt.close()


# ---------------------------------------------------------------- 8. curvature at a trained MLP
def exp_curvature(model, X, y, p):
    g = lambda q: model.grad(q, X, y)  # noqa: E731
    vals, _ = cv.top_eigs_lanczos_free(g, p, k=3, iters=200)
    diag_h = cv.diag_hessian_hutchinson(g, p, samples=300)
    per = np.array([model.grad(p, X[i:i + 1], y[i:i + 1]) - 0 for i in range(len(y))])
    # remove the L2 term so only the data-fit part is in the Fisher
    reg_part = np.array([model.lam * np.concatenate([
        model.unpack(p)[0].ravel(), np.zeros(model.h), model.unpack(p)[2], [0.0]])])
    fisher = cv.empirical_fisher_diag(per - reg_part)
    corr = float(np.corrcoef(diag_h, fisher)[0, 1])
    # Full Hessian by n HVPs, for a check of the low-rank claim
    n = p.size
    H = np.array([cv.hvp(g, p, e) for e in np.eye(n)])
    H = 0.5 * (H + H.T)
    eig = np.sort(np.linalg.eigvalsh(H))[::-1]
    RESULTS["curvature_mlp"] = dict(
        n_params=int(n), top3_power_iteration=vals.tolist(), top3_exact=eig[:3].tolist(),
        smallest_eig=float(eig[-1]), n_negative_eigs=int(np.sum(eig < -1e-8)),
        corr_diagHessian_vs_diagFisher=corr,
    )


def main():
    exp_convex()
    exp_rosenbrock()
    exp_local_minima_and_saddle()
    exp_sensitivity()
    model, X, y, p = exp_ml()
    exp_gauss_newton()
    exp_noisy()
    exp_curvature(model, X, y, p)
    with open(os.path.join(OUT, "results.json"), "w") as fh:
        json.dump(RESULTS, fh, indent=2, default=float)
    print(json.dumps({k: v for k, v in RESULTS.items() if k not in ("convex_quadratic", "nonconvex_rosenbrock")}, indent=1, default=float))
    for key in ("convex_quadratic", "nonconvex_rosenbrock"):
        print("\n" + key)
        for m, r in RESULTS[key].items():
            print(f"  {m:9s} lr={r['best_lr']}  final_f={r['final_f']:.3e}  runtime={r['runtime_s']*1e3:.1f} ms")


if __name__ == "__main__":
    main()
