"""VQE on a transverse-field Ising chain (Track C). SIMULATION ONLY.

H = - sum_i Z_i Z_{i+1} - h sum_i X_i   (open chain, n qubits, h = 1)
The exact ground energy comes from diagonalising the 2^n x 2^n matrix, which is the classical
baseline. Ansatz: hardware-efficient, (L+1) RY layers separated by L CNOT chains.
"""
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp


def tfim(n, h=1.0):
    coeffs, ops = [], []
    for i in range(n - 1):
        coeffs.append(-1.0)
        ops.append(qml.PauliZ(i) @ qml.PauliZ(i + 1))
    for i in range(n):
        coeffs.append(-h)
        ops.append(qml.PauliX(i))
    return qml.Hamiltonian(coeffs, ops)


def exact_ground_energy(H, n):
    return float(np.linalg.eigvalsh(qml.matrix(H, wire_order=range(n)))[0])


def make_qnode(n, L, H, diff_method="parameter-shift"):
    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev, diff_method=diff_method)
    def energy(params):
        for l in range(L + 1):
            for q in range(n):
                qml.RY(params[l, q], wires=q)
            if l < L:
                for q in range(n - 1):
                    qml.CNOT(wires=[q, q + 1])
        return qml.expval(H)

    return dev, energy


def run_optimizer(name, n, L, H, e0, seed, steps, stepsize, spsa_a=0.3, tol=1e-2):
    """Run one optimizer from a random start. Returns error curve and circuit executions used."""
    dev, energy = make_qnode(n, L, H)
    # Separate device used ONLY to log the error each step, so logging evaluations are not
    # counted in the execution totals of the optimizer being measured.
    _, energy_log = make_qnode(n, L, H)
    rng = np.random.default_rng(seed)
    p0 = rng.uniform(0, 2 * np.pi, (L + 1, n))
    params = pnp.array(p0, requires_grad=True)
    errs, execs_at_tol = [], None
    with qml.Tracker(dev) as tr:
        if name == "SPSA":
            f = lambda x: float(energy(pnp.array(x.reshape(L + 1, n), requires_grad=False)))  # noqa: E731
            x = p0.ravel().copy()
            srng = np.random.default_rng(seed + 1)
            A = 0.1 * steps
            for k in range(steps):
                ak = spsa_a / (k + 1 + A) ** 0.602
                ck = 0.15 / (k + 1) ** 0.101
                d = srng.choice([-1.0, 1.0], size=x.shape)
                g = (f(x + ck * d) - f(x - ck * d)) / (2 * ck) * (1.0 / d)
                x = x - ak * g
                errs.append(float(energy_log(pnp.array(x.reshape(L + 1, n), requires_grad=False))) - e0)
                if execs_at_tol is None and errs[-1] < tol:
                    execs_at_tol = tr.totals.get("executions", None)
        else:
            if name == "GD":
                opt = qml.GradientDescentOptimizer(stepsize)
            elif name == "Adam":
                opt = qml.AdamOptimizer(stepsize)
            elif name == "QNG":
                opt = qml.QNGOptimizer(stepsize, approx="block-diag")
            else:
                raise ValueError(name)
            for _ in range(steps):
                params = opt.step(energy, params)
                errs.append(float(energy_log(params)) - e0)
                if execs_at_tol is None and errs[-1] < tol:
                    execs_at_tol = tr.totals.get("executions", None)
        total_execs = tr.totals.get("executions", None)
    return dict(errors=errs, final_error=errs[-1], execs_at_tol=execs_at_tol, total_execs=total_execs)
