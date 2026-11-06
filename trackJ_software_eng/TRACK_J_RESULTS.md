# Track J: Software-Engineering Optimization, Results

Problem: **test-suite minimisation and prioritisation** for this repository's own Python code (Tracks A to F), formulated as weighted set cover and checked with mutation testing. The codebase under test is **5,159 lines of Python** (Tracks A to F, excluding results folders) with 76 tests that could be matched to both coverage and timing (77 exist; one has no matching record). No claim is made about other projects. Numbers come from `python trackJ_software_eng/run_track_j.py` (about 6 minutes) and are in `results/results.json`. Timings are from a shared 2-core machine.

## Formulation

- Universe `U`: the 1,531 source lines covered by at least one test, measured per test with coverage.py dynamic contexts.
- Variables: `x_t` = keep test t.
- Objective: minimise `sum_t cost_t x_t`, where `cost_t` is the measured run time (or 1 for minimum test count).
- Constraint: every line in `U` is covered by at least one kept test, `sum_{t covers l} x_t >= 1`.
- Methods: exact ILP (HiGHS), greedy by most new lines, greedy by new lines per second, plus baselines: original order until covered, fastest-first until covered, and 500 random orders until covered.
- Plus: prioritisation (order the tests so faults are found early), measured by APFD (average percentage of faults detected; 1 is best).

## Profile of the baseline

The full suite takes **12.2 s** of summed test time. The profile is extremely skewed:

| Test | Time | Share |
|---|---|---|
| `test_track_c.test_depolarizing_noise_limits` | 6.28 s | 51% |
| `test_track_f.test_fuzz_each_pass_and_pipeline_match_reference_interpreter` | 1.73 s | 14% |
| `test_track_c.test_fast_simulator_matches_pennylane` | 1.12 s | 9% |
| `test_track_c.test_deep_global_cost_gradient_variance_shrinks_with_qubits` | 0.63 s | 5% |
| `test_track_e.test_ilp_matches_brute_force_on_tiny_instances` | 0.45 s | 4% |

Four tests hold about 80% of the time, so the best saving comes from skipping a few slow tests, which a good minimiser should find.

## Whole-suite minimisation (100% line coverage kept)

| Method | Tests kept | Time | Line coverage |
|---|---|---|---|
| Full suite | 76 | 12.23 s | 100% |
| ILP, minimise run time (proven optimal) | 50 | 5.48 s | 100% |
| ILP, minimise test count | 42 | 5.48 s | 100% |
| Greedy, most new lines | 42 | 5.50 s | 100% |
| Greedy, new lines per second | 65 | 5.61 s | 100% |
| Fastest first until covered | 68 | 5.75 s | 100% |
| Original order until covered | 53 | 12.11 s | 100% |
| Random order until covered (500 draws) | 53.8 ± 3.1 | 7.00 ± 2.51 s | 100% |

**Gain:** 55% less summed test time (12.2 s to 5.5 s) at the same line coverage. Greedy comes within 0.5% of the ILP on time. Most of the gain is simply avoiding the 6.3 s noise test where other tests cover the same lines; the exact ILP adds little over a simple fastest-first rule (5.48 vs 5.75 s).

## Cost to correctness: fault detection lost (mutation study, Track F)

To check what minimisation costs, we wrote a mutation tester (`mutate.py`: AST mutants of arithmetic, comparison, boolean operators, `not`, and integer constants) and applied 90 sampled mutants to the Track F compiler modules (`frontend`, `opt`, `regalloc`, `vm`; 1,312 lines) with the 21 Track F tests.

- 90 mutants: 72 killed, 17 survived, 1 timed out (excluded). Mutation score of the full suite: 72 / 89 = **81%**. The 17 survivors are gaps in the existing tests (or equivalent mutants; we did not classify them by hand).
- Six tests are the *only* test killing some mutant, led by the fuzz test (4 mutants) and the ILP-vs-brute-force allocator test (3).

Fraction of those 72 killed mutants that each reduced suite still kills (line coverage restricted to the four mutated modules is 100% in every subset except the last):

| Reduced suite | Tests | Time | Mutants still killed |
|---|---|---|---|
| Full suite | 21 | 2.03 s | 100% |
| ILP, minimise run time | 14 | 1.84 s | 95.8% |
| Greedy, new lines per second | 15 | 1.86 s | 95.8% |
| Fastest first until covered | 17 | 1.88 s | 95.8% |
| Drop the slowest test only (line coverage 98.7%) | 20 | 0.29 s | 94.4% |
| Greedy, most new lines | 6 | 1.84 s | 93.1% |
| ILP, minimise test count | 6 | 1.84 s | 90.3% |
| 500 random subsets of 14 tests | 14 | | 93.2% ± 4.5% (line coverage 97.1% ± 3.2%) |

**Reading:** keeping 100% line coverage did lose fault detection: 4% (3 of 72 mutants) for the ILP-by-time subset and about 10% for the smallest, 6-test suite. A random subset of the same size loses about 7%, with a standard deviation of 4.5 points, so the ILP subset's advantage over random on fault detection is not clearly significant here (about 0.6 standard deviations). What coverage-based minimisation reliably guarantees is line coverage, not bug detection, and bug detection is what a team cares about.

Also, the Track F suite is already short (2 s total), so the realised saving is small: pytest wall-clock including start-up was 2.72 ± 0.09 s for the full suite vs 2.58 ± 0.10 s for the ILP subset (5%, about one standard deviation). Minimisation pays off where there are slow tests, as in the whole repository, not in this fast subsuite.

## Prioritisation (APFD on the same mutants)

| Order | APFD |
|---|---|
| Greedy, most new lines first | **0.892** |
| Random (500 orders) | 0.809 ± 0.047 |
| Greedy, new lines per second | 0.805 |
| Original order | 0.788 |
| Reverse order | 0.787 |
| ILP-minimal subset first | 0.783 |
| Fastest first | 0.687 |

Only the greedy "most new lines first" order beats random by a margin (about 1.7 standard deviations); fastest-first is clearly worse than random, since quick tests are often trivial parser tests that catch few faults. Time until every detectable mutant has been caught is about 2.0 s for all orders, which means that this measure cannot separate the orders here (we did not investigate which test detects the last mutant).

## Costs in maintainability and correctness

- A minimised suite must be recomputed whenever the code changes (coverage per test goes stale), and needs per-test coverage collection with its own overhead.
- Removed tests can still catch bugs that no current line-coverage requirement captures (up to 10% of mutants here). The safe way to use this is: run the minimal suite on every commit, the full suite nightly.
- The solver is trivial (50 variables), so it adds no practical cost; collecting the coverage data was the expensive step (about 40 s) and mutation testing the most expensive (280 s for 90 mutants).
- The mutation tester is our own simple one: it tests 5 operator classes, ignores equivalent-mutant detection and samples 90 mutants with a fixed seed, so scores carry sampling uncertainty (a binomial standard error of about 4 points on 89 mutants).

## Caveats

- One codebase (this repository), mostly numerical Python, one mutation seed, 90 mutants.
- Per-test line coverage and times are from single runs; times of about 0.02 s are noise.
- The mutation study covers Track F only (21 tests); the whole-suite coverage results cover all tracks.
- ILP is proven optimal for the stated model; the model (cover lines at minimum time) is not the same as "keep fault-finding power".

## Files

`setcover.py`, `mutate.py`, `collect.py`, `run_track_j.py`, `test_track_j.py` (6 tests), `results/` (results.json, minimisation.png, fault_detection.png, run outputs).
