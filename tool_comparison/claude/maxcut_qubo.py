"""Max-Cut as QUBO and Ising, solved by brute force and simulated annealing (numpy + pytest only).

Conventions (derivations are in the comments next to each function):
  graph:  adjacency matrix A (symmetric, zero diagonal), degrees d_i = sum_j A_ij
  QUBO:   minimise E(x) = x^T Q x,  x_i in {0,1}
  Ising:  E(s) = sum_{i<j} J_ij s_i s_j + sum_i h_i s_i + offset,  s_i in {-1,+1},  x_i = (1 + s_i)/2
"""
import numpy as np

N_NODES, N_EDGES, GRAPH_SEED = 8, 18, 7


def build_graph(n=N_NODES, m=N_EDGES, seed=GRAPH_SEED):
    """Random simple undirected graph with exactly m edges: sample m of the n(n-1)/2 node pairs without replacement."""
    rng = np.random.default_rng(seed)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    chosen = rng.choice(len(pairs), size=m, replace=False)
    A = np.zeros((n, n))
    for k in chosen:
        i, j = pairs[k]
        A[i, j] = A[j, i] = 1.0
    return A


def cut_value(x, A):
    """Number of edges whose endpoints are in different parts: sum_{i<j} A_ij [x_i != x_j]."""
    x = np.asarray(x)
    diff = x[:, None] != x[None, :]
    return float((A * diff).sum() / 2)  # each edge counted twice in the full matrix


def maxcut_qubo(A):
    """Q for min x^T Q x with E(x) = -cut(x).

    An edge (i,j) is cut iff x_i + x_j - 2 x_i x_j = 1 (it is 0 when x_i = x_j, 1 otherwise).
    So cut(x) = sum_{i<j} A_ij (x_i + x_j - 2 x_i x_j) = sum_i d_i x_i - sum_{i<j} 2 A_ij x_i x_j.
    Minimising -cut: diagonal Q_ii = -d_i (because x_i^2 = x_i), and the cross term -(-2 A_ij) x_i x_j = +2 A_ij x_i x_j
    for i<j.  Written with a symmetric Q, x^T Q x counts each pair twice (Q_ij x_i x_j + Q_ji x_i x_j), so
    Q_ij = Q_ji = A_ij.  Hence Q = A - diag(d).
    """
    return A - np.diag(A.sum(axis=1))


def qubo_energy(x, Q):
    x = np.asarray(x, dtype=float)
    return float(x @ Q @ x)


def qubo_to_ising(Q):
    """Substitute x = (1+s)/2 into x^T Q x = sum_i Q_ii x_i + sum_{i<j} 2 Q_ij x_i x_j (Q symmetric, x_i^2 = x_i).

      x_i      = (1 + s_i)/2
      x_i x_j  = (1 + s_i + s_j + s_i s_j)/4
    so   2 Q_ij x_i x_j  =  (Q_ij/2) (1 + s_i + s_j + s_i s_j)
         Q_ii x_i        =  (Q_ii/2) (1 + s_i)
    Collecting terms:
      J_ij   = Q_ij / 2                          (i<j, stored in the upper triangle)
      h_i    = Q_ii / 2 + sum_{j != i} Q_ij / 2
      offset = sum_i Q_ii / 2 + sum_{i<j} Q_ij / 2
    """
    n = Q.shape[0]
    J = np.triu(Q / 2.0, k=1)
    off_diag = Q - np.diag(np.diag(Q))
    h = np.diag(Q) / 2.0 + off_diag.sum(axis=1) / 2.0
    offset = np.diag(Q).sum() / 2.0 + np.triu(off_diag, k=1).sum() / 2.0
    return J, h, float(offset)


def ising_energy(s, J, h, offset):
    s = np.asarray(s, dtype=float)
    return float(s @ J @ s + h @ s + offset)  # J is upper triangular, so s^T J s = sum_{i<j} J_ij s_i s_j


def all_assignments(n):
    """All 2^n binary vectors as rows, row k = binary expansion of k (most significant bit first)."""
    k = np.arange(2 ** n)
    return ((k[:, None] >> np.arange(n - 1, -1, -1)) & 1).astype(int)


def brute_force(A):
    X = all_assignments(A.shape[0])
    cuts = np.array([cut_value(x, A) for x in X])
    return float(cuts.max()), X[cuts == cuts.max()]


def simulated_annealing(Q, rng, sweeps=200, t_start=3.0, t_end=0.05):
    """Single-bit-flip Metropolis annealing on E(x) = x^T Q x with geometric cooling; returns the best x seen.

    Flipping bit k changes x_k by d = 1 - 2 x_k (d = +1 or -1).  Writing E(x) = sum_i Q_ii x_i + sum_{i != j} Q_ij x_i x_j
    (using x_i^2 = x_i), only terms containing x_k change:
        Delta E = Q_kk d + 2 d sum_{j != k} Q_kj x_j          (the factor 2 is because Q is symmetric)
    """
    n = Q.shape[0]
    x = rng.integers(0, 2, size=n)
    e = qubo_energy(x, Q)
    best_x, best_e = x.copy(), e
    temps = t_start * (t_end / t_start) ** (np.arange(sweeps) / (sweeps - 1))
    for t in temps:
        for k in rng.permutation(n):
            d = 1 - 2 * x[k]
            delta = d * (Q[k, k] + 2 * (Q[k] @ x - Q[k, k] * x[k]))
            if delta <= 0 or rng.random() < np.exp(-delta / t):
                x[k] += d
                e += delta
                if e < best_e - 1e-12:
                    best_e, best_x = e, x.copy()
    return best_x, best_e


def main():
    A = build_graph()
    Q = maxcut_qubo(A)
    J, h, offset = qubo_to_ising(Q)
    best_cut, optima = brute_force(A)
    rng = np.random.default_rng(123)
    hits = sum(cut_value(simulated_annealing(Q, rng)[0], A) == best_cut for _ in range(50))
    print(f"graph: {int(A.sum() // 2)} edges, degrees {A.sum(axis=1).astype(int).tolist()}")
    print(f"Ising: h = {h.tolist()}, offset = {offset}")
    print(f"brute force: best cut = {best_cut:.0f}, {len(optima)} optimal assignments")
    print(f"simulated annealing: {hits}/50 runs reached the optimum")


if __name__ == "__main__":
    main()
