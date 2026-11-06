"""Correctness checks for Track J. Run: python -m pytest trackJ_software_eng -q"""
import ast
import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mutate as mu  # noqa: E402
import setcover as sc  # noqa: E402


def random_cover(seed, n_tests=10, n_lines=30):
    rng = np.random.default_rng(seed)
    cover = {f"t{i}": set(int(x) for x in rng.choice(n_lines, rng.integers(3, 12), replace=False)) for i in range(n_tests)}
    covered = sc.universe(cover)
    cost = {t: float(rng.uniform(0.1, 3)) for t in cover}
    return cover, cost, covered


def brute_min_cost(cover, cost):
    tests, u = sorted(cover), sc.universe(cover)
    best = np.inf
    for r in range(len(tests) + 1):
        for s in itertools.combinations(tests, r):
            if sc.covered_fraction(list(s), cover) >= 1.0 - 1e-12 and sc.universe({t: cover[t] for t in s}) == u:
                best = min(best, sum(cost[t] for t in s))
    return best


def test_ilp_matches_brute_force_and_covers_everything():
    for seed in range(10):
        cover, cost, u = random_cover(seed)
        chosen, info = sc.ilp_min_cost(cover, cost)
        assert info["proven_optimal"]
        assert sc.universe({t: cover[t] for t in chosen}) == u
        assert abs(sum(cost[t] for t in chosen) - brute_min_cost(cover, cost)) < 1e-9


def test_heuristics_cover_everything_and_never_beat_the_ilp():
    for seed in range(10):
        cover, cost, u = random_cover(seed)
        opt = sum(cost[t] for t in sc.ilp_min_cost(cover, cost)[0])
        for chosen in (sc.greedy(cover, cost, "count"), sc.greedy(cover, cost, "ratio"), sc.until_covered(sorted(cover), cover)):
            assert sc.universe({t: cover[t] for t in chosen}) == u
            assert sum(cost[t] for t in chosen) >= opt - 1e-9


def test_greedy_can_be_strictly_worse_than_the_optimum():
    # classic set-cover counterexample: greedy takes the big overlapping set first
    cover = {"big": {1, 2, 3, 4}, "a": {1, 2, 5}, "b": {3, 4, 6}, "c": {5}, "d": {6}}
    cost = {t: 1.0 for t in cover}
    g = sc.greedy(cover, cost, "count")
    o, _ = sc.ilp_min_cost(cover, cost)
    assert len(g) >= len(o) and len(o) == 2


def test_apfd_extremes():
    kills = {"f1": {"a"}, "f2": {"a"}}
    assert sc.apfd(["a", "b", "c"], kills) > sc.apfd(["c", "b", "a"], kills)
    assert abs(sc.apfd(["a", "b"], kills) - (1 - 2 / 4 + 1 / 4)) < 1e-12


def test_mutants_are_valid_python_and_differ_from_the_original():
    src = open(os.path.join(HERE, "setcover.py")).read()
    n = mu.count_sites_visit_order(ast.parse(src))
    assert n > 20
    norm = ast.unparse(ast.parse(src))
    changed = 0
    for k in range(0, n, 7):
        m = mu.mutate_source(src, k)
        compile(m, "m", "exec")
        changed += m != norm
    assert changed >= (n // 7) * 0.9


def test_mutation_kills_a_fragile_function(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "lib.py").write_text("def f(a, b):\n    if a < b:\n        return a + b\n    return a - b\n")
    (pkg / "test_lib.py").write_text(
        "import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\nfrom lib import f\n\n"
        "def test_less():\n    assert f(1, 2) == 3\n\ndef test_greater():\n    assert f(5, 2) == 3\n\ndef test_equal_is_untested_boundary():\n    assert True\n")
    res = mu.kill_matrix(str(pkg), ["lib.py"], 20, seed=0, log=lambda *a: None)
    assert res and any(r["status"] == "killed" for r in res)
    assert any("test_less" in r["killed_by"] or "test_greater" in r["killed_by"] for r in res)
