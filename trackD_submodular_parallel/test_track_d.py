"""Correctness checks for Track D. Run: python -m pytest trackD_submodular_parallel -q"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import federated as fd  # noqa: E402
import multitask as mt  # noqa: E402
import parallel_exp as pe  # noqa: E402
import submodular as sm  # noqa: E402


# ------------------------------------------------------------------ submodular
def test_facility_location_is_monotone_submodular_on_random_triples():
    f = sm.FacilityLocation(100, 15, seed=0)
    r = sm.check_conditions(f, f.n, trials=1500)
    assert r["diminishing_returns_violations"] == 0 and r["monotonicity_violations"] == 0


def test_synergy_objective_is_detected_as_not_submodular():
    r, R = sm.load_trackb_objective()
    r2 = sm.check_conditions(sm.SynergySelection(r, R), len(r), trials=1500)
    assert r2["diminishing_returns_violations"] > 0


def test_penalised_selection_is_submodular_but_not_monotone():
    r, R = sm.load_trackb_objective()
    res = sm.check_conditions(sm.PenalisedSelection(r, R), len(r), trials=1500)
    assert res["diminishing_returns_violations"] == 0
    assert res["monotonicity_violations"] > 0


def test_greedy_meets_one_minus_one_over_e_on_facility_location():
    for seed in range(6):
        f = sm.FacilityLocation(120, 14, seed=seed)
        _, g = sm.greedy(f, f.n, 4)
        _, opt = sm.brute_force(f, f.n, 4)
        assert g >= (1 - 1 / np.e) * opt - 1e-9
        assert g <= opt + 1e-9


def test_lazy_greedy_matches_greedy_value_with_fewer_evaluations():
    f1 = sm.FacilityLocation(150, 60, seed=3)
    f2 = sm.FacilityLocation(150, 60, seed=3)
    _, v1 = sm.greedy(f1, f1.n, 8)
    _, v2 = sm.lazy_greedy(f2, f2.n, 8)
    assert abs(v1 - v2) < 1e-9 and f2.calls < f1.calls


# ------------------------------------------------------------------ parallel
def test_amdahl_inverse_roundtrip_and_limits():
    s = 0.1
    S = pe.amdahl_speedup(s, 4)
    assert abs(pe.serial_fraction_from_speedup(S, 4) - s) < 1e-12
    assert pe.amdahl_speedup(s, 10 ** 9) < 1 / s + 1e-6
    assert abs(pe.gustafson_speedup(0.0, 8) - 8) < 1e-12


def test_data_parallel_matches_serial_result():
    tasks = [2000 + 10 * i for i in range(24)]
    assert pe.run_data_parallel(tasks, 1) == pe.run_data_parallel(tasks, 2)
    assert sorted(pe.run_dynamic(tasks, 2)) == sorted(pe.run_data_parallel(tasks, 1))


def test_simulated_schedules_respect_lower_bound_and_ordering():
    rng = np.random.default_rng(0)
    costs = rng.lognormal(0, 1.0, 400)
    for p in (4, 16):
        lb = max(costs.sum() / p, costs.max())
        res = {s: pe.simulate_schedule(costs, p, s)[0] for s in ("static_block", "round_robin", "dynamic", "lpt", "work_stealing")}
        for v in res.values():
            assert v >= lb - 1e-9
        assert res["lpt"] <= res["dynamic"] + 1e-9 + costs.max()  # LPT is within one task of list scheduling
        assert res["work_stealing"] <= res["static_block"] + 1e-9


def test_uniform_tasks_need_no_balancing():
    costs = np.ones(64)
    assert pe.simulate_schedule(costs, 8, "static_block")[0] == 8.0


def test_pipeline_delivers_all_microbatches():
    t, got = pe.run_pipeline([0.001, 0.001], 6)
    assert got == 6


def test_model_parallel_output_equals_single_process():
    rng = np.random.default_rng(0)
    x, w = rng.normal(size=(8, 16)), rng.normal(size=(16, 12))
    pe.run_model_parallel(x, w, repeats=1)  # asserts equality internally


# ------------------------------------------------------------------ federated
def test_fedavg_learns_on_iid_data():
    clients, test = fd.make_clients(6, 150, 10, non_iid=False, seed=1)
    _, hist, _ = fd.fedavg(clients, test, rounds=30, local_steps=5)
    assert hist[-1][1] > 0.75 and hist[-1][0] < hist[0][0]


def test_fedavg_with_one_client_equals_local_sgd_average_of_itself():
    clients, test = fd.make_clients(1, 100, 6, seed=2)
    w, _, _ = fd.fedavg(clients, test, rounds=1, local_steps=3, seed=5)
    rng = np.random.default_rng(5)
    expected = fd.local_sgd(np.zeros(6), *clients[0], 3, 0.1, 20, rng)
    assert np.allclose(w, expected)


# ------------------------------------------------------------------ multi-task
def test_task_gradients_match_finite_differences():
    X, Y = mt.make_data(60, 5, seed=0)
    net = mt.TwoTaskNet(5, h=4, seed=0)
    gs = net.task_grads(X, Y)
    eps = 1e-6
    for t in range(2):
        for pi, p in enumerate(net.params()):
            it = np.nditer(p, flags=["multi_index"])
            idx = it.multi_index
            old = p[idx]
            p[idx] = old + eps
            lp = net.task_losses(X, Y)[t]
            p[idx] = old - eps
            lm = net.task_losses(X, Y)[t]
            p[idx] = old
            assert abs(gs[t][pi][idx] - (lp - lm) / (2 * eps)) < 1e-5


def test_mgda_closed_form_matches_grid_search():
    rng = np.random.default_rng(0)
    for _ in range(10):
        g1, g2 = rng.normal(size=6), rng.normal(size=6)
        a = mt.mgda_alpha(g1, g2)
        grid = np.linspace(0, 1, 2001)
        best = grid[np.argmin([np.linalg.norm(x * g1 + (1 - x) * g2) for x in grid])]
        assert abs(a - best) < 1e-3


def test_gradnorm_and_mgda_weights_sum_to_two_and_training_reduces_loss():
    X, Y = mt.make_data(200, 6, seed=1)
    for m in ("equal", "mgda", "gradnorm"):
        net, wh = mt.train(m, X, Y, steps=400, seed=0)
        assert np.allclose(wh.sum(axis=1), 2.0)
        assert np.all(mt.relative_mse(net, X, Y) < 1.0)
