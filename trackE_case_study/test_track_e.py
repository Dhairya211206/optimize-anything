"""Correctness checks for Track E. Run: python -m pytest trackE_case_study -q"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import roster as R  # noqa: E402


def tiny(seed):
    return R.make_instance(3, 2, seed=seed, avail_prob=1.0, demand_frac=0.6)


def test_ilp_matches_brute_force_on_tiny_instances():
    for seed in range(4):
        inst = tiny(seed)
        _, bv = R.brute_force(inst)
        a, info = R.ilp(inst, time_limit=20)
        e = R.evaluate(inst, a)
        assert info["proven_optimal"] and e["feasible"]
        assert abs(e["objective"] - bv) < 1e-6
        assert abs(info["objective"] - bv) < 1e-6


def test_ilp_solution_is_feasible_on_medium_instance():
    inst = R.make_instance(20, 7, seed=1)
    a, info = R.ilp(inst, time_limit=30)
    assert a is not None and R.evaluate(inst, a)["feasible"]


def test_evaluate_detects_each_violation_type():
    inst = R.make_instance(4, 7, seed=0, avail_prob=1.0)
    a = np.full((4, 7), R.OFF)
    e = R.evaluate(inst, a)
    assert e["shortfall"] == int(inst["demand"].sum())  # nobody works
    a2 = a.copy(); a2[0, 0] = 2; a2[0, 1] = 0
    assert R.evaluate(inst, a2)["rest_violations"] == 1
    a3 = np.zeros((4, 7), int)  # worker 0 works 7 days
    assert R.evaluate(inst, a3)["weekly_violations"] == 4 * 2
    inst2 = dict(inst, avail=np.zeros((4, 7), bool))
    assert R.evaluate(inst2, a3)["availability_violations"] == 28


def test_incremental_state_matches_full_evaluation_after_random_moves():
    inst = R.make_instance(12, 14, seed=2)
    rng = np.random.default_rng(0)
    a = R.greedy(inst)
    st = R._State(inst, a)
    for _ in range(500):
        w, d, v = int(rng.integers(12)), int(rng.integers(14)), int(rng.integers(R.S + 1))
        st.set(w, d, v)
    e = R.evaluate(inst, st.a)
    assert abs(st.pref - e["pref"]) < 1e-9
    assert st.short == e["shortfall"] and st.weekx == e["weekly_violations"] and st.rest == e["rest_violations"]
    assert st.counts.max() - st.counts.min() == e["spread"]


def test_anneal_never_returns_infeasible_and_never_worse_than_its_start():
    inst = R.make_instance(20, 7, seed=3)
    start = R.greedy(inst)
    es = R.evaluate(inst, start)
    best, _ = R.anneal(inst, start, iters=20000, seed=0)
    if best is not None:
        e = R.evaluate(inst, best)
        assert e["feasible"]
        if es["feasible"]:
            assert e["objective"] <= es["objective"] + 1e-9


def test_ilp_objective_is_a_lower_bound_for_heuristics():
    inst = R.make_instance(20, 7, seed=4)
    a, info = R.ilp(inst, time_limit=30)
    assert info["proven_optimal"]
    g = R.evaluate(inst, R.greedy(inst))
    if g["feasible"]:
        assert g["objective"] >= info["objective"] - 1e-6
