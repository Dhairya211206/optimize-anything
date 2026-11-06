# Track F: Compiler Optimization

We built a small compiler for a tiny integer language: lexer, parser, three-address IR, a VM that counts executed instructions, six optimisation passes, and register allocation posed as an optimisation problem solved by heuristics and by an exact ILP.

Run: `python trackF_compiler/run_track_f.py` (about 5 s). Tests: `python -m pytest trackF_compiler -q` (21 pass).
Raw numbers: `results/results.json`. Figures: `results/passes.png`, `results/regalloc.png`.

**What is measured and what is assumed.** Instruction counts (static and dynamic) are exact for our VM. The "weighted cost" assumes `mul` costs 3 cycles and every other instruction 1; that is our assumption, not a hardware measurement, and the strength-reduction gain (mul → shift) exists only because of it. Compile times are milliseconds from a Python implementation. Nothing here was run on real hardware or compared with GCC/LLVM.

## 1. Design

- **Language:** 32-bit signed integers (wrap-around), `+ - *`, comparisons, `if/else`, `while`, `print`.
- **IR:** three-address code with labels and conditional jumps (`bin`, `neg`, `mov`, `print`, `label`, `jmp`, `jz`).
- **Passes**
  1. `const_fold`: constant propagation and folding inside basic blocks, constant-condition branches.
  2. `strength`: algebraic identities (x·1, x+0, x−x, x·0, x·−1) and multiplication by a power of two → shift.
  3. `copy_prop`: copy propagation inside blocks.
  4. `cse`: local common-subexpression elimination by value numbering (commutative operands normalised).
  5. `licm`: loop-invariant code motion. An instruction is hoisted only if its operands are not redefined in the loop, its target has one definition in the loop, and the target is not live at the loop header or at any loop exit (checked with global liveness). This avoids the two classic bugs: a value read before it is redefined in the loop, and overwriting a live-out value when the loop runs zero times.
  6. `dce`: liveness-based dead-code elimination, unreachable-block removal, jump clean-up.
  The driver repeats the pass list until the code stops changing (a fixed point, tested).
- **Correctness argument:** three-way differential testing (reference AST interpreter vs unoptimised IR on the VM vs optimised IR on the VM), see section 3.

## 2. Pass ablation on seven named programs

Weighted cost relative to unoptimised code (lower is better; 1.00 = no change). Dynamic instruction counts and static counts are in `results.json`.

| Program | Unopt. cost | All passes | Only const_fold | Only strength | Only cse | Only licm | Only dce | All minus licm |
|---|---|---|---|---|---|---|---|---|
| sumsq_invariant | 3807 | 0.58 | 0.89 | 0.89 | 1.00 | 0.58 | 1.00 | 0.68 |
| repeated_subexpr | 2606 | 0.39 | 1.00 | 0.85 | 0.92 | 0.47 | 1.00 | 0.65 |
| nested_loops | 13867 | 0.67 | 1.00 | 0.87 | 1.00 | 0.81 | 1.00 | 0.87 |
| fib_dead_code | 727 | 0.72 | 1.00 | 1.00 | 1.00 | 1.00 | 0.78 | 0.72 |
| constant_chain | 29 | 0.07 | 0.66 | 0.72 | 0.93 | 1.00 | 1.00 | 0.07 |
| branchy | 1180 | 0.64 | 1.00 | 0.80 | 1.00 | 1.00 | 0.75 | 0.64 |
| register_pressure | 1069 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

Geometric mean of the weighted-cost ratio over the seven programs: all passes 0.467; leaving out `licm` 0.535; leaving out `dce` 0.683; leaving out `const_fold` 0.604; leaving out `strength` 0.502; leaving out `cse` 0.467 (no change); leaving out `copy_prop` 0.472. Dynamic instruction count, geometric mean: 0.596 with all passes. Static instruction count: 0.644. Every configuration produced the correct output on every program.

What this says:
- **No single pass dominates.** Each program is helped by a different pass: LICM for loops with invariant work, DCE for dead code, strength reduction wherever there are multiplications by powers of two, const_fold for straight-line constants.
- **Passes enable each other.** `dce` alone changes little on some programs, but removing it from the full pipeline costs a lot (0.467 → 0.683), because other passes leave dead copies and temporaries behind that `dce` cleans up. By the same logic `copy_prop` alone changes nothing at all (ratio 1.00 everywhere), and its value only shows up combined.
- **CSE is weak here.** It helps `repeated_subexpr` alone (0.92) but adds nothing on top of the full pipeline (removing it changes nothing in geometric mean), because `strength`/`licm` already take care of the same redundancy in these programs. Our programs are small and artificial, so we cannot say CSE is unimportant in general.
- **The headline 0.467 is flattered by `constant_chain`**, which collapses from 19 instructions to 2. Excluding it, the typical reduction on the loop programs is 28% to 61% of weighted cost. `register_pressure` (every operation depends on the previous one, nothing is constant, redundant or dead) was not improved at all, which is the correct result.
- **Part of the gain comes from our cost model.** The mul → shift saving appears only because we set mul = 3. Dynamic instruction counts (which do not depend on that assumption) fall less than weighted cost: 0.596 vs 0.467 geometric mean.
- **Compile time:** the full pipeline takes 0.1 to 1.1 ms per program (the implementation is Python and the programs have under 40 instructions), so it is negligible here; we make no claim about large programs.

## 3. Validation by fuzzing

400 random terminating programs (nested loops, if/else, repeated subexpressions, multiplications by constants, 32-bit overflow). Each was run through the reference AST interpreter, the unoptimised IR, and the IR after each single pass and after the full pipeline.

- **Output mismatches: 0 of 400** for all seven configurations (also no program hit the step limit). The generator and the compiler were written by the same author, so a shared misunderstanding of the language rules could slip through both; the independent reference is the AST interpreter, which shares only `wrap32`/`apply_op` with the VM.
- Mean weighted cost relative to unoptimised (± std over programs): all passes 0.565 ± 0.226; LICM alone 0.908 ± 0.092; DCE alone 0.911 ± 0.110; const_fold alone 0.947 ± 0.061; strength alone 0.964 ± 0.033; CSE alone 0.993 ± 0.016; copy_prop alone 0.998 ± 0.006.
- Fuzzing found no miscompilation, but absence of failures is not a proof. Targeted unit tests also cover LICM hazards (operand changing in the loop, value read before definition, zero-iteration loop with a live-out value) and the CSE hazards (redefinition between occurrences, `x = x + 1`).

## 4. Register allocation as optimisation

**Model.** Each variable has a live interval over instruction indices (a conservative hull). A variable is either kept in one of K registers for its whole life or spilled to memory for its whole life (no live-range splitting). Every reference to a spilled variable costs one memory access. The kept intervals may never overlap more than K at once; interval graphs are perfect, so that is exactly the condition for a K-register assignment to exist, and every solution was turned into a real register assignment and checked.
**Objective.** Minimise the total spill weight, where a reference weighs either `10^(loop depth)` (static, what a compiler can know) or its measured execution count from a VM profile (profile-guided).
**Methods.** Linear scan (spill the furthest-ending interval); greedy by weight (highest weight first if it still fits); exact 0-1 ILP (maximise the weight of kept intervals subject to at most K overlapping at each start point), once with static weights and once with profile weights. The ILP was checked against exhaustive search on 15 random interval sets (optimal in all).

**Totals over the seven benchmarks, optimised code, K = 4 registers** (dynamic memory accesses caused by spills, measured from the VM profile; lower is better):

| Method | Dynamic spill accesses | Static weighted cost |
|---|---|---|
| Linear scan | 10069 | 1282 |
| Greedy by weight | 7807 | 1129 |
| ILP, static weights | 6698 | 902 |
| ILP, profile weights | 6698 | 902 |

So the exact solution cuts spill traffic by 33% relative to linear scan and 14% relative to greedy on these programs. On unoptimised code at K = 4: linear scan 10758, greedy 12199, ILP 7944 (static weights) and 7915 (profile weights).

**Per-program behaviour is not uniform.**
- `register_pressure` (26 variables, up to 11 live): linear scan is within 1% of ILP at K=2 (1318 vs 1316 accesses) and 5% at K=4 (1064 vs 1012); greedy-by-weight is much worse (2068 and 1764), because it keeps short, heavy variables first and then cannot fit the long-lived ones.
- `nested_loops`: the opposite. Greedy equals ILP for K ≥ 3, while linear scan is 22% worse than ILP at K=2 and up to 12 times worse at K=8 (1834 vs 154 accesses), because it ignores which variables sit in the inner loop.
- So neither heuristic dominates; ILP is never worse in static cost (tested on every benchmark at K = 2 and 4).

**Random programs (83 of 100 needed spilling at K = 4):** the static spill cost of linear scan was 41% ± 38% above the ILP optimum, and greedy-by-weight 62% ± 71% above (mean ± std across programs). Linear scan matched the ILP in 2 of 83 programs and greedy in 20 of 83.

**Static vs profile weights.** The two ILP variants gave nearly identical dynamic spill traffic (6698 vs 6698, and 7944 vs 7915 on unoptimised code). In these small programs the loop-depth estimate ranks variables almost the same as the real profile.

**Limits of the register-allocation result.** Programs have under 40 instructions, so the ILP solves instantly and we say nothing about its scaling; real compilers cannot afford exact solvers on large functions, and they split live ranges, coalesce copies and keep scratch registers, none of which we model. Only the relative ranking of methods under this simplified model is supported.

## 5. Summary of honest caveats
- Own toy language and VM; no comparison against production compilers, no hardware timing.
- Weighted cost depends on the assumed mul = 3.
- Seven hand-written benchmarks plus random programs; the benchmarks were chosen to exercise the passes, so they overstate typical gains.
- Passes are intra-block except `licm` and `dce`; there is no global constant propagation, so some opportunities are missed.
