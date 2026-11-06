"""Curvature tools for Track A: Hessian-vector products, diagonal Hessian,
empirical Fisher, and a low-rank (top-k) eigen-approximation.

None of these form the full Hessian of a large model. That is the point: for n
parameters the Hessian has n^2 entries, but a Hessian-vector product costs about two
gradient evaluations.
"""
import numpy as np


def hvp(grad, x, v, eps=1e-5):
    """Hessian-vector product by central difference of the gradient:
    H v ~ (g(x + eps v) - g(x - eps v)) / (2 eps).
    """
    return (grad(x + eps * v) - grad(x - eps * v)) / (2 * eps)


def diag_hessian_hutchinson(grad, x, samples=200, seed=0):
    """Diagonal of the Hessian via Hutchinson's estimator:
    diag(H) ~ mean_k ( z_k * (H z_k) ), z_k with entries +-1 (Rademacher).
    Unbiased, with variance that falls as 1/samples.
    """
    rng = np.random.default_rng(seed)
    d = np.zeros_like(x)
    for _ in range(samples):
        z = rng.choice([-1.0, 1.0], size=x.shape)
        d += z * hvp(grad, x, z)
    return d / samples


def empirical_fisher_diag(per_sample_grads):
    """Diagonal empirical Fisher: mean over samples of g_i * g_i (elementwise).
    per_sample_grads has shape (n_samples, n_params). It approximates curvature only
    near a good solution; it is not equal to the Hessian in general.
    """
    return np.mean(per_sample_grads ** 2, axis=0)


def top_eigs_lanczos_free(grad, x, k=3, iters=60, seed=0):
    """Top-k eigenpairs of the Hessian by power iteration with deflation, using only
    Hessian-vector products. A simple low-rank approximation H ~ sum lam_i u_i u_i^T.
    Finds the largest-magnitude eigenvalues first.
    """
    rng = np.random.default_rng(seed)
    n = x.size
    vals, vecs = [], []
    for _ in range(k):
        v = rng.normal(size=n)
        v /= np.linalg.norm(v)
        lam = 0.0
        for _ in range(iters):
            w = hvp(grad, x, v)
            for lj, uj in zip(vals, vecs):  # deflate found directions
                w -= lj * (uj @ v) * uj
            lam_new = v @ w
            nw = np.linalg.norm(w)
            if nw < 1e-14:
                break
            v = w / nw
            if abs(lam_new - lam) < 1e-9:
                lam = lam_new
                break
            lam = lam_new
        vals.append(lam)
        vecs.append(v.copy())
    return np.array(vals), np.array(vecs)
