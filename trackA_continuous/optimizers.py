"""First-order and second-order optimizers for Track A.

Every optimizer has the same signature so comparisons are fair:

    opt(grad, x0, steps, **hyperparameters) -> trajectory  (array of shape (steps+1, dim))

`grad` is a callable x -> gradient. The trajectory lets us compute f(x_t) afterwards,
so the stopping rule is identical for every method: a fixed number of iterations.

SGD / mini-batch SGD take a stochastic gradient callable `grad_batch(x, rng)` instead;
see `sgd` below.
"""
import numpy as np


def gd(grad, x0, steps, lr=0.01):
    """Plain gradient descent: x <- x - lr * g."""
    x = x0.astype(float).copy()
    traj = [x.copy()]
    for _ in range(steps):
        x = x - lr * grad(x)
        traj.append(x.copy())
    return np.array(traj)


def sgd(grad_batch, x0, steps, lr=0.01, seed=0):
    """SGD / mini-batch SGD. `grad_batch(x, rng)` returns a noisy or sub-sampled gradient.

    Batch size is chosen inside grad_batch: batch size 1 = SGD, larger = mini-batch,
    full data = GD.
    """
    rng = np.random.default_rng(seed)
    x = x0.astype(float).copy()
    traj = [x.copy()]
    for _ in range(steps):
        x = x - lr * grad_batch(x, rng)
        traj.append(x.copy())
    return np.array(traj)


def momentum(grad, x0, steps, lr=0.01, beta=0.9):
    """Heavy-ball momentum: v <- beta v + g ; x <- x - lr v."""
    x = x0.astype(float).copy()
    v = np.zeros_like(x)
    traj = [x.copy()]
    for _ in range(steps):
        v = beta * v + grad(x)
        x = x - lr * v
        traj.append(x.copy())
    return np.array(traj)


def nag(grad, x0, steps, lr=0.01, beta=0.9):
    """Nesterov accelerated gradient: gradient taken at the look-ahead point."""
    x = x0.astype(float).copy()
    v = np.zeros_like(x)
    traj = [x.copy()]
    for _ in range(steps):
        g = grad(x - lr * beta * v)  # look-ahead
        v = beta * v + g
        x = x - lr * v
        traj.append(x.copy())
    return np.array(traj)


def adagrad(grad, x0, steps, lr=0.5, eps=1e-8):
    """AdaGrad: per-coordinate step lr / sqrt(sum of squared gradients)."""
    x = x0.astype(float).copy()
    G = np.zeros_like(x)
    traj = [x.copy()]
    for _ in range(steps):
        g = grad(x)
        G += g * g
        x = x - lr * g / (np.sqrt(G) + eps)
        traj.append(x.copy())
    return np.array(traj)


def rmsprop(grad, x0, steps, lr=0.01, rho=0.9, eps=1e-8):
    """RMSProp: exponential moving average of squared gradients."""
    x = x0.astype(float).copy()
    s = np.zeros_like(x)
    traj = [x.copy()]
    for _ in range(steps):
        g = grad(x)
        s = rho * s + (1 - rho) * g * g
        x = x - lr * g / (np.sqrt(s) + eps)
        traj.append(x.copy())
    return np.array(traj)


def adam(grad, x0, steps, lr=0.05, b1=0.9, b2=0.999, eps=1e-8):
    """Adam with bias correction."""
    x = x0.astype(float).copy()
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    traj = [x.copy()]
    for t in range(1, steps + 1):
        g = grad(x)
        m = b1 * m + (1 - b1) * g
        v = b2 * v + (1 - b2) * g * g
        mhat = m / (1 - b1 ** t)
        vhat = v / (1 - b2 ** t)
        x = x - lr * mhat / (np.sqrt(vhat) + eps)
        traj.append(x.copy())
    return np.array(traj)


def newton(grad, hess, x0, steps, damping=0.0, lr=1.0):
    """Newton's method: x <- x - lr * (H + damping I)^-1 g.

    Uses a linear solve rather than an explicit inverse. If H is singular the
    solve falls back to a gradient step so the run does not crash.
    """
    x = x0.astype(float).copy()
    traj = [x.copy()]
    n = x.size
    for _ in range(steps):
        g = grad(x)
        H = hess(x) + damping * np.eye(n)
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = g
        x = x - lr * step
        traj.append(x.copy())
    return np.array(traj)


def gauss_newton(residual, jacobian, x0, steps, damping=0.0):
    """Gauss-Newton for least squares f(x) = 0.5 ||r(x)||^2.

    Step: solve (J^T J + damping I) d = J^T r ; x <- x - d.
    Ignores the second-order term sum_i r_i * Hess(r_i), which is why it is only
    a good approximation when residuals are small near the solution.
    """
    x = x0.astype(float).copy()
    traj = [x.copy()]
    n = x.size
    for _ in range(steps):
        r = residual(x)
        J = jacobian(x)
        d = np.linalg.solve(J.T @ J + damping * np.eye(n), J.T @ r)
        x = x - d
        traj.append(x.copy())
    return np.array(traj)
