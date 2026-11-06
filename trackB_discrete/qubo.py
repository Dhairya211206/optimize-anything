"""QUBO and Ising formulations (Track B), reused by Track C.

QUBO:  minimize  E(x) = x^T Q x   with x in {0,1}^n.  Q is stored upper-triangular:
         Q[i,i]  = linear coefficient of x_i   (because x_i^2 = x_i)
         Q[i,j]  = coefficient of x_i x_j for i < j
Ising: E(s) = sum_i h_i s_i + sum_{i<j} J_ij s_i s_j + const,  s in {-1,+1}^n, with x = (1 - s) / 2
       (so x = 0 <-> s = +1 and x = 1 <-> s = -1).
"""
import itertools

import networkx as nx
import numpy as np


# ------------------------------------------------------------------ generic tools
def qubo_energy(Q, x):
    x = np.asarray(x, dtype=float)
    return float(x @ Q @ x)


def all_bitstrings(n):
    """Array of shape (2^n, n); row k is the binary expansion of k, bit i = column i."""
    k = np.arange(1 << n)
    return ((k[:, None] >> np.arange(n)) & 1).astype(np.int8)


def brute_force_qubo(Q):
    """Exact minimum by enumeration (n <= ~22). Returns (energy, x, all_energies)."""
    n = Q.shape[0]
    X = all_bitstrings(n).astype(float)
    E = np.einsum("ki,ij,kj->k", X, Q, X)
    k = int(np.argmin(E))
    return float(E[k]), X[k].astype(int), E


def qubo_to_ising(Q):
    """Binary-to-spin conversion x_i = (1 - s_i)/2.
    Linear term:   Q_ii x_i      = Q_ii/2 - (Q_ii/2) s_i
    Quadratic:     Q_ij x_i x_j  = Q_ij/4 (1 - s_i - s_j + s_i s_j)
    """
    n = Q.shape[0]
    h = np.zeros(n)
    J = np.zeros((n, n))
    const = 0.0
    for i in range(n):
        h[i] += -Q[i, i] / 2.0
        const += Q[i, i] / 2.0
        for j in range(i + 1, n):
            if Q[i, j] != 0:
                J[i, j] = Q[i, j] / 4.0
                h[i] += -Q[i, j] / 4.0
                h[j] += -Q[i, j] / 4.0
                const += Q[i, j] / 4.0
    return h, J, const


def ising_energy(h, J, const, s):
    s = np.asarray(s, dtype=float)
    return float(h @ s + s @ J @ s + const)  # J is strictly upper-triangular


def simulated_annealing(Q, seed=0, sweeps=300, t0=2.0, t1=0.01):
    """Single-bit-flip Metropolis annealing on a QUBO with geometric cooling."""
    rng = np.random.default_rng(seed)
    n = Q.shape[0]
    S = Q + Q.T  # symmetric form for fast flip deltas
    np.fill_diagonal(S, 0)
    x = rng.integers(0, 2, n).astype(float)
    E = qubo_energy(Q, x)
    best_x, best_E = x.copy(), E
    temps = t0 * (t1 / t0) ** (np.arange(sweeps) / max(sweeps - 1, 1))
    for T in temps:
        for i in rng.permutation(n):
            # change in energy if bit i flips
            d = (1 - 2 * x[i]) * (Q[i, i] + S[i] @ x)
            if d <= 0 or rng.random() < np.exp(-d / T):
                x[i] = 1 - x[i]
                E += d
                if E < best_E - 1e-12:
                    best_E, best_x = E, x.copy()
    return best_E, best_x.astype(int)


def hill_climb(Q, seed=0):
    """Greedy 1-flip local search from a random start (no uphill moves)."""
    rng = np.random.default_rng(seed)
    n = Q.shape[0]
    x = rng.integers(0, 2, n).astype(float)
    improved = True
    while improved:
        improved = False
        for i in rng.permutation(n):
            y = x.copy()
            y[i] = 1 - y[i]
            if qubo_energy(Q, y) < qubo_energy(Q, x) - 1e-12:
                x = y
                improved = True
    return qubo_energy(Q, x), x.astype(int)


# ------------------------------------------------------------------ Max-Cut
def maxcut_graph(n=8, p=0.5, seed=7):
    g = nx.gnp_random_graph(n, p, seed=seed)
    return g


def maxcut_qubo(g):
    """cut(x) = sum_{(i,j) in E} (x_i + x_j - 2 x_i x_j).  Minimizing E(x) = -cut(x):
       Q_ii = -deg(i),  Q_ij = +2 for each edge i<j.
    """
    n = g.number_of_nodes()
    Q = np.zeros((n, n))
    for i, j in g.edges():
        a, b = min(i, j), max(i, j)
        Q[a, a] -= 1
        Q[b, b] -= 1
        Q[a, b] += 2
    return Q


def cut_value(g, x):
    return int(sum(1 for i, j in g.edges() if x[i] != x[j]))


def maxcut_ilp(g):
    """Max-Cut as an ILP (HiGHS). Edge variable y_e = 1 only if its endpoints are on different sides:
         maximize sum_e y_e   s.t.  y_e <= x_i + x_j,   y_e <= 2 - x_i - x_j,   x, y binary.
    Returns (cut, x)."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    n, edges = g.number_of_nodes(), list(g.edges())
    m = len(edges)
    A = np.zeros((2 * m, n + m))
    ub = np.zeros(2 * m)
    for e, (i, j) in enumerate(edges):
        A[2 * e, n + e], A[2 * e, i], A[2 * e, j] = 1, -1, -1          # y - xi - xj <= 0
        A[2 * e + 1, n + e], A[2 * e + 1, i], A[2 * e + 1, j] = 1, 1, 1  # y + xi + xj <= 2
        ub[2 * e], ub[2 * e + 1] = 0, 2
    c = np.r_[np.zeros(n), -np.ones(m)]
    res = milp(c, constraints=LinearConstraint(A, ub=ub), integrality=np.ones(n + m), bounds=Bounds(0, 1))
    x = np.round(res.x[:n]).astype(int)
    return int(round(-res.fun)), x


# ------------------------------------------------------------------ feature selection
def make_feature_data(n_samples=400, seed=0):
    """12 features: 4 informative, 4 near-copies of informative ones (redundant), 4 noise."""
    rng = np.random.default_rng(seed)
    inf = rng.normal(size=(n_samples, 4))
    y = inf @ np.array([1.5, -1.0, 0.8, 0.5]) + rng.normal(0, 0.5, n_samples)
    copies = inf[:, :4] + rng.normal(0, 0.15, (n_samples, 4))
    noise = rng.normal(size=(n_samples, 4))
    X = np.hstack([inf, copies, noise])
    return X, y


def feature_selection_qubo(X, y, k, alpha=1.0, penalty=2.0):
    """Maximize relevance minus redundancy with exactly k features:
         maximize sum_i r_i x_i - alpha sum_{i<j} R_ij x_i x_j       (r = |corr(x_i, y)|, R = |corr(x_i, x_j)|)
         subject to sum_i x_i = k
       The cardinality constraint becomes a penalty P (sum x - k)^2
         = P [ sum_i (1 - 2k) x_i + 2 sum_{i<j} x_i x_j + k^2 ].
       Returns Q (minimization form, constant P k^2 dropped).
    """
    n = X.shape[1]
    r = np.abs([np.corrcoef(X[:, i], y)[0, 1] for i in range(n)])
    R = np.abs(np.corrcoef(X.T))
    Q = np.zeros((n, n))
    for i in range(n):
        Q[i, i] = -r[i] + penalty * (1 - 2 * k)
        for j in range(i + 1, n):
            Q[i, j] = alpha * R[i, j] + 2 * penalty
    return Q, r, R


def fs_objective(x, r, R, alpha=1.0):
    """The UNPENALISED objective (higher is better) used to compare solutions fairly."""
    x = np.asarray(x, dtype=float)
    return float(r @ x - alpha * 0.5 * (x @ (R - np.eye(len(x))) @ x))


def greedy_forward_selection(r, R, k, alpha=1.0):
    chosen = []
    for _ in range(k):
        best, bi = -np.inf, None
        for i in range(len(r)):
            if i in chosen:
                continue
            x = np.zeros(len(r))
            x[chosen + [i]] = 1
            val = fs_objective(x, r, R, alpha)
            if val > best:
                best, bi = val, i
        chosen.append(bi)
    x = np.zeros(len(r), dtype=int)
    x[chosen] = 1
    return x
