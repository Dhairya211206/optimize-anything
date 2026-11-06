# Assignment 8: Prompt Logs & Vibe-Coding Register

This directory contains the prompt records for all 10 tracks (`trackA` through `trackJ`) of **Assignment 8: Optimize Anything (The 14-Day Vibe-Coding Challenge)**.

As required by **Section 8 (Mandatory Vibe-Coding Practice)** and **Section 9 (Submission Requirements)** of the course specification, all implementation and optimization work was directed via AI prompts following a rigorous, repeatable engineering methodology.

---

## 1. Generic Master Prompt Template (Section 8 Framework)

Every track in this project is driven by a generic, six-stage optimization prompt structured as follows:

```markdown
Role & Task:
You are an expert optimization engineer and algorithms researcher. We are completing Track [TRACK_NAME] of the 14-Day Vibe-Coding Challenge under the "Optimization Techniques" syllabus.

Please follow the mandatory 6-stage problem-solving methodology:

1. Problem Formulation:
   - Identify the real or simulated process to optimize.
   - Formulate decision variables, the objective function, hard/soft constraints, and mathematical assumptions.
   - Define quantitative success metrics (runtime, objective value, resource consumption, approximation ratio).

2. Algorithm Selection (Chapter 6 Syllabus):
   - Compare the candidate optimization algorithms suited for this problem.
   - Justify why the selected methods are appropriate and explicitly state why rejected methods are unsuitable.

3. Modular Implementation:
   - Implement the baseline and proposed optimization methods in clean, modular Python (or C for xv6).
   - Use deterministic seeds, type hints, proper input validation, and detailed comments explaining the optimization logic.

4. Independent Verification & Testing:
   - Write comprehensive pytest unit tests covering edge cases, micro-instances, and known analytical solutions.
   - Independently verify constraints and objective values to ensure results cannot be misleading.

5. Fair Benchmarking & Comparison:
   - Benchmark all algorithms on identical datasets, stopping criteria, and evaluation hardware.
   - Report wall-clock runtime, objective values, iterations, and memory/resource usage with clear units.

6. Critical Review & Trade-Off Analysis:
   - Skeptically analyze results: identify bottlenecks, trade-offs (e.g. speed vs accuracy), overheads, and failure modes.
   - Document any negative results or theoretical limits (e.g. Amdahl's law, barren plateaus, NISQ noise).
```

---

## 2. Track-by-Track Generic Prompts Index

| Track | Focus Domain | Core Optimization Formulation | Chapter 6 Algorithms Covered | Primary Metrics |
|---|---|---|---|---|
| [**Track A**](trackA/README.md) | Continuous Optimization | Convex & non-convex function landscapes, 2-layer MLP loss | GD, SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss-Newton, Backprop, Fisher/HVP | Loss, runtime, iterations to $10^{-6}$ tolerance, learning-rate sensitivity |
| [**Track B**](trackB/README.md) | Discrete Optimization & QUBO | 0/1 Knapsack, Max-Cut graph partitioning, Feature Selection | Greedy ratio, Dynamic Programming, Branch & Bound, ILP, QUBO/Ising, Simulated Annealing | Cut value, knapsack value, runtime, assignment validity |
| [**Track C**](trackC/README.md) | Quantum Optimization | Max-Cut QUBO on QAOA, Ground state energy on VQE | QAOA ($p \ge 1$), VQE, Parameter-shift rule, SPSA, Quantum Natural Gradient (QNG) | Energy expectation, gradient variance (barren plateaus), shot noise impact |
| [**Track D**](trackD/README.md) | Submodular, Parallel & Distributed | Maximum coverage / sensor placement, distributed learning | Submodular Greedy, Lazy Greedy, Amdahl/Gustafson parallel speedup, FedAvg, MGDA, GradNorm | $(1 - 1/e)$ approximation bound, parallel efficiency, communication rounds |
| [**Track E**](trackE/README.md) | Main Case Study | Hospital / Workforce Shift Rostering (Open Domain) | Strategy selection table, Greedy heuristic, Simulated Annealing, Exact ILP | Hard constraint violations, overtime penalty score, runtime across scales |
| [**Track F**](trackF/README.md) | Compiler Optimization | Mini-compiler bytecode IR passes & Register Allocation | Constant Folding/Prop, Dead Code Elimination, CSE, LICM, Graph-Coloring & ILP RegAlloc | Dynamic instruction count, execution cycles, binary size, compile time |
| [**Track G**](trackG/README.md) | xv6 Operating System | Kernel memory allocation & multi-core CPU scheduling | Per-CPU freelist allocator with batch stealing, Lottery scheduling with tickets | Throughput, lock contention, allocation latency, fairness proportionality |
| [**Track H**](trackH/README.md) | DBMS Optimization | Index selection under disk storage budget (TPC-H-like) | Greedy Cost-Benefit, Greedy Marginal Gain, Knapsack DP, Exact ILP | Query execution latency, EXPLAIN plan cost, index storage overhead |
| [**Track I**](trackI/README.md) | Quantum Algorithms & QML | Algorithmic speedup & classification advantage | Grover vs linear search, QNN data re-uploading, Quantum Kernel SVM vs classical RBF | Query count, gate count, wall-clock time, classification accuracy |
| [**Track J**](trackJ/README.md) | Software Engineering | Test-suite minimization & fault-detection prioritization | Weighted Set-Cover ILP, Greedy Set-Cover, Additional Coverage Prioritization (APFD) | Test-suite execution duration, reduction ratio, statement coverage, APFD |

---

## 3. Session & Tool Usage Summary

The implementation was developed through AI-assisted coding sessions using **Claude 3.5 Sonnet** (for full pipeline scaffolding and experiments) and **Gemini 3.8 Flash** via Google Antigravity (for the multi-tool comparison on Track B Max-Cut QUBO).

* **AI Tools Register**: See [`AI_TOOLS_REGISTER.md`](../AI_TOOLS_REGISTER.md) for full version details, dates, and track coverage.
* **Failure Log**: See [`FAILURE_LOG.md`](../FAILURE_LOG.md) for documented instances where AI suggestions were corrected.
* **Tool Comparison**: See [`TOOL_COMPARISON.md`](../TOOL_COMPARISON.md) for head-to-head benchmarking between Claude and Gemini.

### Chat Exports and Screenshots
- `claude_chat_export_partial.md`: Raw chat transcript excerpt covering the latter tracks.
- Per-track folders contain individual prompt logs, test verification records, and revision summaries.
