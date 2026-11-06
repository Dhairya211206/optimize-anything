"""Barren-plateau experiment (Track C). SIMULATION ONLY.

Circuit: L layers of [RY(theta) on every qubit, then a chain of CZ gates between neighbours],
starting from |0...0>. Parameters are drawn uniformly from [0, 2 pi).

Costs (both zero iff the output state is |0...0>):
    global: C_G = 1 - |<0...0|psi>|^2
    local : C_L = 1 - (1/n) sum_q P(qubit q measured as 0)

We estimate Var[ dC / d theta ] over random parameter draws for one fixed parameter (middle
layer, middle qubit), using the exact parameter-shift rule (RY(t) = exp(-i t Y / 2), so
dC/dt = [C(t + pi/2) - C(t - pi/2)] / 2).
"""
import numpy as np


class HEA:
    def __init__(self, n):
        self.n = n
        N = 1 << n
        idx = np.arange(N)
        # axis q of the reshaped state <-> bit (n-1-q) of the index
        bits = np.array([(idx >> (n - 1 - q)) & 1 for q in range(n)]).T  # (N, n); column q = qubit q
        self.cz_sign = (-1.0) ** (bits[:, :-1] * bits[:, 1:]).sum(axis=1)
        self.p0_masks = [(bits[:, q] == 0) for q in range(n)]

    def _ry(self, t, theta, q):
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        U = np.array([[c, -s], [s, c]])
        return np.moveaxis(np.tensordot(U, t, axes=([1], [q])), 0, q)

    def state(self, thetas):
        n = self.n
        L = thetas.shape[0]
        psi = np.zeros(1 << n)
        psi[0] = 1.0
        t = psi.reshape((2,) * n)
        for l in range(L):
            for q in range(n):
                t = self._ry(t, thetas[l, q], q)
            t = (t.reshape(-1) * self.cz_sign).reshape((2,) * n)
        return t.reshape(-1)

    def costs(self, thetas):
        psi = self.state(thetas)
        pr = psi ** 2
        c_global = 1.0 - pr[0]
        c_local = 1.0 - np.mean([pr[mask].sum() for mask in self.p0_masks])
        return c_global, c_local

    def grad_one(self, thetas, l, q):
        tp, tm = thetas.copy(), thetas.copy()
        tp[l, q] += np.pi / 2
        tm[l, q] -= np.pi / 2
        gp, lp = self.costs(tp)
        gm, lm = self.costs(tm)
        return 0.5 * (gp - gm), 0.5 * (lp - lm)


def gradient_variance(n, L, samples, seed=0):
    rng = np.random.default_rng(seed)
    h = HEA(n)
    gg, gl = [], []
    for _ in range(samples):
        th = rng.uniform(0, 2 * np.pi, (L, n))
        a, b = h.grad_one(th, L // 2, n // 2)
        gg.append(a)
        gl.append(b)
    return float(np.var(gg)), float(np.var(gl))


def pennylane_cost(thetas):
    """Same circuit and costs in PennyLane, used by the tests to validate HEA."""
    import pennylane as qml
    L, n = thetas.shape
    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev)
    def circ():
        for l in range(L):
            for q in range(n):
                qml.RY(thetas[l, q], wires=q)
            for q in range(n - 1):
                qml.CZ(wires=[q, q + 1])
        return qml.probs(wires=range(n))

    pr = np.array(circ())
    # PennyLane orders basis states with wire 0 as the most significant bit, as in HEA.
    bits = np.array([[(k >> (n - 1 - q)) & 1 for q in range(n)] for k in range(1 << n)])
    c_global = 1.0 - pr[0]
    c_local = 1.0 - np.mean([pr[bits[:, q] == 0].sum() for q in range(n)])
    return float(c_global), float(c_local)
