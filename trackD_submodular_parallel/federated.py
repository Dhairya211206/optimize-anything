"""Federated averaging (FedAvg) versus centralized training (Track D). SIMULATED clients on one machine.

Model: logistic regression. Each round, every client starts from the global weights, runs
`local_steps` mini-batch SGD steps on its own data, and the server averages the client weights
weighted by client sample counts (McMahan et al., 2017). Communication cost = rounds.
"""
import numpy as np


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def make_clients(n_clients=10, n_per=200, d=20, non_iid=False, seed=0):
    """Binary classification with a shared true weight vector. IID: every client sees the same
    distribution. Non-IID: each client's label balance and feature mean differ (label skew +
    covariate shift), which causes client drift."""
    rng = np.random.default_rng(seed)
    w_true = rng.normal(size=d)
    clients = []
    for k in range(n_clients):
        shift = rng.normal(0, 1.0, d) if non_iid else np.zeros(d)
        X = rng.normal(size=(n_per * 4, d)) + shift
        y = (sigmoid(X @ w_true) > rng.uniform(size=len(X))).astype(float)
        if non_iid:  # keep a skewed label mix (either mostly 0 or mostly 1)
            want1 = 0.85 if k % 2 == 0 else 0.15
            idx1, idx0 = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
            n1 = int(n_per * want1)
            sel = np.r_[rng.choice(idx1, min(n1, len(idx1)), replace=False),
                        rng.choice(idx0, min(n_per - n1, len(idx0)), replace=False)]
        else:
            sel = np.arange(n_per)
        clients.append((X[sel], y[sel]))
    Xt = rng.normal(size=(4000, d))  # balanced global test set drawn from the unshifted distribution
    yt = (sigmoid(Xt @ w_true) > rng.uniform(size=len(Xt))).astype(float)
    return clients, (Xt, yt)


def loss_acc(w, X, y):
    p = np.clip(sigmoid(X @ w), 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), float(np.mean((p > 0.5) == (y > 0.5)))


def grad(w, X, y):
    return X.T @ (sigmoid(X @ w) - y) / len(y)


def local_sgd(w, X, y, steps, lr, batch, rng):
    w = w.copy()
    for _ in range(steps):
        idx = rng.choice(len(y), size=min(batch, len(y)), replace=False)
        w -= lr * grad(w, X[idx], y[idx])
    return w


def fedavg(clients, test, rounds, local_steps, lr=0.1, batch=20, seed=0):
    rng = np.random.default_rng(seed)
    d = clients[0][0].shape[1]
    w = np.zeros(d)
    sizes = np.array([len(c[1]) for c in clients], float)
    hist = []
    for r in range(rounds):
        ws = [local_sgd(w, X, y, local_steps, lr, batch, rng) for X, y in clients]
        w = np.average(ws, axis=0, weights=sizes)
        hist.append(loss_acc(w, *test))
    grad_evals = rounds * local_steps * len(clients) * batch  # sample-gradients computed in total
    return w, hist, grad_evals


def centralized_sgd(clients, test, steps, lr=0.1, batch=20, seed=0, record_every=1):
    """Pooled-data mini-batch SGD with the same batch size and learning rate."""
    rng = np.random.default_rng(seed)
    X = np.vstack([c[0] for c in clients])
    y = np.concatenate([c[1] for c in clients])
    w = np.zeros(X.shape[1])
    hist = []
    for t in range(steps):
        idx = rng.choice(len(y), size=batch, replace=False)
        w -= lr * grad(w, X[idx], y[idx])
        if (t + 1) % record_every == 0:
            hist.append(loss_acc(w, *test))
    return w, hist, steps * batch
