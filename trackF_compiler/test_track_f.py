"""Correctness checks for Track F. Run: python -m pytest trackF_compiler -q"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frontend as fe  # noqa: E402
import opt  # noqa: E402
import regalloc as ra  # noqa: E402
import vm  # noqa: E402
from fuzz import random_program  # noqa: E402
from programs import PROGRAMS  # noqa: E402


def outputs(code):
    return vm.run(code)["out"]


# ------------------------------------------------------------------ front end
def test_parser_precedence_and_interpreter():
    ast = fe.parse("print 2 + 3 * 4; print (2 + 3) * 4; print -2 * 3; print 1 < 2; print 3 == 3; print 3 != 3;")
    assert fe.interpret(ast) == [14, 20, -6, 1, 1, 0]


def test_32bit_wraparound():
    assert fe.interpret(fe.parse("x = 2147483647; print x + 1;")) == [-2147483648]


def test_syntax_error_reported():
    for bad in ("x = ;", "print 1", "while (1) { x = 1;", "x = 1 $ 2;"):
        try:
            fe.parse(bad)
        except SyntaxError:
            continue
        raise AssertionError(bad)


def test_unoptimised_ir_matches_interpreter_on_benchmarks():
    for name, src in PROGRAMS.items():
        ast = fe.parse(src)
        assert outputs(fe.compile_ast(ast)) == fe.interpret(ast), name


# ------------------------------------------------------------------ individual passes
def test_const_fold_folds_and_removes_constant_branch():
    code = fe.compile_source("a = 2 + 3; if (1 < 2) { print a * 2; } else { print 0; }")
    out = opt.dce(opt.const_fold(code))
    assert vm.static_count(out) < vm.static_count(code)
    assert outputs(out) == [10]


def test_strength_reduction_replaces_mul_by_power_of_two():
    code = [("mov", "x", 5), ("bin", "mul", "y", "x", 8), ("bin", "mul", "z", 4, "x"), ("print", "y"), ("print", "z")]
    out = opt.strength(code)
    assert ("bin", "shl", "y", "x", 3) in out and ("bin", "shl", "z", "x", 2) in out
    assert outputs(out) == outputs(code) == [40, 20]


def test_algebraic_identities():
    code = [("mov", "x", 9), ("bin", "mul", "a", "x", 1), ("bin", "add", "b", "x", 0), ("bin", "sub", "c", "x", "x"),
            ("bin", "mul", "d", "x", 0), ("bin", "mul", "e", "x", -1), ("print", "a"), ("print", "b"), ("print", "c"),
            ("print", "d"), ("print", "e")]
    assert outputs(opt.strength(code)) == [9, 9, 0, 0, -9]


def test_cse_removes_duplicate_but_respects_redefinition():
    code = fe.compile_source("x = 3; y = 4; a = x * y; b = x * y; print a + b;")
    out = opt.dce(opt.copy_prop(opt.cse(code)))
    assert sum(1 for i in out if i[0] == "bin" and i[1] == "mul") < sum(1 for i in code if i[0] == "bin" and i[1] == "mul")
    code2 = fe.compile_source("x = 3; y = 4; a = x * y; x = 10; b = x * y; print a; print b;")
    assert outputs(opt.cse(code2)) == [12, 40]


def test_cse_does_not_record_self_referential_expression():
    code = fe.compile_source("x = 1; x = x + 1; y = x + 1; print x; print y;")
    assert outputs(opt.cse(code)) == [2, 3]


def test_dce_removes_dead_computation_keeps_prints():
    code = fe.compile_source("a = 1; b = a * 5; c = b + 2; print a;")
    out = opt.dce(code)
    assert vm.static_count(out) < vm.static_count(code) and outputs(out) == [1]


def test_licm_hoists_invariant_and_preserves_output():
    code = fe.compile_source("i = 0; k = 3; s = 0; while (i < 10) { c = k * 7 + 1; s = s + c; i = i + 1; } print s;")
    out = opt.licm(code)
    assert outputs(out) == outputs(code)
    assert vm.run(out)["dyn"] < vm.run(code)["dyn"]


def test_licm_does_not_hoist_when_operand_changes_in_loop():
    code = fe.compile_source("i = 0; k = 3; s = 0; while (i < 5) { c = k * 7; k = k + 1; s = s + c; i = i + 1; } print s;")
    assert outputs(opt.optimize(code, ["licm"])) == outputs(code)


def test_licm_zero_iteration_loop_does_not_change_live_out_value():
    # c is live after the loop; the loop body never runs, so c must keep its pre-loop value
    code = fe.compile_source("c = 99; k = 5; i = 10; while (i < 3) { c = k * 7; i = i + 1; } print c;")
    assert outputs(opt.optimize(code)) == [99]


def test_licm_does_not_hoist_value_read_before_definition_in_loop():
    code = fe.compile_source("t = 1; i = 0; while (i < 4) { print t; t = 5 * 3; i = i + 1; }")
    assert outputs(opt.optimize(code, ["licm"])) == outputs(code) == [1, 15, 15, 15]


# ------------------------------------------------------------------ whole pipeline: differential testing
def test_pipeline_preserves_output_on_benchmarks_and_improves_them():
    for name, src in PROGRAMS.items():
        code = fe.compile_source(src)
        o = opt.optimize(code)
        assert outputs(o) == outputs(code), name
        assert vm.run(o)["cost"] <= vm.run(code)["cost"], name


def test_fuzz_each_pass_and_pipeline_match_reference_interpreter():
    n_checked = 0
    for seed in range(250):
        ast = random_program(seed)
        try:
            ref = fe.interpret(ast)
        except RuntimeError:
            continue
        code = fe.compile_ast(ast)
        assert outputs(code) == ref, seed
        for name in opt.PASSES:
            assert outputs(opt.optimize(code, [name])) == ref, (name, seed)
        assert outputs(opt.optimize(code)) == ref, seed
        n_checked += 1
    assert n_checked > 200


def test_optimiser_reaches_fixed_point():
    code = fe.compile_source(PROGRAMS["nested_loops"])
    o = opt.optimize(code)
    assert opt.optimize(o) == o


# ------------------------------------------------------------------ register allocation
def _alloc_setup(name="register_pressure"):
    code = opt.optimize(fe.compile_source(PROGRAMS[name]))
    iv, refs = ra.intervals_and_refs(code)
    return code, iv, refs


def test_every_allocator_returns_a_valid_assignment():
    code, iv, refs = _alloc_setup()
    w = ra.weights(code, refs)
    for K in (2, 3, 4, 6):
        for spilled in (ra.linear_scan(iv, K), ra.greedy_weight(iv, w, K), ra.ilp_alloc(iv, w, K)[0]):
            kept = set(iv) - spilled
            assert ra.max_pressure(iv, kept) <= K
            regs = ra.assign_registers(iv, kept, K)
            for a in kept:
                for b in kept:
                    if a < b and not (iv[a][1] < iv[b][0] or iv[b][1] < iv[a][0]):
                        assert regs[a] != regs[b]


def test_ilp_allocation_is_optimal_against_brute_force_on_random_intervals():
    import itertools
    rng = np.random.default_rng(0)
    for _ in range(15):
        n, K = 9, 2
        iv = {}
        for i in range(n):
            s = int(rng.integers(0, 10))
            iv[f"v{i}"] = (s, s + int(rng.integers(0, 6)))
        w = {v: float(rng.integers(1, 20)) for v in iv}
        best = min(ra.spill_cost(set(iv) - set(keep), w)
                   for r in range(n + 1) for keep in itertools.combinations(sorted(iv), r)
                   if ra.max_pressure(iv, set(keep)) <= K)
        spilled, info = ra.ilp_alloc(iv, w, K)
        assert info["proven_optimal"] and abs(ra.spill_cost(spilled, w) - best) < 1e-9


def test_ilp_never_worse_than_heuristics_on_static_cost():
    for name in PROGRAMS:
        code, iv, refs = _alloc_setup(name)
        w = ra.weights(code, refs)
        for K in (2, 4):
            ilp_cost = ra.spill_cost(ra.ilp_alloc(iv, w, K)[0], w)
            assert ilp_cost <= ra.spill_cost(ra.linear_scan(iv, K), w) + 1e-9
            assert ilp_cost <= ra.spill_cost(ra.greedy_weight(iv, w, K), w) + 1e-9


def test_no_spills_when_enough_registers():
    code, iv, refs = _alloc_setup()
    assert ra.linear_scan(iv, len(iv)) == set()
