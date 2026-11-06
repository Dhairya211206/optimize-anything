# Track F: Compiler Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude Sonnet 5.5 | **Date:** 2026-11-04  
**Track Focus:** Intermediate Representation (IR), Multi-Pass Bytecode Transformations, Register Allocation via Linear Scan, Greedy, and Exact ILP

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert compiler engineer and optimization researcher. Implement Track F (Compiler Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Compiler Architecture & IR:
   - Build a complete mini-compiler for an imperative arithmetic and control-flow language:
     * Frontend: Tokenizer/Lexer and Recursive-Descent Parser producing Abstract Syntax Trees (AST).
     * Intermediate Representation: Stack/Register-based bytecode IR with basic blocks, control-flow edges, and virtual registers.
     * Runtime Virtual Machine (VM): Deterministic bytecode interpreter with instruction execution profiling.

2. Optimization Passes (Implement 6 Passes across Pipeline):
   - Pass 1: Constant Folding & Propagation (evaluate compile-time constants across basic blocks).
   - Pass 2: Algebraic Simplification & Strength Reduction (replace expensive ops like mul with adds/shifts).
   - Pass 3: Copy Propagation & Common Sub-expression Elimination (CSE).
   - Pass 4: Loop-Invariant Code Motion (LICM) (hoist invariant computations to loop pre-header with liveness safety).
   - Pass 5: Dead-Code Elimination (DCE) (prune unreachable blocks and dead assignments).

3. Compiler Decision Optimization Formulation (Register Allocation):
   - Formulate Register Allocation as a formal combinatorial optimization problem over variable live intervals:
     * Method 1: Linear Scan Register Allocator (standard fast compiler heuristic).
     * Method 2: Greedy Priority Allocator.
     * Method 3: Exact Integer Linear Programming (ILP) Allocator (minimizing memory spill load/store traffic via `scipy.optimize.milp`).
     * Finding: ILP allocator cuts memory spill traffic by 33% compared to linear scan on the benchmark suite.

4. Verification & Testing:
   - Write pytest tests (`test_track_f.py`):
     * Differential Fuzzing: Automatically generate random valid programs across diverse syntactic structures (loops, conditionals, expressions). Verify that optimized bytecode produces bitwise-identical output to the unoptimized AST reference interpreter.
     * Edge Cases: Verify LICM correctly preserves semantics when loops execute zero times.
     * Verify that ILP register allocation achieves optimal spill counts against exhaustive search on small interference graphs.

5. Fair Benchmarking & Critical Review:
   - Benchmark 7 canonical programs: Matrix Multiplication, Recursive Fibonacci, Nested Loops, Sieve of Eratosthenes, Polynomial Evaluation, etc.
   - Measure: Dynamic instruction count, execution cycles (with calibrated memory/op latency model), bytecode size (bytes), and compilation time (ms).
   - Trade-Off Analysis: Quantify compile-time overhead vs runtime performance gains.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `frontend.py`, `vm.py`, `opt.py`, `regalloc.py`, fuzzing engine, 7 benchmark suites, 21 tests, `run_track_f.py`, and `TRACK_F_RESULTS.md`.
* **Revisions during session:**
  1. Corrected an empirical claim in the results draft where static instruction reduction did not proportionally reduce dynamic memory accesses (Failure Log #10).
  2. Implemented LICM with strict dominance and liveness safety conditions to prevent hoisting instructions out of conditional bodies that might divide by zero.

---

## Verification Note

* **21 pytest tests pass** (`python -m pytest trackF_compiler -q`).
* Differential fuzzing across 400 random programs with 7 optimizer pass combinations revealed **zero semantic mismatches**.
* Exact ILP register allocator proven optimal against brute force.
* Instruction counts, compile times, and execution speedups reported in `TRACK_F_RESULTS.md`.
