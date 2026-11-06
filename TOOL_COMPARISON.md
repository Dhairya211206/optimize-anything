# AI Tool Comparison

Task: **Max-Cut as a QUBO and Ising model, solved by brute force and simulated annealing** (Track B formulation), same prompt given to both tools (prompt below). Files: `tool_comparison/claude/` (code + a separate `test_maxcut_qubo.py`) and `tool_comparison/antigravity/maxcut_qubo.py` (code and tests in one file). Antigravity's time, prompt count and first-run result come from its own execution log as relayed by Dhairya; Claude's speed figure excludes model generation time, so the two speed cells are not directly comparable.

## Prompt (identical for both tools)

> Write a Python 3 file maxcut_qubo.py (numpy only) that: builds a random undirected graph with 8 nodes and 18 edges using a fixed seed of 7; formulates Max-Cut as a QUBO (minimise x^T Q x, x_i in {0,1}); converts it to Ising form returning J, h and the offset; solves by brute force over all 2^8 assignments; solves by simulated annealing (fixed seed, 50 runs) and reports how many reach the brute-force optimum; and writes pytest tests checking (a) QUBO energy equals minus the cut value for every one of the 256 assignments, (b) Ising energy equals QUBO energy for every assignment, (c) the annealer never returns an invalid 0/1 vector. Run the tests and show the output. Only numpy and pytest. Explain formulas in comments. If any test fails, fix the code and say what was wrong.

## Comparison

| Criterion | Tool 1: Claude (Claude Sonnet 5.5) | Tool 2: Antigravity (Gemini 3.8 Flash, medium) |
|---|---|---|
| Task | as above | as above |
| Correct on first try? | **No.** My own 4th test caught a bug on the first run (3 of 4 tests passed): the annealer's incremental energy update used `Q_kk * d^2` instead of `Q_kk * d`, so the reported energy drifted (−6122 vs −8) and annealing reached the optimum in only 8/50 runs. Fixed in one edit; then 4/4 pass and 50/50 runs reach the optimum. | **Yes**, per Antigravity's execution log (as relayed by Dhairya): 3 of 3 tests passed on its first run with no edits. I also re-ran the file independently and 3 of 3 pass. |
| Hallucinations (made-up APIs, wrong facts) | None found: numpy and pytest only. The bug above was a derivation slip in a comment-and-code pair, not an invented API. | None found when I read the code: numpy and pytest only; one harmless hard-coded default `target_cut=13` that is overridden by the brute-force value. |
| Correctness of the maths | Q = A − diag(d); Ising J_ij = Q_ij/2 (upper triangle), h = 0, offset = −9.0 | Same Q; J_ij = Q_ij/2 (symmetric matrix); h = 0, offset = −9.0 |
| Results on its own graph | best cut 13 (8 optimal assignments); annealing 50/50 | best cut 13 (8 optimal assignments); annealing 50/50 |
| Speed (wall-clock to working result) | Tool-run time from first writing the file to all tests green was about 8 s (two test runs, one edit). Model generation time was not measured. | 5 min 54 s from the request (12:52:37) to passing tests (12:58:31), per its execution log; pytest itself took 1.65 s there. |
| Prompt iterations needed | 0 extra prompts from the user; 1 self-correction after a failing test | 0 follow-up prompts needed to get working code (one "all done?" check-in message was sent, which did not change the code) |
| Tests | 4 (adds a graph-shape check and a check that the annealer's reported energy matches its returned vector, which is what exposed the bug) | 3, exactly the three asked for; (c) checks shape, values and dtype over 50 seeds |
| Notes | Code is split into a module and a test file. Annealing uses incremental energy updates (faster, but that is where the bug came from). | One file with a long derivation docstring and a demo `main()` that also runs pytest. Recomputes the full energy for every proposed flip (simpler, slower, no bug). |

## What this does and does not show

- Both tools produced a correct formulation on the same task; the same graph came out for both (13 is the optimum for this seed-7 graph in both implementations, 8 optimal assignments each; it is a different graph from the Track B graph whose optimum is 14).
- The difference worth reporting is how the tools failed or did not: Claude's first draft had an annealing bug that an extra consistency test caught; Antigravity's file had none in the version I checked.
- One task and one run per tool is a small sample. It says nothing general about either tool.
