# Track C: Quantum Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude Sonnet 5.5 | **Date:** 2026-11-04  
**Track Focus:** Variational Quantum Algorithms (QAOA & VQE), Parameter-Shift Rules, SPSA, Quantum Natural Gradient, and Noise/Barren Plateaus

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert quantum computing and optimization researcher. Implement Track C (Quantum Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. Problem Formulation:
   - Formulate quantum optimization across two foundational paradigms:
     a) Combinatorial Max-Cut via QAOA: Map the Track B Max-Cut QUBO into an Ising Hamiltonian H_C = sum_{(i,j) in E} J_ij Z_i Z_j and driver H_M = sum_i X_i. Formulate the p-layer QAOA state |gamma, beta> and expectation value E(gamma, beta) = <H_C>.
     b) Ground-State Energy of a 4-Qubit Transverse-Field Ising Chain via VQE: Formulate Variational Quantum Eigensolver for a 4-qubit Ising chain Hamiltonian H = -sum_i Z_i Z_{i+1} - h sum_i X_i using Parameterized Quantum Circuits (PQCs) with Ry and CNOT entangling layers.

2. Algorithm Selection (Chapter 6 Syllabus):
   - Quantum Optimizers & Gradient Estimators:
     * Exact Analytical Gradients: Parameter-shift rule (per-gate shift df/dtheta = (f(theta + pi/2) - f(theta - pi/2)) / 2). Include a naive shared-parameter shift as an explicit negative control.
     * Simultaneous Perturbation Stochastic Approximation (SPSA): 2-measurement simultaneous perturbation gradient estimate for noisy/shot-based circuits.
     * Quantum Natural Gradient (QNG): Natural gradient descent using the Fubini-Study metric tensor / quantum Fisher information.
     * Classical Hybrid Optimizers: Adam and Gradient Descent applied to the quantum expectation landscape.

3. Simulation & Implementation:
   - Build a high-performance pure-NumPy state-vector quantum simulator for rapid execution, cross-validated against PennyLane.
   - Implement circuit noise models:
     * Depolarizing channel with error rate p in [0, 1].
     * Finite measurement shot noise (sampling from state-vector probability distributions with shots in [100, 10000]).
   - Barren Plateau Experiment: Measure gradient variance as a function of qubit count n in [2, 10] across randomly initialized deep ansatzes.

4. Verification & Testing:
   - Write pytest tests (`test_track_c.py`):
     * Verify fast NumPy state-vector simulator exactly matches PennyLane QAOA expectation values to within 1e-12.
     * Verify per-gate parameter-shift gradient matches numerical finite differences to within 1e-6.
     * Verify that under 100% depolarizing noise, circuit energy degenerates to uniform random state expectation.
     * Verify that SPSA gradient estimates asymptotically align with exact parameter shifts.

5. Fair Benchmarking & Critical Review:
   - Compare QAOA cut values against the classical Track B Simulated Annealing and ILP baselines.
   - Rigorously distinguish between mathematical state-vector simulation and physical quantum hardware execution.
   - Discuss practical quantum bottlenecks: measurement shot overhead, circuit depth limitations, and the onset of barren plateaus.
```

---

## Session Execution Summary

* **Scaffolding:** Developed `qaoa_sim.py`, `vqe.py`, `barren.py`, `test_track_c.py`, `run_track_c.py`, and `TRACK_C_RESULTS.md`.
* **Revisions during session:**
  1. PennyLane took ~3 ms per circuit evaluation, causing optimizer grid searches to drag. Built an exact vectorized NumPy state-vector simulator achieving 50x speedup; verified PennyLane agreement to $< 5 \times 10^{-15}$.
  2. Implemented the naive "shift-all-shared-parameters" rule alongside the rigorous per-gate parameter-shift rule as an educational negative control (demonstrating errors up to 7.7).
  3. Decoupled diagnostic metric logging from optimizer step tracking so SPSA was not unfairly penalized in circuit call counts.

---

## Verification Note

* **13 pytest tests pass** (`python -m pytest trackC_quantum -q`).
* Fast state-vector simulator matches PennyLane to machine precision ($< 10^{-14}$).
* Analytical per-gate parameter shift agrees with numerical finite differences to $\approx 10^{-8}$.
* Clear demonstration of barren plateaus: gradient variance decays exponentially with qubit count ($R^2 > 0.98$).
