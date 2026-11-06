"""Minimal state-vector simulator (NumPy) used for the Track I circuits. Qubit 0 is the most significant bit,
the same convention as PennyLane. Everything here is a classical SIMULATION of ideal (noise-free) qubits."""
import numpy as np

H = np.array([[1, 1], [1, -1]], complex) / np.sqrt(2)
X = np.array([[0, 1], [1, 0]], complex)
Z = np.array([[1, 0], [0, -1]], complex)


def zero_state(n):
    s = np.zeros(2 ** n, complex)
    s[0] = 1.0
    return s


def basis_state(n, k):
    s = np.zeros(2 ** n, complex)
    s[k] = 1.0
    return s


def apply_1q(psi, U, q, n):
    t = np.tensordot(U, psi.reshape((2,) * n), axes=([1], [q]))
    return np.moveaxis(t, 0, q).reshape(-1)


def apply_controlled(psi, U, c, t, n):
    """Apply the 2x2 matrix U to qubit t if qubit c is 1."""
    p = psi.reshape((2,) * n).copy()
    idx = [slice(None)] * n
    idx[c] = 1
    sub = p[tuple(idx)]
    tt = t if t < c else t - 1
    p[tuple(idx)] = np.moveaxis(np.tensordot(U, sub, axes=([1], [tt])), 0, tt)
    return p.reshape(-1)


def apply_cphase(psi, theta, c, t, n):
    p = psi.reshape((2,) * n).copy()
    idx = [slice(None)] * n
    idx[c] = 1
    idx[t] = 1
    p[tuple(idx)] *= np.exp(1j * theta)
    return p.reshape(-1)


def apply_swap(psi, a, b, n):
    return np.swapaxes(psi.reshape((2,) * n), a, b).reshape(-1).copy()


def apply_h_all(psi, qubits, n):
    for q in qubits:
        psi = apply_1q(psi, H, q, n)
    return psi


def qft_circuit(psi, qubits, n, inverse=False):
    """Textbook QFT on the listed qubits (first listed = most significant): Hadamard, then controlled phases
    of 2*pi/2^m from every later qubit, then swaps to reverse the bit order."""
    m = len(qubits)
    ops = []
    for j in range(m):
        ops.append(("h", qubits[j]))
        for k in range(j + 1, m):
            ops.append(("cp", qubits[k], qubits[j], 2 * np.pi / 2 ** (k - j + 1)))
    for j in range(m // 2):
        ops.append(("swap", qubits[j], qubits[m - 1 - j]))
    if inverse:
        ops = ops[::-1]
    for op in ops:
        if op[0] == "h":
            psi = apply_1q(psi, H, op[1], n)
        elif op[0] == "cp":
            psi = apply_cphase(psi, -op[3] if inverse else op[3], op[1], op[2], n)
        else:
            psi = apply_swap(psi, op[1], op[2], n)
    return psi


def qft_gate_count(m):
    return dict(hadamards=m, controlled_phases=m * (m - 1) // 2, swaps=m // 2)
