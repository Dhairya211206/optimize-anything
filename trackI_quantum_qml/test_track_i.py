"""Correctness checks for Track I. Run: python -m pytest trackI_quantum_qml -q"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qalgs as qa  # noqa: E402
import qml_sim as qm  # noqa: E402
import qsim as qs  # noqa: E402


def test_deutsch_jozsa_distinguishes_constant_from_balanced():
    n = 4
    assert abs(qa.deutsch_jozsa(n, np.zeros(2 ** n)) - 1) < 1e-12
    assert abs(qa.deutsch_jozsa(n, np.ones(2 ** n)) - 1) < 1e-12
    rng = np.random.default_rng(0)
    for _ in range(10):
        f = np.zeros(2 ** n)
        f[rng.permutation(2 ** n)[: 2 ** (n - 1)]] = 1
        assert qa.deutsch_jozsa(n, f) < 1e-12


def test_bernstein_vazirani_recovers_every_secret():
    n = 5
    for s in range(2 ** n):
        got, p = qa.bernstein_vazirani(n, s)
        assert got == s and abs(p - 1) < 1e-12


def test_grover_matches_closed_form_for_all_iteration_counts():
    for n, marked in ((3, 5), (4, [2, 9]), (5, 17)):
        nm = len(np.atleast_1d(marked))
        for k in range(0, 8):
            assert abs(qa.grover_success(n, marked, k) - qa.grover_theory(n, nm, k)) < 1e-10


def test_grover_overshoot_reduces_success():
    n = 6
    k = qa.optimal_iterations(n)
    assert qa.grover_success(n, 7, k) > 0.99
    assert qa.grover_success(n, 7, 2 * k) < 0.5


def test_grover_fast_equals_gate_level_version():
    for n in (4, 6):
        k = qa.optimal_iterations(n)
        a = np.abs(qa.grover_state(n, 3, k)) ** 2
        b = np.abs(qa.grover_fast(n, 3, k)) ** 2
        assert np.allclose(a, b, atol=1e-12)


def test_qft_circuit_equals_dft_matrix_and_is_unitary():
    for m in (1, 2, 3, 4):
        Q = qa.qft_matrix_from_circuit(m)
        assert np.allclose(Q, qa.dft_matrix(m), atol=1e-12)
        assert np.allclose(Q.conj().T @ Q, np.eye(2 ** m), atol=1e-12)


def test_inverse_qft_inverts_qft():
    rng = np.random.default_rng(1)
    psi = rng.normal(size=16) + 1j * rng.normal(size=16)
    psi /= np.linalg.norm(psi)
    out = qs.qft_circuit(qs.qft_circuit(psi, [0, 1, 2, 3], 4), [0, 1, 2, 3], 4, inverse=True)
    assert np.allclose(out, psi, atol=1e-12)


def test_qpe_exact_for_representable_phase_and_peaked_otherwise():
    p = qa.qpe_distribution(5 / 16, 4)
    assert int(np.argmax(p)) == 5 and abs(p.max() - 1) < 1e-10
    p = qa.qpe_distribution(0.3, 6)
    assert abs(np.argmax(p) / 64 - 0.3) <= 1 / 64 and p.max() > 0.4


def test_shor_order_finding_distribution_and_factoring_15():
    for a in (2, 7, 8, 11, 13):
        p, t = qa.order_finding_distribution(a, 15)
        assert abs(p.sum() - 1) < 1e-9
        r = qa.true_order(a, 15)
        # probability mass sits on multiples of 2^t / r when r divides 2^t (r = 2, 4 here)
        peak = np.flatnonzero(p > 1e-6)
        assert all((y * r) % (2 ** t) == 0 for y in peak)
    assert qa.factors_from_order(7, 4, 15) == (3, 5)


def test_fft_inverse_qft_equals_circuit():
    psi = np.random.default_rng(2).normal(size=8) + 0j
    psi /= np.linalg.norm(psi)
    a = qs.qft_circuit(psi, [0, 1, 2], 3, inverse=True)
    b = np.fft.fft(psi) / math.sqrt(8)
    assert np.allclose(a, b, atol=1e-12)


def test_simulator_agrees_with_pennylane_qft_and_grover():
    import pennylane as qml
    dev = qml.device("default.qubit", wires=3)

    @qml.qnode(dev)
    def qft_circ(k):
        qml.BasisState(np.array([int(b) for b in format(k, "03b")]), wires=range(3))
        qml.QFT(wires=range(3))
        return qml.state()

    for k in range(8):
        assert np.allclose(qft_circ(k), qs.qft_circuit(qs.basis_state(3, k), [0, 1, 2], 3), atol=1e-10)

    @qml.qnode(dev)
    def grover(it):
        for w in range(3):
            qml.Hadamard(w)
        for _ in range(it):
            qml.FlipSign([1, 0, 1], wires=range(3))
            qml.GroverOperator(wires=range(3))
        return qml.probs(wires=range(3))

    for it in (1, 2):
        assert abs(grover(it)[5] - qa.grover_success(3, 5, it)) < 1e-10


# ------------------------------------------------------------------ QML
def test_qnn_matches_pennylane():
    import pennylane as qml
    rng = np.random.default_rng(0)
    w = rng.uniform(-3, 3, (2, 2, 2))
    X = rng.uniform(0, np.pi, (4, 2))
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev)
    def circ(x, w):
        for l in range(2):
            for q in range(2):
                qml.RY(x[q], wires=q)
            for q in range(2):
                qml.RZ(w[l, q, 0], wires=q)
                qml.RY(w[l, q, 1], wires=q)
            qml.CNOT(wires=[0, 1])
        return qml.expval(qml.PauliZ(0))

    ref = np.array([circ(x, w) for x in X])
    assert np.allclose(qm.qnn_expval(X, w), ref, atol=1e-10)


def test_qnn_parameter_shift_gradient_matches_finite_differences():
    rng = np.random.default_rng(1)
    w = rng.uniform(-3, 3, (2, 2, 2))
    X = rng.uniform(0, np.pi, (5, 2))
    g = qm.qnn_grad_expval(X, w)
    eps = 1e-6
    for idx in np.ndindex(*w.shape):
        wp, wm = w.copy(), w.copy()
        wp[idx] += eps
        wm[idx] -= eps
        fd = (qm.qnn_expval(X, wp) - qm.qnn_expval(X, wm)) / (2 * eps)
        assert np.allclose(g[(slice(None),) + idx], fd, atol=1e-6)


def test_qnn_training_reduces_loss():
    rng = np.random.default_rng(3)
    X = rng.uniform(0, np.pi, (40, 2))
    y = np.where(X[:, 0] + X[:, 1] > np.pi, 1.0, -1.0)
    _, hist, runs = qm.train_qnn(X, y, layers=2, epochs=60, seed=0)
    assert hist[-1] < hist[0] and runs == 60 * 40 * (1 + 2 * 8)


def test_quantum_kernel_is_symmetric_psd_with_unit_diagonal():
    X = np.random.default_rng(0).uniform(0, np.pi, (20, 2))
    K = qm.kernel_matrix(X, X)
    assert np.allclose(K, K.T, atol=1e-12) and np.allclose(np.diag(K), 1, atol=1e-12)
    assert np.linalg.eigvalsh(K).min() > -1e-10
