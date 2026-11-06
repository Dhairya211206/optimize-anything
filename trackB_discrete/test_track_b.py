"""Correctness checks for Track B. Run: python -m pytest trackB_discrete -q"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import discrete as dc  # noqa: E402
import qubo as qb  # noqa: E402


def test_exact_knapsack_solvers_agree_with_brute_force():
    for seed in range(12):
        v, w, cap = dc.make_instance(14, seed=seed)
        ref = dc.brute(v, w, cap)[0]
        for name in ("dp", "bnb", "ilp"):
            val, chosen, _ = getattr(dc, name)(v, w, cap)
            assert val == ref, (name, seed)
            assert dc.is_feasible(chosen, w, cap)
            assert int(np.sum(v[chosen])) == val  # reported value matches the reported set


def test_greedy_is_feasible_and_never_better_than_optimum():
    for seed in range(20):
        v, w, cap = dc.make_instance(16, seed=seed)
        g, chosen, _ = dc.greedy(v, w, cap)
        assert dc.is_feasible(chosen, w, cap)
        assert g <= dc.dp(v, w, cap)[0]


def test_greedy_can_be_arbitrarily_bad_on_known_instance():
    v, w, cap = np.array([2, 15]), np.array([1, 10]), 10
    assert dc.greedy(v, w, cap)[0] == 2
    assert dc.dp(v, w, cap)[0] == 15


def test_knapsack_edge_cases():
    assert dc.dp([5], [3], 2)[0] == 0          # nothing fits
    assert dc.dp([5], [3], 0)[0] == 0          # zero capacity
    assert dc.bnb([5], [3], 3)[0] == 5          # exact fit
    try:
        dc.dp([1, 2], [1], 5)
        assert False
    except ValueError:
        pass


def test_maxcut_qubo_energy_is_minus_cut_for_every_assignment():
    g = qb.maxcut_graph(8, 0.5, 7)
    Q = qb.maxcut_qubo(g)
    for x in qb.all_bitstrings(8):
        assert qb.qubo_energy(Q, x) == -qb.cut_value(g, x)


def test_ising_energy_equals_qubo_energy_for_every_assignment():
    g = qb.maxcut_graph(8, 0.5, 7)
    Q = qb.maxcut_qubo(g)
    h, J, c = qb.qubo_to_ising(Q)
    for x in qb.all_bitstrings(8):
        s = 1 - 2 * x.astype(float)  # x=0 -> s=+1, x=1 -> s=-1
        assert abs(qb.ising_energy(h, J, c, s) - qb.qubo_energy(Q, x)) < 1e-9


def test_ising_conversion_on_a_random_dense_qubo():
    rng = np.random.default_rng(0)
    n = 6
    Q = np.triu(rng.normal(size=(n, n)))
    h, J, c = qb.qubo_to_ising(Q)
    for x in qb.all_bitstrings(n):
        s = 1 - 2 * x.astype(float)
        assert abs(qb.ising_energy(h, J, c, s) - qb.qubo_energy(Q, x)) < 1e-9


def test_feature_selection_qubo_matches_penalised_objective():
    X, y = qb.make_feature_data(200, seed=1)
    k, P, a = 4, 2.0, 1.0
    Q, r, R = qb.feature_selection_qubo(X, y, k, alpha=a, penalty=P)
    rng = np.random.default_rng(0)
    for _ in range(50):
        x = rng.integers(0, 2, X.shape[1])
        lhs = qb.qubo_energy(Q, x) + P * k * k
        rhs = -qb.fs_objective(x, r, R, a) + P * (x.sum() - k) ** 2
        assert abs(lhs - rhs) < 1e-9


def test_large_penalty_enforces_cardinality():
    X, y = qb.make_feature_data(300, seed=2)
    for k in (3, 4, 6):
        Q_big, _, _ = qb.feature_selection_qubo(X, y, k, penalty=5.0)
        _, x_big, _ = qb.brute_force_qubo(Q_big)
        assert x_big.sum() == k
    # NOTE: a small penalty does not always break the constraint (it depends on the data and
    # k), so that is measured in run_track_b.py's penalty sweep, not asserted here.


def test_simulated_annealing_finds_maxcut_optimum_on_small_graph():
    g = qb.maxcut_graph(8, 0.5, 7)
    Q = qb.maxcut_qubo(g)
    opt = qb.brute_force_qubo(Q)[0]
    best = min(qb.simulated_annealing(Q, seed=s)[0] for s in range(10))
    assert abs(best - opt) < 1e-9
