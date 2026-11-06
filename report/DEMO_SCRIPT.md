# Live Demonstration & Viva Presentation Script (5 to 10 Minutes)

**Student:** Dhairya Dabi  
**Course:** Optimization Techniques — Assignment 8 (14-Day Vibe-Coding Challenge)  
**Goal:** Demonstrate the optimization problem, mathematical methods, measurable evidence of improvement, and key engineering lessons.

Every command below is executed directly from the repository root.

| Time | Slide / Screen | Key Talking Point & Defense | Command or Reference File |
|---|---|---|---|
| 0:00 | Repo README, Track Matrix | Ten compulsory tracks implemented; every number explicitly labelled as *measured*, *simulated*, or *theoretical*. | `README.md`, `CHECKLIST.md` |
| 0:45 | Track E: Shift Rostering Baseline | Problem formulation with binary tensor $x_{e,d,s}$; greedy baseline is 24.5% to 26.8% above proven optimum. | `trackE_case_study/TRACK_E_RESULTS.md`, `python trackE_case_study/run_track_e.py` |
| 1:45 | Exact ILP vs Heuristics | Exact ILP finds the global optimum in < 1s; simulated annealing reaches near-optima with sufficient budget. | `trackE_case_study/results/roster_comparison.png` |
| 2:45 | Compiler Passes & Register Allocation | 4 optimization passes achieve 0.467 cost ratio (53% cycle cut); ILP regalloc eliminates 33% of spill traffic. | `trackF_compiler/TRACK_F_RESULTS.md` |
| 3:45 | xv6 OS Kernel Benchmarks | Per-CPU allocator eliminated lock contention ($\approx 500\text{k}$ failed acquisitions to 0); lottery scheduler enforces ticket proportionality. | `trackG_xv6/TRACK_G_RESULTS.md`, `xv6_changes.patch` |
| 4:45 | DBMS Index Selection (Model vs Reality) | Exact ILP without interaction was 2.6x slower; harm-aware formulation recovers 1.55x physical speedup. | `trackH_dbms/results/index_selection.png` |
| 5:45 | Quantum Advantage & QML Reality | Grover reduces queries by $652\times$ ($n=20$); simulation wall-clock is slower; QML shows no NISQ advantage over tuned RBF. | `trackI_quantum_qml/results/grover.png`, `qml.png` |
| 6:45 | Software Engineering Test Minimization | Weighted Set-Cover ILP cuts test execution time by 55% at 100% statement coverage (losing 4–10% killed mutants); APFD prioritization hits 0.89. | `trackJ_software_eng/results/fault_detection.png` |
| 7:45 | Comprehensive Pytest Suite | Over 100 automated unit tests pass across all tracks; 14 AI-generated failure logs documented. | `pytest -q --ignore=trackG_xv6`, `FAILURE_LOG.md` |
| 8:45 | Concluding Engineering Lessons | Optimization without physical validation can degrade real performance; honest negative results carry full scientific weight. | `report/TECHNICAL_REPORT.md` |

**Pre-demo Tip:** Run `pytest -q --ignore=trackG_xv6` once prior to the presentation to ensure warm Python caching.
