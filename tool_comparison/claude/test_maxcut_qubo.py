import numpy as np
import pytest

from maxcut_qubo import (all_assignments, build_graph, cut_value, ising_energy, maxcut_qubo, qubo_energy,
                         qubo_to_ising, simulated_annealing)

A = build_graph()
Q = maxcut_qubo(A)
J, h, OFFSET = qubo_to_ising(Q)
X = all_assignments(8)


def test_graph_has_8_nodes_and_18_edges():
    assert A.shape == (8, 8) and A.sum() / 2 == 18 and np.allclose(A, A.T) and np.all(np.diag(A) == 0)


def test_qubo_energy_is_minus_cut_for_all_256_assignments():
    assert len(X) == 256
    for x in X:
        assert qubo_energy(x, Q) == pytest.approx(-cut_value(x, A))


def test_ising_energy_equals_qubo_energy_for_all_256_assignments():
    for x in X:
        s = 2 * x - 1
        assert ising_energy(s, J, h, OFFSET) == pytest.approx(qubo_energy(x, Q))


def test_annealer_always_returns_valid_binary_vector():
    rng = np.random.default_rng(0)
    for _ in range(50):
        x, e = simulated_annealing(Q, rng)
        assert x.shape == (8,) and set(np.unique(x)) <= {0, 1}
        assert e == pytest.approx(qubo_energy(x, Q))  # the reported energy matches the returned vector
