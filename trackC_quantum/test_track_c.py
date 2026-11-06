"""Correctness checks for Track C. Run: python -m pytest trackC_quantum -q"""
import json
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import barren as bp  # noqa: E402
import qaoa_sim as qs  # noqa: E402
import run_track_c as rt  # noqa: E402

INST = json.load(open(os.path.join(HERE, "..", "trackB_discrete", "results", "maxcut_instance.json")))
Q = qs.MaxCutQAOA(INST["n"], INST["edges"])


def rand_params(p, seed):
    rng = np.random.default_rng(seed)
    return np.r_[rng.uniform(0, np.pi, p), rng.uniform(0, np.pi / 2, p)]


def test_max_cut_matches_track_b_exact_optimum():
    assert Q.max_cut == INST["optimal_cut"] == 14


def test_zero_angles_give_uniform_superposition_energy():
    assert abs(Q.energy(np.zeros(2)) + Q.m / 2) < 1e-12


def test_probabilities_normalised():
    assert abs(Q.probs(rand_params(3, 0)).sum() - 1) < 1e-12


def test_fast_simulator_matches_pennylane():
    for p in (1, 2):
        prm = rand_params(p, p)
        assert abs(Q.energy(prm) - qs.pennylane_energy(Q.n, Q.edges, prm)) < 1e-9


def test_per_gate_parameter_shift_matches_finite_differences():
    for p in (1, 2, 3):
        prm = rand_params(p, 10 + p)
        assert np.max(np.abs(Q.grad_param_shift(prm) - Q.grad_finite_difference(prm))) < 1e-6


def test_naive_shared_parameter_shift_is_wrong():
    prm = rand_params(1, 5)
    err = np.max(np.abs(Q.grad_naive_shared_shift(prm) - Q.grad_finite_difference(prm)))
    assert err > 0.1


def test_qaoa_beats_random_guess_after_optimisation():
    x, _ = qs.adam_ps(Q, rand_params(1, 0), 2000, 0.1)
    assert Q.summary(x)["approx_ratio"] > (Q.m / 2) / Q.max_cut + 0.1


def test_spsa_minimises_a_quadratic():
    x, _ = qs.spsa(lambda v: float(np.sum((v - 1.0) ** 2)), np.zeros(4), 400, a=0.5, c=0.1, seed=0)
    assert np.sum((x - 1.0) ** 2) < 0.1


def test_finite_shot_estimator_is_unbiased_and_has_sqrt_shots_variance():
    prm = rand_params(1, 3)
    pr = Q.probs(prm)
    exact = pr @ Q.cost
    sigma = np.sqrt(pr @ Q.cost ** 2 - exact ** 2)
    rng = np.random.default_rng(0)
    est = np.array([Q.sample_energy(prm, 400, rng) for _ in range(400)])
    assert abs(est.mean() - exact) < 4 * sigma / np.sqrt(400 * 400)
    assert 0.8 < est.std() / (sigma / np.sqrt(400)) < 1.2


def test_barren_simulator_matches_pennylane():
    th = np.random.default_rng(0).uniform(0, 2 * np.pi, (3, 5))
    assert np.allclose(bp.HEA(5).costs(th), bp.pennylane_cost(th), atol=1e-10)


def test_barren_gradient_matches_finite_difference():
    h = bp.HEA(4)
    th = np.random.default_rng(1).uniform(0, 2 * np.pi, (3, 4))
    g, l = h.grad_one(th, 1, 2)
    e = 1e-6
    tp, tm = th.copy(), th.copy()
    tp[1, 2] += e
    tm[1, 2] -= e
    assert abs(g - (h.costs(tp)[0] - h.costs(tm)[0]) / (2 * e)) < 1e-6
    assert abs(l - (h.costs(tp)[1] - h.costs(tm)[1]) / (2 * e)) < 1e-6


def test_deep_global_cost_gradient_variance_shrinks_with_qubits():
    v4 = bp.gradient_variance(4, 8, 150, seed=1)[0]
    v8 = bp.gradient_variance(8, 16, 150, seed=1)[0]
    assert v8 < v4 / 3


def test_depolarizing_noise_limits():
    prm = np.array([0.7, 0.3])
    assert abs(rt.noisy_energy_pl(Q, prm, 0.0) - Q.energy(prm)) < 1e-9
    assert abs(rt.noisy_energy_pl(Q, prm, 0.75) + Q.m / 2) < 1e-6  # fully depolarized -> random guess
