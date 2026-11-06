"""Small MLP with hand-written backpropagation (Track A).

Backprop computes the GRADIENT of the loss. It is not an optimizer: the optimizers in
optimizers.py consume that gradient. Keeping them separate is a Chapter 6 requirement.

Model: 2 inputs -> H tanh units -> 1 sigmoid output. Loss: binary cross-entropy plus
L2 regularization (lam/2 * ||W||^2 on weights, not biases).
All parameters live in one flat vector so any optimizer can act on them.
"""
import numpy as np


def make_moons(n=200, noise=0.2, seed=0):
    """Two interleaving half-circles, generated with numpy only."""
    rng = np.random.default_rng(seed)
    n1 = n // 2
    t1 = rng.uniform(0, np.pi, n1)
    t2 = rng.uniform(0, np.pi, n - n1)
    a = np.c_[np.cos(t1), np.sin(t1)]
    b = np.c_[1 - np.cos(t2), 0.5 - np.sin(t2)]
    X = np.vstack([a, b]) + rng.normal(0, noise, (n, 2))
    y = np.r_[np.zeros(n1), np.ones(n - n1)]
    return X, y


class MLP:
    def __init__(self, hidden=8, lam=1e-3):
        self.h = hidden
        self.lam = lam
        self.n_params = 2 * hidden + hidden + hidden + 1

    def init(self, seed=0):
        rng = np.random.default_rng(seed)
        W1 = rng.normal(0, 0.5, (2, self.h))
        b1 = np.zeros(self.h)
        W2 = rng.normal(0, 0.5, self.h)
        b2 = np.zeros(1)
        return np.concatenate([W1.ravel(), b1, W2, b2])

    def unpack(self, p):
        h = self.h
        W1 = p[: 2 * h].reshape(2, h)
        b1 = p[2 * h: 3 * h]
        W2 = p[3 * h: 4 * h]
        b2 = p[4 * h]
        return W1, b1, W2, b2

    def forward(self, p, X):
        W1, b1, W2, b2 = self.unpack(p)
        z1 = X @ W1 + b1
        a1 = np.tanh(z1)
        z2 = a1 @ W2 + b2
        return z1, a1, 1.0 / (1.0 + np.exp(-z2))

    def loss(self, p, X, y):
        _, _, out = self.forward(p, X)
        eps = 1e-12
        bce = -np.mean(y * np.log(out + eps) + (1 - y) * np.log(1 - out + eps))
        W1, _, W2, _ = self.unpack(p)
        return bce + 0.5 * self.lam * (np.sum(W1 ** 2) + np.sum(W2 ** 2))

    def grad(self, p, X, y):
        """Backpropagation, derived by hand.

        With sigmoid + BCE the output-layer error simplifies to dz2 = (out - y) / n.
        Then: dW2 = a1^T dz2 ; da1 = dz2 W2^T ; dz1 = da1 * (1 - a1^2) ; dW1 = X^T dz1.
        """
        n = X.shape[0]
        W1, b1, W2, b2 = self.unpack(p)
        z1, a1, out = self.forward(p, X)
        dz2 = (out - y) / n
        dW2 = a1.T @ dz2 + self.lam * W2
        db2 = np.sum(dz2)
        da1 = np.outer(dz2, W2)
        dz1 = da1 * (1.0 - a1 ** 2)
        dW1 = X.T @ dz1 + self.lam * W1
        db1 = dz1.sum(axis=0)
        return np.concatenate([dW1.ravel(), db1, dW2, [db2]])

    def accuracy(self, p, X, y):
        _, _, out = self.forward(p, X)
        return float(np.mean((out > 0.5) == (y > 0.5)))


def finite_difference_grad(f, p, eps=1e-6):
    """Central-difference gradient, used ONLY to check backprop."""
    g = np.zeros_like(p)
    for i in range(p.size):
        e = np.zeros_like(p)
        e[i] = eps
        g[i] = (f(p + e) - f(p - e)) / (2 * eps)
    return g
