# Track I: Quantum Algorithms and QML Advantage — Prompt Log

**Tool:** Claude (claude.ai), Claude Sonnet 5.5 | **Date:** 2026-11-04  
**Track Focus:** Quantum Circuit Simulation, Algorithmic Complexity Advantage (Grover vs Linear Search), and QML vs Classical Baselines

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert quantum algorithms researcher. Implement Track I (Quantum Algorithms and QML Advantage) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Quantum Algorithms Implementation:
   - Build pure state-vector circuits from scratch for the canonical quantum algorithms:
     * Deutsch-Jozsa (constant vs balanced oracle determination in 1 query).
     * Bernstein-Vazirani (recovering hidden n-bit string in 1 query).
     * Grover's Unstructured Search (O(sqrt(N)) amplitude amplification). Write the custom phase oracle and diffusion operator directly.
     * Quantum Fourier Transform (QFT) & Quantum Phase Estimation (QPE).
     * Shor's Order-Finding Algorithm (period finding via modular exponentiation).
   - Write custom circuit implementations for at least two algorithms directly (do not just call black-box libraries).

2. Algorithmic Advantage Benchmark (Grover vs Classical Linear Search):
   - Formulate search over an unsorted database of size N = 2^n for n in [3, 10].
   - Compare Quantum vs Classical metrics:
     * Query Complexity: O(sqrt(N)) quantum oracle calls vs O(N) classical evaluations.
     * Gate / Operation Count: Total elementary 1-qubit and 2-qubit gates vs classical branch comparisons.
     * Wall-Clock Runtime: Real execution time under state-vector simulation vs classical NumPy array scan.
   - Hardware Noise Impact: Model PennyLane depolarizing noise and shot sampling on Grover success probability.

3. Quantum Machine Learning (QML) vs Classical Baseline:
   - Problem: Binary classification on a non-linearly separable dataset (circles / spirals).
   - Quantum Models:
     * Model 1: Data Re-uploading Quantum Neural Network (QNN) with alternating rotation and entangling layers.
     * Model 2: Quantum Kernel Support Vector Machine (estimating quantum kernel matrix via state fidelity).
   - Classical Baselines:
     * Multi-Layer Perceptron (MLP) with matched parameter count.
     * Classical Support Vector Machine with tuned RBF kernel.
   - Comparison Criteria: Classification test accuracy, training wall-clock time, parameter count, and required circuit evaluations.

4. Verification & Testing:
   - Write pytest tests (`test_track_i.py`):
     * Verify Deutsch-Jozsa correctly classifies constant and balanced oracles with probability 1.0.
     * Verify Bernstein-Vazirani identifies hidden bitstrings of varying lengths with 100% fidelity.
     * Verify Grover search amplifies marked state probability to > 0.95 within floor(pi/4 * sqrt(N)) iterations.
     * Cross-validate custom quantum simulator against PennyLane state outputs.

5. Critical Review & Realistic Advantage Analysis:
   - Provide an honest, evidence-based assessment of quantum advantage:
     * Explain why simulation wall-clock time is exponentially slower than classical search despite O(sqrt(N)) query advantage.
     * Analyze data-loading bottleneck (input encoding overhead) in QML.
     * Contrast with Track D multi-core parallel speedups to show where quantum methods genuinely help vs where NISQ noise destroys advantage.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `qalgs.py` (custom DJ, BV, Grover, QFT, QPE, Shor), `qsim.py`, `qml_sim.py` (QNN, Quantum Kernel SVM), classical baseline models, 15 tests, `run_track_i.py`, and `TRACK_I_RESULTS.md`.
* **Revisions during session:**
  1. Quantum Kernel SVM was initially compared against an untuned RBF kernel; re-ran with a fair $C$ and $\gamma$ grid search on the classical RBF baseline to ensure an unbiased comparison (Failure Log #12).
  2. Fixed the Grover classical comparison to search for a fixed item rather than random stopping, ensuring exact deterministic query counts (Failure Log #13).
  3. Corrected a noise-crossover threshold statement in the draft text to match the measured values in `results.json`.

---

## Verification Note

* **15 pytest tests pass** (`python -m pytest trackI_quantum_qml -q`).
* Custom simulator matches PennyLane circuit states to $< 10^{-12}$.
* Grover quadratic query advantage demonstrated analytically; simulation wall-clock overhead clearly explained.
* Balanced report with zero false advantage claims, fully documented in `TRACK_I_RESULTS.md`.
