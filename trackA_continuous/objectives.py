"""Test objectives for Track A.

Each objective returns (f, grad, hess) callables on 2-D numpy arrays so the same
optimizers can be run on all of them.

Landscapes:
  - quadratic:  convex, strongly convex (condition number 20), single global min at (0, 0)
  - rosenbrock: non-convex, one global min at (1, 1) in a narrow curved valley
  - himmelblau: non-convex, FOUR local (also global) minima, one local max
  - saddle:     f = x^2 - y^2, a saddle point at the origin, no minimum
"""
import numpy as np

# ---- strongly convex quadratic: f = 0.5 x^T A x, A = diag(1, 20) ----
A_QUAD = np.diag([1.0, 20.0])


def quad_f(x):
    return 0.5 * x @ A_QUAD @ x


def quad_grad(x):
    return A_QUAD @ x


def quad_hess(x):
    return A_QUAD


# ---- Rosenbrock ----
def rosen_f(x):
    return (1 - x[0]) ** 2 + 100.0 * (x[1] - x[0] ** 2) ** 2


def rosen_grad(x):
    return np.array([
        -2 * (1 - x[0]) - 400.0 * x[0] * (x[1] - x[0] ** 2),
        200.0 * (x[1] - x[0] ** 2),
    ])


def rosen_hess(x):
    return np.array([
        [2 - 400.0 * (x[1] - x[0] ** 2) + 800.0 * x[0] ** 2, -400.0 * x[0]],
        [-400.0 * x[0], 200.0],
    ])


# ---- Himmelblau ----
def him_f(x):
    return (x[0] ** 2 + x[1] - 11) ** 2 + (x[0] + x[1] ** 2 - 7) ** 2


def him_grad(x):
    return np.array([
        4 * x[0] * (x[0] ** 2 + x[1] - 11) + 2 * (x[0] + x[1] ** 2 - 7),
        2 * (x[0] ** 2 + x[1] - 11) + 4 * x[1] * (x[0] + x[1] ** 2 - 7),
    ])


def him_hess(x):
    return np.array([
        [12 * x[0] ** 2 + 4 * x[1] - 42, 4 * x[0] + 4 * x[1]],
        [4 * x[0] + 4 * x[1], 12 * x[1] ** 2 + 4 * x[0] - 26],
    ])


# Known minima of Himmelblau (f = 0), used to check which one a method lands in.
HIMMELBLAU_MINIMA = np.array([
    [3.0, 2.0],
    [-2.805118, 3.131312],
    [-3.779310, -3.283186],
    [3.584428, -1.848126],
])


# ---- saddle ----
def saddle_f(x):
    return x[0] ** 2 - x[1] ** 2


def saddle_grad(x):
    return np.array([2 * x[0], -2 * x[1]])


def saddle_hess(x):
    return np.array([[2.0, 0.0], [0.0, -2.0]])


OBJECTIVES = {
    "quadratic": dict(f=quad_f, grad=quad_grad, hess=quad_hess, x0=np.array([4.0, 3.0]), opt=np.zeros(2)),
    "rosenbrock": dict(f=rosen_f, grad=rosen_grad, hess=rosen_hess, x0=np.array([-1.5, 1.5]), opt=np.ones(2)),
    "himmelblau": dict(f=him_f, grad=him_grad, hess=him_hess, x0=np.array([0.0, 0.0]), opt=None),
    "saddle": dict(f=saddle_f, grad=saddle_grad, hess=saddle_hess, x0=np.array([1.0, 1e-3]), opt=None),
}
