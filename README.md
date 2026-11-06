# Optimize Anything: The 14-Day Vibe-Coding Challenge
### Assignment 8 — Optimization Techniques

**Student:** Dhairya Dabi  
**Course:** Optimization Techniques  
**Repository:** Public Submission & Comprehensive Technical Documentation  
**Development Methodology:** Mandatory AI-Assisted (Vibe) Coding with Strict Traceability  

---

## 📖 Executive Overview

This repository contains the complete experimental, analytical, and software implementations for **Assignment 8: Optimize Anything (The 14-Day Vibe-Coding Challenge)**. 

Rather than a conventional monolithic project, this work investigates how mathematical and algorithmic optimization techniques from **Chapter 6** can measurably improve real and simulated processes across diverse computing domains. The project spans **ten compulsory tracks (Tracks A through J)**, combining continuous loss surfaces, discrete combinatorial NP-hard problems, quantum circuit optimization, parallel and distributed scaling, operating systems, compilers, database engines, and software engineering pipelines.

All code, tests, and documentation adhere strictly to the **Section 8 Vibe-Coding Guidelines**: every component was driven by structured AI prompting, independently verified via automated test suites, checked against analytical edge cases, benchmarked under fair conditions, and documented with complete commit traceability.

---

## 🗂️ Complete Directory Structure

```text
optimize-anything/
├── README.md                           # Master project guide, track index & reproduction steps
├── CHECKLIST.md                        # Chapter 6 syllabus coverage mapping
├── AI_TOOLS_REGISTER.md                # Comprehensive audit register of all AI tools used
├── FAILURE_LOG.md                      # Post-mortem analysis of 14 AI-generated bugs & fixes
├── TOOL_COMPARISON.md                  # Head-to-head benchmark: Claude Sonnet 5.5 vs Gemini 3.8 Flash
├── requirements.txt                    # Python dependencies
├── maxcut_qubo.py                      # Standalone Max-Cut QUBO/Ising & Annealer with pytest suite
├── prompts/                            # Section 8 prompt logs for every track
│   ├── README.md                       # Master prompt log register & generic 6-stage template
│   ├── claude_chat_export_partial.md   # Raw chat transcript excerpt from Claude session
│   ├── trackA/ ... trackJ/             # Per-track prompts, AI responses, revisions, notes
│   └── trackB/antigravity_chat_export.md # Antigravity (Gemini) tool comparison chat export
├── report/
│   ├── TECHNICAL_REPORT.md             # Consolidated technical report & empirical findings
│   ├── FINAL_QUESTIONS.md              # Detailed answers to the 11 compulsory final questions
│   └── DEMO_SCRIPT.md                  # 10-minute live viva demonstration walkthrough
├── tool_comparison/                    # Code artifacts for the tool comparison benchmark
│   ├── claude/                         # Claude implementation & separate test file
│   └── antigravity/                    # Antigravity (Gemini) all-in-one implementation
├── trackA_continuous/                  # Track A: Continuous optimizers, backprop, landscapes
├── trackB_discrete/                    # Track B: Knapsack (DP/B&B/ILP), QUBO/Ising Max-Cut
├── trackC_quantum/                     # Track C: QAOA, VQE, SPSA, parameter-shift, barren plateaus
├── trackD_submodular_parallel/         # Track D: Submodular greedy, Amdahl's law, FedAvg, MGDA
├── trackE_case_study/                  # Track E: Main case study — Plant Shift Rostering
├── trackF_compiler/                    # Track F: Mini-compiler bytecode passes & ILP regalloc
├── trackG_xv6/                         # Track G: xv6 per-CPU allocator & Lottery CPU scheduler
├── trackH_dbms/                        # Track H: SQLite TPC-H workload physical index selection
├── trackI_quantum_qml/                 # Track I: Grover advantage, QNN, Quantum Kernel vs classical
└── trackJ_software_eng/                # Track J: Test-suite minimization (ILP) & APFD mutation testing
```

---

## 🚀 Environment Setup & Quickstart

### Prerequisites
* **Python 3.10+** (Tested on Python 3.13)
* Standard C toolchain / QEMU RISC-V (required only for Track G xv6 kernel compilation)

### Installation
```bash
# Clone the repository
git clone https://github.com/Dhairya211206/optimize-anything.git
cd optimize-anything

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.venv\Scripts\activate          # On Windows (PowerShell: .venv\Scripts\Activate.ps1)

# Install required dependencies
pip install -r requirements.txt
```

### Reproducing All Tests
You can run automated tests across all Python tracks directly from the repository root:

```bash
# Run complete test suite across Python tracks:
pytest -q --ignore=trackG_xv6
```

### Reproducing Individual Track Experiments & Tests
Each track is completely self-contained with its own execution runner and pytest test suite:

```bash
# Track A: Continuous Optimization
python trackA_continuous/run_track_a.py
python -m pytest trackA_continuous/test_optimizers.py -v

# Track B: Discrete Combinatorial & QUBO/Ising
python trackB_discrete/run_track_b.py
python -m pytest trackB_discrete/test_track_b.py -v

# Standalone Max-Cut QUBO Tool Comparison (Gemini implementation)
python maxcut_qubo.py
python -m pytest maxcut_qubo.py -v

# Track C: Quantum Optimization (QAOA, VQE, Barren Plateaus)
python trackC_quantum/run_track_c.py
python -m pytest trackC_quantum/test_track_c.py -v

# Track D: Submodular, Parallel Scaling & Distributed Learning
python trackD_submodular_parallel/run_track_d.py
python -m pytest trackD_submodular_parallel/test_track_d.py -v

# Track E: Main Case Study (Shift Rostering)
python trackE_case_study/run_track_e.py
python -m pytest trackE_case_study/test_track_e.py -v

# Track F: Compiler Optimization Passes & Register Allocation
python trackF_compiler/run_track_f.py
python -m pytest trackF_compiler/test_track_f.py -v

# Track G: xv6 Kernel Optimization (under QEMU)
cd trackG_xv6/xv6-riscv && make qemu

# Track H: DBMS Index Selection on SQLite
python trackH_dbms/run_track_h.py
python -m pytest trackH_dbms/test_track_h.py -v

# Track I: Quantum Algorithms & QML Advantage
python trackI_quantum_qml/run_track_i.py
python -m pytest trackI_quantum_qml/test_track_i.py -v

# Track J: Software Engineering Test-Suite Minimization & Mutation
python trackJ_software_eng/run_track_j.py
python -m pytest trackJ_software_eng/test_track_j.py -v
```

---

## 🔬 Compulsory Track Summary Matrix (Tracks A to J)

| Track | Domain | Problem Formulated | Chapter 6 Algorithms Evaluated | Key Empirical Finding | Evidence Label |
|:---:|:---|:---|:---|:---|:---:|
| **A** | **Continuous Optimization** | Quadratic, Rosenbrock saddle, 2-layer MLP loss | GD, SGD, Momentum, NAG, AdaGrad, RMSProp, Adam, Newton, Gauss-Newton, Backprop, Fisher/HVP | Momentum/NAG converge in 1,390 iterations on Rosenbrock where plain GD stalls; Newton takes 1 step on quadratics | *Measured* |
| **B** | **Discrete & QUBO** | 0/1 Knapsack, Max-Cut graph cut, Feature selection | Greedy ratio, Dynamic Programming, Branch & Bound, ILP (`scipy.optimize.milp`), QUBO/Ising, Annealing | DP and B&B achieve 100% exact optimum; greedy has an arbitrary optimality gap (2 vs 15 on correlated case); annealing achieves 100% optimum on 8-node Max-Cut | *Measured* |
| **C** | **Quantum Optimization** | Max-Cut on QAOA, 4-qubit transverse-field Ising chain on VQE | QAOA ($p \ge 1$), VQE, Parameter-Shift Rule, SPSA, Quantum Natural Gradient (QNG) | QAOA reaches 0.75 approximation ratio; gradient variance decays exponentially with qubits ($3\times$ per added qubit) confirming barren plateaus | *Simulated* |
| **D** | **Submodular & Parallel** | Sensor coverage, multi-core scaling, FedAvg, multi-task | Submodular Greedy, Lazy Greedy, Amdahl/Gustafson laws, FedAvg, MGDA, GradNorm | Greedy achieves 0.94 of optimum on facility location (beats $1-1/e$ bound); 1.66x speedup on 2 physical cores; GradNorm balances tasks whereas MGDA starves one | *Measured + Sim* |
| **E** | **Main Case Study** | Weekly manufacturing plant shift rostering ($w$ workers, $d$ days, $s$ shifts) | Constructive Greedy, Simulated Annealing, Exact ILP with linearized constraints | Exact ILP optimal in 0.04–0.73s across all 16 instances; greedy ends 24.5% to 26.8% above optimal cost; annealing is 6.7% to 26.8% above | *Measured (Synth)* |
| **F** | **Compiler Optimization** | Mini-compiler bytecode IR passes, register allocation | Constant folding/prop, DCE, CSE, LICM, Linear Scan, Greedy, and Exact ILP RegAlloc | Full pipeline achieves 0.467 cost ratio (53% cycle reduction); ILP cuts register spills by 33% vs linear scan; 0 semantic mismatches across 400 fuzz programs | *Measured* |
| **G** | **xv6 Operating System** | Kernel memory lock contention, CPU share fairness | Per-CPU freelist allocator with batch stealing, Proportional Lottery Scheduler | Lock contention eliminated ($\approx 500\text{k}$ failed acquisitions to 0); run time unchanged within noise because page zeroing outside lock dominates latency; lottery tracks tickets (69.6% for 70%) | *Measured (QEMU)* |
| **H** | **DBMS Optimization** | SQLite physical index selection under storage budget | Greedy Cost-Benefit, Greedy Marginal Gain, Knapsack DP, Exact ILP | Up to 1.55x speedup under 10 MB budget; naive ILP without interaction modeling degraded performance 2.6x, fixed with harm-aware modeling (1.47–1.55x) | *Measured (Synth)* |
| **I** | **Quantum Algorithms & QML** | Grover search vs linear scan, QNN & Quantum Kernel | DJ, BV, Grover, QFT, QPE, Shor, Data Re-uploading QNN, Quantum Kernel SVM vs classical MLP/RBF | Grover cuts oracle queries up to $652\times$ ($n=20$); simulation wall-clock time is slower than Python scan; QML shows no NISQ advantage over tuned RBF | *Simulated + Theory* |
| **J** | **Software Engineering** | Test-suite minimization & fault detection order | Weighted Set-Cover ILP, Greedy Set-Cover, Additional Coverage Prioritization (APFD) | 55% less summed test time at 100% line coverage; APFD 0.89 for best order (Greedy most-new-lines vs 0.81 random); minimal suites lost 4–10% of killed mutants | *Measured* |

---

## 🛠️ Mandatory Vibe-Coding Governance & Compliance

Under Sections 8 and 9 of the Assignment 8 guidelines, all AI assistance must be disclosed, verified, and audited:

### 1. AI Tools Register ([`AI_TOOLS_REGISTER.md`](AI_TOOLS_REGISTER.md))
Documents the primary AI models used (**Claude Sonnet 5.5** and **Gemini 3.8 Flash**), dates of usage, track coverage, and nature of work performed (planning, code generation, verification, and documentation).

### 2. Failure Log ([`FAILURE_LOG.md`](FAILURE_LOG.md))
Contains **14 detailed post-mortem case studies** where AI-generated code produced bugs, incorrect mathematical derivations, or unsafe assumptions. Each entry includes:
* The failing code and symptom.
* Root-cause diagnosis.
* The corrective prompt and fix.
* Generalizable software engineering lessons learned.

### 3. Tool Comparison Benchmark ([`TOOL_COMPARISON.md`](TOOL_COMPARISON.md))
A head-to-head evaluation on an identical mathematical task (**Max-Cut QUBO & Ising formulation with Simulated Annealing**):
* **Google Antigravity (Gemini 3.8 Flash):** Passed all 3 pytest tests on its **first run** (`3 passed in 1.65s`) with an exact derivation of $Q = A - \text{diag}(d) = -L$ and zero edits required.
* **Claude Sonnet 5.5:** First draft suffered an incremental energy calculation bug (`Q_kk * d^2` vs `Q_kk * d`), requiring one revision before passing all tests.

### 4. Commit Traceability Convention
All commits in this repository strictly adhere to the course tagging convention:
* `[AI:claude] ...` for code/documentation generated through Claude.
* `[AI:antigravity] ...` for code/documentation generated through Gemini / Google Antigravity.
* `[manual] ...` for manual edits, hyperparameter tuning, test design, and verification reviews by Dhairya Dabi.

---

## 🧪 Comprehensive Test & Verification Matrix

Over **100 automated unit tests** run across the repository to independently verify correctness:
* **Track A:** Analytical backprop gradients verified against finite differences to within $10^{-6}$; power iteration top eigenvalues match full Hessian to 8 digits.
* **Track B:** Exhaustive equivalence verified ($\text{DP} = \text{Branch-and-Bound} = \text{ILP} = \text{Brute Force}$) on random instances; $E_{\text{QUBO}}(x) = -\text{Cut}(x)$ and $E_{\text{Ising}}(s) = E_{\text{QUBO}}(x)$ for all 256 state assignments.
* **Track C:** Custom NumPy state-vector simulator agrees with PennyLane to $< 10^{-14}$; analytical per-gate parameter shifts match finite differences.
* **Track D:** Submodularity diminishing returns property mathematically verified on random subsets; Lazy Greedy matches standard Greedy with $4.4\times$ fewer evaluations.
* **Track E:** ILP matches exhaustive search on micro-instances; exact ILP proven optimal across all 16 instances.
* **Track F:** Differential fuzzing across 400 random programs and 7 optimizer configurations confirms **zero semantic divergence** from the unoptimized AST reference interpreter.
* **Track G:** xv6 kernel cleanly compiles and passes the comprehensive `usertests -q` suite under QEMU emulation.
* **Track H:** Invariant verified: all 12 analytical queries return bitwise-identical results across all indexed configurations.
* **Track I:** Circuit state vectors validated against analytical oracles; Grover amplifies marked state probability to $> 0.95$.
* **Track J:** Minimized test suite preserves 100.0% of statement coverage while cutting runtime by 55% (with 4–10% of killed mutants lost).

---

## ⚖️ Academic Integrity & Honest Reporting Declaration

In strict compliance with **Section 10 (Academic and Technical Expectations)**:
1. **Evidence-Based Claims:** No optimization speedup or quality gain is claimed unless backed by measured numbers logged in this repository.
2. **Clear Labeling:** All results are explicitly tagged as *measured* (on physical hardware), *simulated* (state-vector or mock cluster), or *theoretical*. No quantum speedups are claimed from classical simulator execution.
3. **Reproducible Stochastic Runs:** All stochastic algorithms (Simulated Annealing, SPSA, SGD, Lottery Scheduling) are evaluated across repeated fixed seeds, reporting mean $\pm$ standard deviation.
4. **Transparent Negative Results:** Negative and neutral findings are prominently reported and analyzed rather than concealed:
   * Track G Feature 1: Lock contention eliminated without wall-clock speedup because page zeroing (`memset`) is done outside the lock, which dominates allocation latency, combined with noisy QEMU timing.
   * Track I: Quantum Machine Learning shows zero advantage over classical ML on NISQ-scale data.
   * Track D: Model parallelism on small networks yields negative speedup due to inter-process communication overhead.

---

## 📚 Technical Report & Presentation Materials
* **Technical Report:** Full narrative, tables, and trade-off analyses in [`report/TECHNICAL_REPORT.md`](report/TECHNICAL_REPORT.md).
* **Final Questions:** Comprehensive answers to the 11 compulsory viva questions in [`report/FINAL_QUESTIONS.md`](report/FINAL_QUESTIONS.md).
* **Viva Demonstration Guide:** Step-by-step 10-minute live presentation outline in [`report/DEMO_SCRIPT.md`](report/DEMO_SCRIPT.md).
