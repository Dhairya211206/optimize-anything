"""Correctness checks for Track H. Run: python -m pytest trackH_dbms -q"""
import itertools
import os
import sqlite3
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dbutil as du  # noqa: E402
import selection as sel  # noqa: E402
import tpch_like  # noqa: E402
from workload import CANDIDATES, QUERIES  # noqa: E402


def small_db(tmp_path):
    p = str(tmp_path / "t.db")
    counts = tpch_like.build(p, sf=0.004, seed=1)
    return sqlite3.connect(p), counts


def test_dataset_row_counts_and_keys(tmp_path):
    con, c = small_db(tmp_path)
    assert c["customer"] == 600 and c["orders"] == 6000 and c["part"] == 800 and c["nation"] == 25
    assert 6000 <= c["lineitem"] <= 6000 * 7
    assert con.execute("SELECT COUNT(*) FROM orders WHERE o_custkey NOT IN (SELECT c_custkey FROM customer)").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM lineitem WHERE l_orderkey NOT IN (SELECT o_orderkey FROM orders)").fetchone()[0] == 0


def test_query_results_identical_with_and_without_indexes(tmp_path):
    con, _ = small_db(tmp_path)
    base = {q: du.result_hash(du.run_query(con, sql)[0]) for q, (sql, _) in QUERIES.items()}
    assert all(not du.run_query(con, sql)[2] for sql, _ in QUERIES.values())
    rng = np.random.default_rng(0)
    names = list(CANDIDATES)
    for _ in range(3):
        chosen = list(rng.choice(names, size=8, replace=False))
        du.create_indexes(con, chosen, CANDIDATES)
        for q, (sql, _) in QUERIES.items():
            assert du.result_hash(du.run_query(con, sql)[0]) == base[q], (q, chosen)
        du.drop_indexes(con, chosen)


def test_an_index_changes_the_plan(tmp_path):
    con, _ = small_db(tmp_path)
    sql = QUERIES["P1_customer_orders"][0]
    before = du.plan(con, sql)
    du.create_indexes(con, ["o_custkey"], CANDIDATES)
    after = du.plan(con, sql)
    assert before != after and any("ix_o_custkey" in line for line in after)


def test_index_size_is_reported(tmp_path):
    con, _ = small_db(tmp_path)
    du.create_indexes(con, ["li_shipdate"], CANDIDATES)
    assert du.index_size_bytes(con, "ix_li_shipdate") > 0


def _random_instance(seed, nq=5, ni=8):
    rng = np.random.default_rng(seed)
    B = rng.uniform(0, 10, (nq, ni)) * (rng.uniform(size=(nq, ni)) < 0.5)
    w = rng.integers(1, 5, nq).astype(float)
    sizes = rng.uniform(1, 5, ni)
    return B, w, sizes


def test_ilp_equals_brute_force_on_random_instances():
    for seed in range(12):
        B, w, sizes = _random_instance(seed)
        budget = sizes.sum() * 0.4
        chosen, info = sel.ilp(B, w, sizes, budget)
        _, best = sel.brute_force(B, w, sizes, budget)
        assert info["proven_optimal"] and sizes[chosen].sum() <= budget + 1e-9
        assert abs(sel.model_benefit(B, w, chosen) - best) < 1e-6
        assert abs(info["predicted"] - best) < 1e-6


def test_heuristics_respect_budget_and_never_beat_the_ilp():
    for seed in range(12):
        B, w, sizes = _random_instance(seed)
        budget = sizes.sum() * 0.35
        _, best = sel.brute_force(B, w, sizes, budget)
        for chosen in (sel.greedy_ratio(B, w, sizes, budget), sel.greedy_marginal(B, w, sizes, budget),
                       sel.knapsack_dp(B, w, sizes, budget, 0.05)):
            assert sizes[chosen].sum() <= budget + 1e-9
            assert sel.model_benefit(B, w, chosen) <= best + 1e-9


def test_knapsack_dp_is_optimal_for_the_additive_objective():
    for seed in range(8):
        B, w, sizes = _random_instance(seed, ni=9)
        sizes = np.round(sizes, 1)
        budget = float(np.round(sizes.sum() * 0.4, 1))
        ben = sel.additive_benefit(B, w)
        best = max(sum(ben[i] for i in s) for r in range(10) for s in itertools.combinations(range(9), r) if sizes[list(s)].sum() <= budget + 1e-9)
        got = sel.knapsack_dp(B, w, sizes, budget, 0.1)
        assert abs(sum(ben[i] for i in got) - best) < 1e-6


def test_additive_model_overcounts_when_two_indexes_help_the_same_query():
    B = np.array([[10.0, 9.0]])
    w = np.array([1.0])
    assert sel.additive_benefit(B, w).sum() == 19.0 and sel.model_benefit(B, w, [0, 1]) == 10.0
