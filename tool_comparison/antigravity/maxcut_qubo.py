"""
Max-Cut QUBO and Ising Formulation with Simulated Annealing
Implemented using NumPy and Pytest only.

Problem Description & Formulas:
--------------------------------
1. Max-Cut as a Graph Problem:
   Given an undirected graph G = (V, E) with n nodes and m edges.
   Let A be the symmetric adjacency matrix:
       A_ij = 1 if (i, j) in E, else 0  (with A_ii = 0).
   The degree of node i is d_i = sum_j A_ij.
   The degree matrix is D = diag(d_1, ..., d_n).
   The graph Laplacian matrix is L = D - A.

   For a partition vector x in {0, 1}^n where:
       x_i = 1 if node i is in partition S
       x_i = 0 if node i is in partition V \\ S
   An edge (i, j) is cut if and only if x_i != x_j.
   Since x_i in {0, 1}, we have:
       (x_i - x_j)^2 = x_i + x_j - 2 * x_i * x_j = 1 if cut, else 0.

   The total cut value Cut(x) is:
       Cut(x) = sum_{(i, j) in E} (x_i - x_j)^2
              = 0.5 * sum_{i, j} A_ij (x_i + x_j - 2 * x_i * x_j)
              = sum_i d_i x_i - sum_{i, j} A_ij x_i x_j.
   Because x_i in {0, 1}, x_i^2 = x_i, so sum_i d_i x_i = x^T D x.
   Therefore:
       Cut(x) = x^T D x - x^T A x = x^T (D - A) x = x^T L x.

2. QUBO Formulation:
   Max-Cut seeks to MAXIMIZE Cut(x).
   In QUBO (Quadratic Unconstrained Binary Optimization), we MINIMIZE:
       E_QUBO(x) = x^T Q x,  with x_i in {0, 1}.
   Setting E_QUBO(x) = -Cut(x):
       x^T Q x = - x^T (D - A) x = x^T (A - D) x.
   Hence, the symmetric QUBO matrix Q is:
       Q = A - D = -L.
   Explicitly:
       Q_ii = -d_i
       Q_ij = A_ij  (for i != j).

3. Conversion from QUBO to Ising Form:
   Ising spins s_i in {-1, +1} are mapped to binary variables x_i in {0, 1} via:
       x_i = (s_i + 1) / 2
   (so s_i = -1 maps to x_i = 0, and s_i = +1 maps to x_i = 1).

   Substitute x_i into the QUBO objective x^T Q x:
       x_i * x_j = [(s_i + 1) * (s_j + 1)] / 4
                 = (s_i * s_j + s_i + s_j + 1) / 4.
       x_i = (s_i + 1) / 2 = (2 * s_i + 2) / 4.

   Expanding x^T Q x = sum_i Q_ii x_i + sum_{i < j} (Q_ij + Q_ji) x_i x_j:
   Since Q is symmetric (Q_ij = Q_ji):
       x^T Q x = sum_{i < j} 2 * Q_ij * [(s_i * s_j + s_i + s_j + 1) / 4]
                 + sum_i Q_ii * [(s_i + 1) / 2]
               = sum_{i < j} (Q_ij / 2) * s_i * s_j
                 + sum_i [ Q_ii / 2 + sum_{j != i} (Q_ij / 2) ] * s_i
                 + [ sum_i (Q_ii / 2) + sum_{i < j} (Q_ij / 2) ].

   This matches the standard Ising Hamiltonian:
       E_Ising(s) = sum_{i < j} J_ij * s_i * s_j + sum_i h_i * s_i + offset
                  = 0.5 * s^T J s + h^T s + offset
   where:
       J_ij = Q_ij / 2 for i != j, and J_ii = 0 (symmetric coupling)
       h_i  = 0.5 * sum_j Q_ij (linear magnetic bias)
       offset = 0.25 * sum_i Q_ii + 0.25 * sum_{i, j} Q_ij (constant energy offset).

   For Max-Cut specifically:
       - Row sums sum_j Q_ij = sum_j A_ij - d_i = d_i - d_i = 0, so h_i = 0 for all i
         (reflecting the global spin-flip symmetry s -> -s of Max-Cut).
       - offset = 0.25 * sum_i (-d_i) + 0 = -0.25 * (2 * |E|) = - |E| / 2 = -9.0.
       - J_ij = 0.5 if (i, j) in E, else 0.
"""

import numpy as np
import pytest


# ============================================================================
# 1. Graph Generation
# ============================================================================

def build_graph(num_nodes=8, num_edges=18, seed=7):
    """
    Build a random undirected simple graph with num_nodes and num_edges
    using a fixed random seed.

    Parameters:
        num_nodes (int): Number of nodes (default: 8).
        num_edges (int): Number of undirected edges (default: 18).
        seed (int): Random seed for reproducibility (default: 7).

    Returns:
        adj (np.ndarray): Symmetric (num_nodes, num_nodes) adjacency matrix.
    """
    rng = np.random.default_rng(seed)
    # Generate all possible undirected node pairs (u < v)
    all_pairs = [
        (u, v) for u in range(num_nodes) for v in range(u + 1, num_nodes)
    ]
    if num_edges > len(all_pairs):
        raise ValueError(
            f"Cannot select {num_edges} edges from {len(all_pairs)} possible pairs."
        )

    # Sample num_edges distinct pairs without replacement
    chosen_indices = rng.choice(len(all_pairs), size=num_edges, replace=False)

    adj = np.zeros((num_nodes, num_nodes), dtype=int)
    for idx in chosen_indices:
        u, v = all_pairs[idx]
        adj[u, v] = 1
        adj[v, u] = 1

    return adj


# ============================================================================
# 2. Max-Cut to QUBO Formulation
# ============================================================================

def maxcut_to_qubo(adj_matrix):
    """
    Formulate Max-Cut as a QUBO problem: minimise x^T Q x with x_i in {0, 1}.

    Mathematical derivation:
        Cut(x) = x^T (D - A) x = x^T L x
        Minimising -Cut(x) is equivalent to minimising x^T (A - D) x.
        Therefore, Q = A - D = -L.

    Parameters:
        adj_matrix (np.ndarray): Symmetric (n, n) adjacency matrix.

    Returns:
        Q (np.ndarray): Symmetric (n, n) QUBO matrix.
    """
    degrees = adj_matrix.sum(axis=1)
    degree_matrix = np.diag(degrees)
    # Q = A - D
    Q = adj_matrix.astype(float) - degree_matrix.astype(float)
    return Q


def qubo_energy(x, Q):
    """
    Compute QUBO energy E(x) = x^T Q x for a binary vector x in {0, 1}^n.
    """
    x_vec = np.asarray(x, dtype=float)
    return float(x_vec @ Q @ x_vec)


def cut_value(x, adj_matrix):
    """
    Compute the cut value for assignment x in {0, 1}^n on the given graph:
    Cut(x) = number of edges (u, v) with x[u] != x[v].
    """
    x_vec = np.asarray(x, dtype=int)
    n = len(x_vec)
    u_idx, v_idx = np.triu_indices(n, k=1)
    edge_mask = adj_matrix[u_idx, v_idx] == 1
    cut = int(np.sum(x_vec[u_idx[edge_mask]] != x_vec[v_idx[edge_mask]]))
    return cut


# ============================================================================
# 3. QUBO to Ising Conversion
# ============================================================================

def qubo_to_ising(Q):
    """
    Convert a QUBO matrix Q to Ising Hamiltonian parameters (J, h, offset)
    such that for s_i in {-1, +1} and x_i = (s_i + 1) / 2:
        E_QUBO(x) = E_Ising(s) = sum_{i < j} J_ij * s_i * s_j + sum_i h_i * s_i + offset
                               = 0.5 * s^T J s + h^T s + offset

    Formulas:
        Q_sym = (Q + Q^T) / 2
        J_ij = 0.5 * Q_sym_ij (for i != j), with J_ii = 0
        h_i = 0.5 * sum_j Q_sym_ij
        offset = 0.25 * (sum_{i,j} Q_sym_ij + trace(Q_sym))

    Parameters:
        Q (np.ndarray): (n, n) QUBO matrix.

    Returns:
        J (np.ndarray): Symmetric (n, n) coupling matrix with zero diagonal.
        h (np.ndarray): (n,) linear bias vector.
        offset (float): Constant energy offset.
    """
    Q_sym = 0.5 * (Q + Q.T)
    n = Q_sym.shape[0]

    # Coupling matrix J: symmetric with zero diagonal
    J = 0.5 * Q_sym.copy()
    np.fill_diagonal(J, 0.0)

    # Linear bias vector h
    h = 0.5 * np.sum(Q_sym, axis=1)

    # Constant energy offset
    offset = float(0.25 * np.sum(Q_sym) + 0.25 * np.trace(Q_sym))

    return J, h, offset


def ising_energy(s, J, h, offset):
    """
    Compute Ising energy for a spin vector s in {-1, +1}^n:
        E(s) = 0.5 * s^T J s + h^T s + offset
             = sum_{i < j} J_ij * s_i * s_j + sum_i h_i * s_i + offset.
    """
    s_vec = np.asarray(s, dtype=float)
    return float(0.5 * (s_vec @ J @ s_vec) + np.dot(h, s_vec) + offset)


# ============================================================================
# 4. Brute-Force Solver
# ============================================================================

def solve_brute_force(adj_matrix, Q):
    """
    Solve Max-Cut by brute-force enumeration over all 2^n binary assignments.

    Parameters:
        adj_matrix (np.ndarray): (n, n) adjacency matrix.
        Q (np.ndarray): (n, n) QUBO matrix.

    Returns:
        best_cut (int): Maximum cut value found.
        best_qubo_energy (float): Minimum QUBO energy (-best_cut).
        optimal_assignments (list of np.ndarray): Binary vectors achieving maximum cut.
    """
    n = adj_matrix.shape[0]
    total_states = 1 << n  # 2^n
    best_cut = -1
    best_qubo_energy = float("inf")
    optimal_assignments = []

    for i in range(total_states):
        # Convert integer i to binary vector x
        x = np.array([(i >> (n - 1 - b)) & 1 for b in range(n)], dtype=int)
        cut = cut_value(x, adj_matrix)
        energy = qubo_energy(x, Q)

        if cut > best_cut:
            best_cut = cut
            best_qubo_energy = energy
            optimal_assignments = [x]
        elif cut == best_cut:
            optimal_assignments.append(x)

    return best_cut, best_qubo_energy, optimal_assignments


# ============================================================================
# 5. Simulated Annealing
# ============================================================================

def simulated_annealing(
    Q,
    seed=None,
    initial_temp=10.0,
    final_temp=0.01,
    cooling_rate=0.95,
    steps_per_temp=10,
):
    """
    Simulated annealing to minimise the QUBO energy x^T Q x.

    At each step:
        1. Propose flipping a randomly chosen bit k: x'_k = 1 - x_k.
        2. Compute Delta E = E(x') - E(x).
        3. If Delta E < 0, accept the move.
           Otherwise, accept with probability exp(-Delta E / T).
        4. Lower temperature T <- T * cooling_rate until T <= final_temp.

    Parameters:
        Q (np.ndarray): (n, n) QUBO matrix.
        seed (int or np.random.Generator, optional): Random seed or generator.
        initial_temp (float): Starting temperature.
        final_temp (float): Stopping temperature.
        cooling_rate (float): Geometric cooling factor per temperature step.
        steps_per_temp (int): Number of bit-flip proposals per temperature level.

    Returns:
        best_x (np.ndarray): Best binary assignment found (values in {0, 1}).
        best_energy (float): Minimum QUBO energy found during annealing.
    """
    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    n = Q.shape[0]
    # Initialize with a random binary assignment
    x = rng.integers(0, 2, size=n, dtype=int)
    current_energy = qubo_energy(x, Q)

    best_x = x.copy()
    best_energy = current_energy

    temp = initial_temp
    while temp > final_temp:
        for _ in range(steps_per_temp):
            # Propose flipping a random bit
            k = int(rng.integers(0, n))
            x_candidate = x.copy()
            x_candidate[k] = 1 - x_candidate[k]

            candidate_energy = qubo_energy(x_candidate, Q)
            delta_e = candidate_energy - current_energy

            # Metropolis acceptance criterion
            if delta_e < 0.0 or rng.random() < np.exp(-delta_e / temp):
                x = x_candidate
                current_energy = candidate_energy

                if current_energy < best_energy:
                    best_energy = current_energy
                    best_x = x.copy()

        temp *= cooling_rate

    return best_x, best_energy


def run_annealing_experiment(
    Q,
    adj_matrix,
    num_runs=50,
    seed=42,
    target_cut=13,
):
    """
    Run simulated annealing for a fixed number of runs using a master seed.

    Parameters:
        Q (np.ndarray): QUBO matrix.
        adj_matrix (np.ndarray): Graph adjacency matrix.
        num_runs (int): Number of annealing runs (default: 50).
        seed (int): Master seed for the experiment (default: 42).
        target_cut (int): Known optimal cut value.

    Returns:
        optimal_run_count (int): How many runs achieved the target cut.
        run_results (list of dict): Details of each run.
    """
    master_rng = np.random.default_rng(seed)
    optimal_run_count = 0
    run_results = []

    for run_idx in range(num_runs):
        # Pass master_rng to maintain a single reproducible stochastic sequence
        best_x, best_e = simulated_annealing(Q, seed=master_rng)
        cut = cut_value(best_x, adj_matrix)
        is_optimum = (cut == target_cut)
        if is_optimum:
            optimal_run_count += 1

        run_results.append({
            "run": run_idx + 1,
            "best_x": best_x,
            "cut": cut,
            "qubo_energy": best_e,
            "is_optimum": is_optimum,
        })

    return optimal_run_count, run_results


# ============================================================================
# 6. Pytest Tests
# ============================================================================

def test_qubo_energy_equals_negative_cut():
    """
    Check (a): For EVERY one of the 256 assignments, the QUBO energy
    equals minus the cut value: E_QUBO(x) == -Cut(x).
    """
    adj = build_graph(num_nodes=8, num_edges=18, seed=7)
    Q = maxcut_to_qubo(adj)
    n = adj.shape[0]
    total_assignments = 1 << n  # 256

    for i in range(total_assignments):
        x = np.array([(i >> (n - 1 - b)) & 1 for b in range(n)], dtype=int)
        c = cut_value(x, adj)
        e = qubo_energy(x, Q)
        assert np.isclose(e, -float(c)), (
            f"Assignment {i} ({x}) failed: QUBO energy {e} != -Cut {-c}"
        )


def test_ising_energy_equals_qubo_energy():
    """
    Check (b): The Ising energy equals the QUBO energy for EVERY one
    of the 256 assignments: E_Ising(s) == E_QUBO(x), where s = 2x - 1.
    """
    adj = build_graph(num_nodes=8, num_edges=18, seed=7)
    Q = maxcut_to_qubo(adj)
    J, h, offset = qubo_to_ising(Q)
    n = adj.shape[0]
    total_assignments = 1 << n  # 256

    for i in range(total_assignments):
        x = np.array([(i >> (n - 1 - b)) & 1 for b in range(n)], dtype=int)
        # Transform binary x in {0, 1} to spin s in {-1, +1}
        s = 2 * x - 1
        e_qubo = qubo_energy(x, Q)
        e_ising = ising_energy(s, J, h, offset)
        assert np.isclose(e_ising, e_qubo, atol=1e-12), (
            f"Assignment {i} ({x}) failed: Ising energy {e_ising} != QUBO energy {e_qubo}"
        )


def test_annealer_returns_valid_binary_vector():
    """
    Check (c): The annealer never returns an assignment that is not a valid 0/1 vector.
    Verified across multiple independent runs with various random seeds.
    """
    adj = build_graph(num_nodes=8, num_edges=18, seed=7)
    Q = maxcut_to_qubo(adj)

    # Test with 50 runs from different seeds
    for test_seed in range(50):
        best_x, _ = simulated_annealing(Q, seed=test_seed)

        # 1. Correct length / dimension
        assert isinstance(best_x, np.ndarray), "Annealer output must be a NumPy array."
        assert best_x.shape == (8,), f"Expected shape (8,), got {best_x.shape}"

        # 2. Elements must be strictly binary: 0 or 1
        assert np.all(np.isin(best_x, [0, 1])), (
            f"Run with seed {test_seed} returned invalid values: {best_x}"
        )

        # 3. Integer or binary type
        assert np.issubdtype(best_x.dtype, np.integer), (
            f"Run with seed {test_seed} returned non-integer dtype: {best_x.dtype}"
        )


# ============================================================================
# Main Execution / Demonstration
# ============================================================================

def main():
    print("=" * 70)
    print("Max-Cut QUBO & Ising Formulation with Simulated Annealing")
    print("=" * 70)

    # 1. Build graph
    adj = build_graph(num_nodes=8, num_edges=18, seed=7)
    num_edges = int(adj.sum() // 2)
    degrees = adj.sum(axis=1)
    print(f"\n1. Graph Construction:")
    print(f"   Nodes: {adj.shape[0]}, Edges: {num_edges}, Seed: 7")
    print(f"   Node degrees: {degrees.tolist()}")

    # 2. Formulate Max-Cut as QUBO
    Q = maxcut_to_qubo(adj)
    print(f"\n2. QUBO Matrix Q (size {Q.shape}, symmetric):")
    print("   Q = A - diag(deg)")
    print(Q.astype(int))

    # 3. Convert QUBO to Ising form
    J, h, offset = qubo_to_ising(Q)
    print(f"\n3. Ising Model Conversion:")
    print(f"   Coupling matrix J (shape {J.shape}, zero diagonal):")
    print(J)
    print(f"   Linear field h: {h.tolist()}")
    print(f"   Constant offset: {offset}")

    # 4. Brute-force solution
    best_cut, best_qubo_e, optimal_assignments = solve_brute_force(adj, Q)
    print(f"\n4. Brute-Force Solution (over all 256 assignments):")
    print(f"   Best cut value: {best_cut} (out of {num_edges} total edges)")
    print(f"   Minimum QUBO energy: {best_qubo_e}")
    print(f"   Number of optimal assignments: {len(optimal_assignments)}")
    print("   Optimal assignments (binary):")
    for opt_x in optimal_assignments:
        print(f"     {opt_x.tolist()}")

    # 5. Simulated Annealing (50 runs)
    num_runs = 50
    master_seed = 42
    opt_count, results = run_annealing_experiment(
        Q, adj, num_runs=num_runs, seed=master_seed, target_cut=best_cut
    )
    print(f"\n5. Simulated Annealing Experiment ({num_runs} runs, master seed {master_seed}):")
    print(f"   Runs reaching brute-force optimum ({best_cut}): {opt_count}/{num_runs} ({opt_count / num_runs * 100:.1f}%)")

    # 6. Run pytest tests
    print("\n" + "=" * 70)
    print("Running Pytest Tests...")
    print("=" * 70)
    ret_code = pytest.main(["-v", __file__])
    return ret_code


if __name__ == "__main__":
    main()

