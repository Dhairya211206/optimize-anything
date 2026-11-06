"""Exact state-vector QAOA simulator for Max-Cut, plus the optimizers used on it (Track C).

SIMULATION ONLY. Nothing here runs on quantum hardware.

Why a hand-written simulator: the optimizer comparisons need tens of thousands of circuit
evaluations. A PennyLane circuit costs about 3 ms per evaluation; this costs about 50 us.
`pennylane_energy` below builds the identical circuit in PennyLane, and the tests check that the
two agree to 1e-9, so the fast simulator is validated against a standard SDK.

Circuit for p layers on n qubits (gate angles a, one per gate occurrence):
    |+>^n, then for each layer l:  IsingZZ(a_e) on every edge e   [= exp(-i a_e Z_i Z_j / 2)]
                                   RX(a_i)     on every qubit i   [= exp(-i a_i X / 2)]
With a_e = gamma_l for all edges and a_i = 2 beta_l this is the standard QAOA ansatz for the
cost Hamiltonian H_C = sum_e (1/2) Z_i Z_j - m/2, whose value on a bitstring is  -cut(bitstring).
"""
import numpy as np


class MaxCutQAOA:
    def __init__(self, n, edges):
        self.n = n
        self.edges = [tuple(e) for e in edges]
        self.m = len(self.edges)
        N = 1 << n
        idx = np.arange(N)
        bits = (idx[:, None] >> np.arange(n)) & 1
        z = 1 - 2 * bits
        self.ZZ = np.array([z[:, i] * z[:, j] for i, j in self.edges], dtype=float)  # (m, N)
        self.cut = 0.5 * (1 - self.ZZ).sum(axis=0)  # cut value of every basis state
        self.cost = -self.cut  # energy of every basis state
        self.max_cut = float(self.cut.max())
        self.opt_mask = self.cut == self.max_cut

    # ---------------------------------------------------------------- circuit
    def n_angles(self, p):
        return p * (self.m + self.n)

    def angles(self, params):
        """params = [gamma_1..gamma_p, beta_1..beta_p] -> one angle per gate."""
        p = len(params) // 2
        gam, bet = params[:p], params[p:]
        a = []
        for g, b in zip(gam, bet):
            a += [g] * self.m + [2 * b] * self.n
        return np.array(a, dtype=float)

    def _rx_all(self, psi, thetas):
        n = self.n
        t = psi.reshape((2,) * n)
        for q in range(n):
            ax = n - 1 - q  # bit q of the index is axis n-1-q after reshape
            c, s = np.cos(thetas[q] / 2), np.sin(thetas[q] / 2)
            U = np.array([[c, -1j * s], [-1j * s, c]])
            t = np.moveaxis(np.tensordot(U, t, axes=([1], [ax])), 0, ax)
        return t.reshape(-1)

    def probs_from_angles(self, a):
        n, m = self.n, self.m
        p = len(a) // (m + n)
        psi = np.full(1 << n, 1 / np.sqrt(1 << n), dtype=complex)
        for l in range(p):
            ae = a[l * (m + n): l * (m + n) + m]
            at = a[l * (m + n) + m: (l + 1) * (m + n)]
            psi = psi * np.exp(-0.5j * (ae @ self.ZZ))
            psi = self._rx_all(psi, at)
        return np.abs(psi) ** 2

    def energy_angles(self, a):
        return float(self.probs_from_angles(a) @ self.cost)

    def probs(self, params):
        return self.probs_from_angles(self.angles(params))

    def energy(self, params):
        return self.energy_angles(self.angles(params))

    # ---------------------------------------------------------------- gradients
    def grad_param_shift(self, params):
        """Parameter-shift gradient, applied PER GATE OCCURRENCE.

        gamma_l is shared by m gates, so d/dgamma_l = sum over those gates of the per-gate
        derivative; likewise d/dbeta_l = 2 * sum over the n RX gates. Each per-gate derivative is
        [E(a + pi/2 e_k) - E(a - pi/2 e_k)] / 2, valid because every gate is exp(-i a G / 2) with
        G having eigenvalues +-1.
        """
        params = np.asarray(params, dtype=float)
        p = len(params) // 2
        a = self.angles(params)
        g_angle = np.zeros_like(a)
        for k in range(len(a)):
            ap, am = a.copy(), a.copy()
            ap[k] += np.pi / 2
            am[k] -= np.pi / 2
            g_angle[k] = 0.5 * (self.energy_angles(ap) - self.energy_angles(am))
        g = np.zeros(2 * p)
        for l in range(p):
            blk = g_angle[l * (self.m + self.n): (l + 1) * (self.m + self.n)]
            g[l] = blk[: self.m].sum()
            g[p + l] = 2.0 * blk[self.m:].sum()
        return g

    def grad_naive_shared_shift(self, params):
        """A WRONG gradient, kept only to demonstrate the pitfall: shifting the shared parameter
        by +-pi/2 as a whole is not valid, because gamma_l drives several gates at once and the
        generator sum_e Z_i Z_j / 2 has more than two distinct eigenvalues."""
        params = np.asarray(params, dtype=float)
        g = np.zeros_like(params)
        for k in range(len(params)):
            pp, pm = params.copy(), params.copy()
            pp[k] += np.pi / 2
            pm[k] -= np.pi / 2
            g[k] = 0.5 * (self.energy(pp) - self.energy(pm))
        return g

    def grad_finite_difference(self, params, eps=1e-6):
        params = np.asarray(params, dtype=float)
        g = np.zeros_like(params)
        for k in range(len(params)):
            e = np.zeros_like(params)
            e[k] = eps
            g[k] = (self.energy(params + e) - self.energy(params - e)) / (2 * eps)
        return g

    # ---------------------------------------------------------------- sampling
    def sample_energy(self, params, shots, rng):
        """Estimate <H_C> from `shots` measured bitstrings (finite-shot estimator)."""
        pr = self.probs(params)
        draws = rng.choice(len(pr), size=shots, p=pr / pr.sum())
        return float(self.cost[draws].mean())

    def summary(self, params):
        pr = self.probs(params)
        e = float(pr @ self.cost)
        return dict(expected_cut=-e, approx_ratio=-e / self.max_cut, prob_optimal=float(pr[self.opt_mask].sum()))


# -------------------------------------------------------------------- optimizers
def adam_ps(problem, params0, evals_budget, lr, b1=0.9, b2=0.999, eps=1e-8):
    """Adam driven by parameter-shift gradients, stopped by a budget of CIRCUIT EVALUATIONS
    (one gradient costs 2 per gate occurrence, plus 1 to evaluate the energy)."""
    x = np.array(params0, dtype=float)
    p = len(x) // 2
    per_step = 2 * problem.n_angles(p) + 1
    steps = max(evals_budget // per_step, 1)
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    for t in range(1, steps + 1):
        g = problem.grad_param_shift(x)
        m = b1 * m + (1 - b1) * g
        v = b2 * v + (1 - b2) * g * g
        x = x - lr * (m / (1 - b1 ** t)) / (np.sqrt(v / (1 - b2 ** t)) + eps)
    return x, steps * per_step


def spsa(f, params0, steps, a=0.2, c=0.1, A=None, alpha=0.602, gamma=0.101, seed=0):
    """Simultaneous-perturbation stochastic approximation. Two function evaluations per step,
    independent of the number of parameters. f may itself be noisy (finite shots)."""
    rng = np.random.default_rng(seed)
    x = np.array(params0, dtype=float)
    A = A if A is not None else 0.1 * steps
    for k in range(steps):
        ak = a / (k + 1 + A) ** alpha
        ck = c / (k + 1) ** gamma
        delta = rng.choice([-1.0, 1.0], size=x.shape)
        g = (f(x + ck * delta) - f(x - ck * delta)) / (2 * ck) * (1.0 / delta)
        x = x - ak * g
    return x, 2 * steps


# -------------------------------------------------------------------- PennyLane cross-check
def pennylane_energy(n, edges, params):
    """Identical QAOA circuit built in PennyLane (default.qubit). Used to validate the simulator."""
    import pennylane as qml
    p = len(params) // 2
    dev = qml.device("default.qubit", wires=n)
    obs = [qml.PauliZ(i) @ qml.PauliZ(j) for i, j in edges]
    H = qml.Hamiltonian([0.5] * len(edges), obs)

    @qml.qnode(dev)
    def circuit():
        for w in range(n):
            qml.Hadamard(w)
        for l in range(p):
            for i, j in edges:
                qml.IsingZZ(params[l], wires=[i, j])
            for w in range(n):
                qml.RX(2 * params[p + l], wires=w)
        return qml.expval(H)

    return float(circuit()) - len(edges) / 2.0
