"""Correctness checks for Track A. Run: python -m pytest trackA_continuous -q"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import curvature as cv  # noqa: E402
import objectives as ob  # noqa: E402
import optimizers as op  # noqa: E402
from mlp import MLP, finite_difference_grad, make_moons  # noqa: E402


def test_backprop_matches_finite_differences():
    X, y = make_moons(n=40, seed=1)
    m = MLP(hidden=5, lam=1e-2)
    p = m.init(seed=2)
    g_bp = m.grad(p, X, y)
    g_fd = finite_difference_grad(lambda q: m.loss(q, X, y), p)
    assert np.max(np.abs(g_bp - g_fd)) < 1e-6


def test_analytic_gradients_match_finite_differences():
    rng = np.random.default_rng(0)
    for name in ["quadratic", "rosenbrock", "himmelblau", "saddle"]:
        o = ob.OBJECTIVES[name]
        x = rng.normal(size=2)
        g_fd = finite_difference_grad(o["f"], x)
        assert np.allclose(o["grad"](x), g_fd, atol=1e-4), name


def test_analytic_hessians_match_finite_differences_of_gradient():
    rng = np.random.default_rng(0)
    for name in ["quadratic", "rosenbrock", "himmelblau", "saddle"]:
        o = ob.OBJECTIVES[name]
        x = rng.normal(size=2)
        H_fd = np.array([cv.hvp(o["grad"], x, e) for e in np.eye(2)])
        assert np.allclose(o["hess"](x), H_fd, atol=1e-3), name


def test_all_first_order_methods_decrease_quadratic():
    o = ob.OBJECTIVES["quadratic"]
    f0 = o["f"](o["x0"])
    runs = {
        "gd": op.gd(o["grad"], o["x0"], 200, lr=0.05),
        "momentum": op.momentum(o["grad"], o["x0"], 200, lr=0.01, beta=0.9),
        "nag": op.nag(o["grad"], o["x0"], 200, lr=0.01, beta=0.9),
        "adagrad": op.adagrad(o["grad"], o["x0"], 200, lr=1.0),
        "rmsprop": op.rmsprop(o["grad"], o["x0"], 400, lr=0.01),
        "adam": op.adam(o["grad"], o["x0"], 400, lr=0.1),
    }
    for name, tr in runs.items():
        assert o["f"](tr[-1]) < 0.05 * f0, name


def test_newton_solves_quadratic_in_one_step():
    o = ob.OBJECTIVES["quadratic"]
    tr = op.newton(o["grad"], o["hess"], o["x0"], steps=1)
    assert np.allclose(tr[-1], 0.0, atol=1e-10)


def test_gauss_newton_solves_linear_least_squares_in_one_step():
    rng = np.random.default_rng(3)
    J = rng.normal(size=(20, 3))
    x_true = np.array([1.0, -2.0, 0.5])
    b = J @ x_true
    tr = op.gauss_newton(lambda x: J @ x - b, lambda x: J, np.zeros(3), steps=1)
    assert np.allclose(tr[-1], x_true, atol=1e-8)


def test_hvp_exact_on_quadratic():
    x = np.array([1.0, 2.0])
    v = np.array([0.3, -0.7])
    assert np.allclose(cv.hvp(ob.quad_grad, x, v), ob.A_QUAD @ v, atol=1e-6)


def test_hutchinson_diag_close_to_true_diag():
    d = cv.diag_hessian_hutchinson(ob.quad_grad, np.array([1.0, 1.0]), samples=300)
    assert np.allclose(d, [1.0, 20.0], atol=1e-3)


def test_power_iteration_finds_top_eigenvalue():
    vals, _ = cv.top_eigs_lanczos_free(ob.quad_grad, np.array([1.0, 1.0]), k=2)
    assert abs(vals[0] - 20.0) < 1e-3 and abs(vals[1] - 1.0) < 1e-2


def test_saddle_gradient_zero_at_origin_and_indefinite_hessian():
    assert np.allclose(ob.saddle_grad(np.zeros(2)), 0)
    assert np.min(np.linalg.eigvalsh(ob.saddle_hess(np.zeros(2)))) < 0 < np.max(np.linalg.eigvalsh(ob.saddle_hess(np.zeros(2))))


def test_himmelblau_minima_have_zero_value_and_gradient():
    for m in ob.HIMMELBLAU_MINIMA:
        assert ob.him_f(m) < 1e-4
        assert np.linalg.norm(ob.him_grad(m)) < 1e-2
