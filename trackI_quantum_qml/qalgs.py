"""Quantum algorithms written from scratch on the NumPy simulator (Track I): Deutsch-Jozsa, Bernstein-Vazirani,
Grover, QFT check, quantum phase estimation, Shor order finding. All SIMULATED, noise-free unless stated."""
import math
from fractions import Fraction

import numpy as np

import qsim as qs


# ------------------------------------------------------------------ Deutsch-Jozsa / Bernstein-Vazirani
def phase_oracle(psi, f_values):
    """Black-box phase oracle |x> -> (-1)^f(x) |x>. One call = one query."""
    return psi * (1 - 2 * np.asarray(f_values))


def hadamard_test_circuit(n, f_values):
    """H^n, oracle, H^n on n qubits starting from |0..0>; returns the final state. Uses ONE oracle query."""
    psi = qs.apply_h_all(qs.zero_state(n), range(n), n)
    psi = phase_oracle(psi, f_values)
    return qs.apply_h_all(psi, range(n), n)


def deutsch_jozsa(n, f_values):
    """Returns the probability of measuring all zeros: 1 if f is constant, 0 if balanced."""
    return float(abs(hadamard_test_circuit(n, f_values)[0]) ** 2)


def bernstein_vazirani(n, secret):
    """f(x) = secret . x mod 2. Returns (most likely outcome, its probability); one quantum query."""
    f = np.array([bin(x & secret).count("1") & 1 for x in range(2 ** n)])
    p = np.abs(hadamard_test_circuit(n, f)) ** 2
    return int(np.argmax(p)), float(p.max())


# ------------------------------------------------------------------ Grover
def grover_state(n, marked, iterations):
    """Gate-level Grover: H^n, then `iterations` x (oracle + diffusion). Diffusion = H^n X^n (CZ..Z) X^n H^n.
    Oracle calls = iterations."""
    marked = np.atleast_1d(marked)
    f = np.zeros(2 ** n)
    f[marked] = 1
    psi = qs.apply_h_all(qs.zero_state(n), range(n), n)
    for _ in range(iterations):
        psi = phase_oracle(psi, f)
        psi = qs.apply_h_all(psi, range(n), n)
        for q in range(n):
            psi = qs.apply_1q(psi, qs.X, q, n)
        psi[-1] *= -1  # multi-controlled Z on |1...1>
        for q in range(n):
            psi = qs.apply_1q(psi, qs.X, q, n)
        psi = qs.apply_h_all(psi, range(n), n)
        psi = -psi  # global phase of the gate construction, irrelevant but keeps 2|s><s| - I exactly
    return psi


def grover_success(n, marked, iterations):
    psi = grover_state(n, marked, iterations)
    return float(sum(abs(psi[m]) ** 2 for m in np.atleast_1d(marked)))


def grover_theory(n, n_marked, k):
    theta = math.asin(math.sqrt(n_marked / 2 ** n))
    return math.sin((2 * k + 1) * theta) ** 2


def optimal_iterations(n, n_marked=1):
    theta = math.asin(math.sqrt(n_marked / 2 ** n))
    return max(0, round(math.pi / (4 * theta) - 0.5))


def grover_fast(n, marked, iterations):
    """Same algorithm as grover_state but with the diffusion applied as 2<s|psi>|s> - psi (identical result,
    O(N) per iteration instead of O(n N)); used only for the large-n scaling run."""
    N = 2 ** n
    psi = np.full(N, 1 / math.sqrt(N), complex)
    for _ in range(iterations):
        psi[marked] *= -1
        psi = 2 * psi.mean() - psi
    return psi


def classical_linear_search_queries(N, marked, rng):
    """Expected number of queries of random-order linear search for one marked item is (N+1)/2."""
    order = rng.permutation(N)
    return int(np.flatnonzero(order == marked)[0]) + 1


# ------------------------------------------------------------------ QFT
def qft_matrix_from_circuit(m):
    n = m
    cols = [qs.qft_circuit(qs.basis_state(n, k), list(range(n)), n) for k in range(2 ** n)]
    return np.array(cols).T


def dft_matrix(m):
    N = 2 ** m
    j, k = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    return np.exp(2j * np.pi * j * k / N) / np.sqrt(N)


# ------------------------------------------------------------------ phase estimation
def qpe_distribution(phi, t):
    """QPE of the phase gate U|1> = e^{2 pi i phi}|1> with t counting qubits (target prepared in |1>).
    Returns the probability of each counting-register outcome y (estimate = y / 2^t)."""
    n = t + 1
    psi = qs.apply_1q(qs.zero_state(n), qs.X, t, n)  # target |1>
    psi = qs.apply_h_all(psi, range(t), n)
    for k in range(t):  # counting qubit k controls U^(2^(t-1-k))
        psi = qs.apply_cphase(psi, 2 * np.pi * phi * 2 ** (t - 1 - k), k, t, n)
    psi = qs.qft_circuit(psi, list(range(t)), n, inverse=True)
    p = (np.abs(psi.reshape(2 ** t, 2)) ** 2).sum(axis=1)
    return p


# ------------------------------------------------------------------ Shor (order finding by QPE, oracle-level modular exponentiation)
def order_finding_distribution(a, N):
    """Counting register of t = 2L qubits (L = bits of N), target register of L qubits starting at |1>.
    Controlled modular multiplication by a^(2^j) is applied as a permutation of the target basis states (an
    ORACLE: it is not compiled into gates). The inverse QFT is applied with the FFT, which test_track_i
    checks equals the QFT circuit. Returns the distribution over counting outcomes."""
    L = N.bit_length()
    t = 2 * L
    T, M = 2 ** t, 2 ** L
    psi = np.zeros((T, M), complex)
    psi[:, 1] = 1 / math.sqrt(T)  # Hadamards on the counting register, target |1>
    idx = np.arange(T)
    y = np.arange(M)
    for k in range(t):
        m = pow(a, 2 ** (t - 1 - k), N)
        perm = np.where(y < N, (m * y) % N, y)
        rows = np.flatnonzero((idx >> (t - 1 - k)) & 1)
        new = psi.copy()
        new[rows[:, None], perm[None, :]] = psi[rows, :]
        psi = new
    psi = np.fft.fft(psi, axis=0) / math.sqrt(T)  # inverse QFT on the counting register
    return (np.abs(psi) ** 2).sum(axis=1), t


def true_order(a, N):
    r, x = 1, a % N
    while x != 1:
        x = (x * a) % N
        r += 1
    return r


def order_from_measurement(y, t, a, N):
    """Continued-fraction step: best fraction with denominator < N close to y / 2^t, then check a^r = 1."""
    if y == 0:
        return None
    r = Fraction(y, 2 ** t).limit_denominator(N).denominator
    for mult in (1, 2, 3, 4):
        if pow(a, r * mult, N) == 1:
            return r * mult
    return None


def factors_from_order(a, r, N):
    if r is None or r % 2 or pow(a, r // 2, N) == N - 1:
        return None
    for d in (math.gcd(pow(a, r // 2, N) - 1, N), math.gcd(pow(a, r // 2, N) + 1, N)):
        if 1 < d < N:
            return tuple(sorted((d, N // d)))
    return None
