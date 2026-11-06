"""Batched circuit simulation for the QML experiments (Track I): a data re-uploading variational classifier (QNN)
with exact parameter-shift gradients, and a ZZ-feature-map quantum kernel. SIMULATED, ideal qubits."""
import numpy as np

N_QUBITS = 2


def _apply(psi, U, q, n):
    """psi: (B, 2, ..., 2). U: (2,2) shared or (B,2,2) per sample."""
    x = np.moveaxis(psi, 1 + q, -1)
    x = np.einsum("b...j,bij->b...i", x, U) if U.ndim == 3 else x @ U.T
    return np.moveaxis(x, -1, 1 + q)


def _cnot(psi, c, t):
    p = psi.copy()
    idx = [slice(None)] * psi.ndim
    idx[1 + c] = 1
    sub = p[tuple(idx)]
    tt = 1 + t if t < c else t  # axis of the target after removing the control axis
    p[tuple(idx)] = np.flip(sub, axis=tt)
    return p


def ry(theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    if np.ndim(theta) == 0:
        return np.array([[c, -s], [s, c]], complex)
    U = np.zeros((len(theta), 2, 2), complex)
    U[:, 0, 0], U[:, 0, 1], U[:, 1, 0], U[:, 1, 1] = c, -s, s, c
    return U


def rz(theta):
    e = np.exp(-0.5j * theta)
    if np.ndim(theta) == 0:
        return np.array([[e, 0], [0, np.conj(e)]], complex)
    U = np.zeros((len(theta), 2, 2), complex)
    U[:, 0, 0], U[:, 1, 1] = e, np.conj(e)
    return U


def phase(theta):
    """diag(1, e^{i theta}) per sample"""
    U = np.zeros((len(theta), 2, 2), complex)
    U[:, 0, 0] = 1
    U[:, 1, 1] = np.exp(1j * theta)
    return U


H2 = np.array([[1, 1], [1, -1]], complex) / np.sqrt(2)


def init(B, n=N_QUBITS):
    psi = np.zeros((B,) + (2,) * n, complex)
    psi[(slice(None),) + (0,) * n] = 1
    return psi


# ------------------------------------------------------------------ QNN
def qnn_state(X, w):
    """w has shape (layers, qubits, 2). Each layer: RY(x_q) data encoding, then RZ(w0) RY(w1) per qubit, then CNOT(0,1)."""
    B, n = len(X), N_QUBITS
    psi = init(B)
    for layer in range(w.shape[0]):
        for q in range(n):
            psi = _apply(psi, ry(X[:, q]), q, n)
        for q in range(n):
            psi = _apply(psi, rz(w[layer, q, 0]), q, n)
            psi = _apply(psi, ry(w[layer, q, 1]), q, n)
        psi = _cnot(psi, 0, 1)
    return psi


def qnn_expval(X, w):
    """<Z_0>, in [-1, 1]"""
    p = np.abs(qnn_state(X, w)) ** 2  # shape (B, 2, 2); first axis after the batch is qubit 0
    return p[:, 0, :].sum(axis=1) - p[:, 1, :].sum(axis=1)


def qnn_grad_expval(X, w):
    """Exact parameter-shift gradient of <Z_0> for every sample: returns (B, layers, qubits, 2). Valid because every
    trainable angle drives one RZ/RY gate and the data-encoding gates contain no trainable parameter."""
    g = np.zeros((len(X),) + w.shape)
    for idx in np.ndindex(*w.shape):
        wp, wm = w.copy(), w.copy()
        wp[idx] += np.pi / 2
        wm[idx] -= np.pi / 2
        g[(slice(None),) + idx] = 0.5 * (qnn_expval(X, wp) - qnn_expval(X, wm))
    return g


def train_qnn(X, y, layers=4, epochs=120, lr=0.1, seed=0):
    """Adam on the mean squared error between <Z_0> and the +-1 label. Returns (weights, loss history,
    circuit executions). One epoch needs 1 + 2P circuit runs per sample (forward + parameter-shift pair per parameter)."""
    rng = np.random.default_rng(seed)
    w = rng.uniform(-np.pi, np.pi, (layers, N_QUBITS, 2))
    m, v = np.zeros_like(w), np.zeros_like(w)
    hist, runs = [], 0
    P = w.size
    for t in range(1, epochs + 1):
        f = qnn_expval(X, w)
        g = qnn_grad_expval(X, w)
        grad = np.einsum("b,b...->...", 2 * (f - y), g) / len(X)
        hist.append(float(np.mean((f - y) ** 2)))
        runs += len(X) * (1 + 2 * P)
        m = 0.9 * m + 0.1 * grad
        v = 0.999 * v + 0.001 * grad ** 2
        w = w - lr * (m / (1 - 0.9 ** t)) / (np.sqrt(v / (1 - 0.999 ** t)) + 1e-8)
    return w, hist, runs


# ------------------------------------------------------------------ quantum kernel
def zz_feature_state(X, reps=2):
    """Qiskit-style ZZFeatureMap on 2 qubits: reps x [H, P(2 x_i), CNOT, P(2 (pi-x0)(pi-x1)) on q1, CNOT]."""
    B, n = len(X), N_QUBITS
    psi = init(B)
    for _ in range(reps):
        for q in range(n):
            psi = _apply(psi, H2, q, n)
            psi = _apply(psi, phase(2 * X[:, q]), q, n)
        psi = _cnot(psi, 0, 1)
        psi = _apply(psi, phase(2 * (np.pi - X[:, 0]) * (np.pi - X[:, 1])), 1, n)
        psi = _cnot(psi, 0, 1)
    return psi.reshape(B, -1)


def kernel_matrix(XA, XB, reps=2):
    A, Bm = zz_feature_state(XA, reps), zz_feature_state(XB, reps)
    return np.abs(A.conj() @ Bm.T) ** 2
