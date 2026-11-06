# Demo Script (about 5 minutes)

Goal from the assignment: show the problem, the method, evidence of improvement, and key lessons. Record your screen while you run these; say it in your own words. Every command is from the repository root.

| Time | Show | Say (key point) | Command or file |
|---|---|---|---|
| 0:00 | Repo README, track table | Ten tracks; every result is labelled measured, simulated, or theoretical. | `README.md` |
| 0:30 | Track E problem and baseline | Shift rostering; greedy is about 25% above the proven optimum. | `trackE_case_study/TRACK_E_RESULTS.md` section 3; optional `python trackE_case_study/run_track_e.py` |
| 1:15 | Exact ILP vs heuristics plot | ILP optimal in under 1 s up to 150 × 28; annealing needs tuning. | `trackE_case_study/results/roster_comparison.png` |
| 1:45 | Compiler ablation | Passes enable each other; headline 0.467 depends on the assumed mul cost. | `trackF_compiler/TRACK_F_RESULTS.md` section 2 |
| 2:15 | xv6 boot and usertests | Two kernel changes; contention to 0, but no run-time gain; lottery follows tickets. | `trackG_xv6/TRACK_G_RESULTS.md`; optionally boot a prebuilt kernel with `bash trackG_xv6/build.sh` |
| 3:00 | DBMS EXPLAIN plans and speedup plot | Exact ILP was optimal for the model and 2.6x slower in reality. | `trackH_dbms/results/index_selection.png` |
| 3:30 | Quantum: Grover and QML plots | 652x fewer queries in the model, slower simulation, no QML advantage. | `trackI_quantum_qml/results/grover.png`, `qml.png` |
| 4:00 | Test minimisation | 55% less test time, 4–10% fewer mutants killed. | `trackJ_software_eng/results/fault_detection.png` |
| 4:30 | Tests and failure log | 106 tests pass; 14 AI errors logged and fixed. | `python -m pytest -q --ignore=trackG_xv6`; `FAILURE_LOG.md` |
| 5:00 | Key lessons | An exactly optimal solution of a wrong model can lose; negative results are results; label simulation honestly. | |

Tip: run the pytest command once beforehand (about 20 s) so the demo does not wait.
