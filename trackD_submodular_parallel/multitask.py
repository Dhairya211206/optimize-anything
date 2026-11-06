"""Multi-task optimization on a two-task model: equal weighting vs MGDA vs GradNorm (Track D).

Model: shared tanh layer (d -> h) feeding two linear heads. Loss_i = MSE of task i.
  equal    : L = L_1 + L_2
  mgda     : L = a_1 L_1 + a_2 L_2 with (a_1, a_2) the min-norm convex combination of the two task
             gradients on the SHARED parameters (closed form for two tasks; Desideri 2012, Sener & Koltun 2018)
  gradnorm : loss weights w_i adapted so each task's gradient norm on the shared layer tracks a target
             set by its relative training rate (Chen et al., 2018), alpha = 1.5, weights sum to 2.
Task scales differ by design (task 2 targets are about 25x larger), which is the situation where equal
weighting lets one task dominate.
"""
import numpy as np


def make_data(n=600, d=8, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, d))
    a, b = rng.normal(size=d), rng.normal(size=d)
    za, zb = X @ a / np.sqrt(d), X @ b / np.sqrt(d)
    y1 = np.sin(2 * za) + 0.3 * zb + 0.05 * rng.normal(size=n)
    y2 = 25 * (np.cos(1.5 * zb) - 0.5 * za) + 1.0 * rng.normal(size=n)
    Y = np.c_[y1, y2]
    # Centre the targets (the scale difference between tasks is kept). Without this, task 2 has a mean of
    # about 15 that Adam, which moves a bias by at most lr per step, needs thousands of steps to reach.
    return X, Y - Y.mean(axis=0)


class TwoTaskNet:
    def __init__(self, d, h=16, seed=0):
        rng = np.random.default_rng(seed)
        self.d, self.h = d, h
        self.W = rng.normal(0, 0.5, (d, h))
        self.b = np.zeros(h)
        self.V = rng.normal(0, 0.5, (h, 2))
        self.c = np.zeros(2)

    def params(self):
        return [self.W, self.b, self.V, self.c]

    def forward(self, X):
        H = np.tanh(X @ self.W + self.b)
        return H, H @ self.V + self.c

    def task_losses(self, X, Y):
        _, P = self.forward(X)
        return np.mean((P - Y) ** 2, axis=0)

    def task_grads(self, X, Y):
        """Gradient of each task's MSE w.r.t. [W, b, V, c], computed by hand-written backprop.
        Returns list of two lists of arrays (shared params first: W, b; then V, c)."""
        n = len(X)
        H, P = self.forward(X)
        out = []
        for t in range(2):
            dP = np.zeros_like(P)
            dP[:, t] = 2 * (P[:, t] - Y[:, t]) / n
            dV = H.T @ dP
            dc = dP.sum(axis=0)
            dH = dP @ self.V.T
            dZ = dH * (1 - H ** 2)
            out.append([X.T @ dZ, dZ.sum(axis=0), dV, dc])
        return out


def flat_shared(g):
    return np.concatenate([g[0].ravel(), g[1].ravel()])


def mgda_alpha(g1, g2):
    """argmin_{a in [0,1]} || a g1 + (1-a) g2 ||^2  ->  a = clip(((g2 - g1) . g2) / ||g1 - g2||^2, 0, 1)."""
    diff = g1 - g2
    den = float(diff @ diff)
    if den < 1e-20:
        return 0.5
    return float(np.clip(((g2 - g1) @ g2) / den, 0.0, 1.0))


class Adam:
    def __init__(self, shapes, lr=0.01, b1=0.9, b2=0.999, eps=1e-8):
        self.m = [np.zeros(s) for s in shapes]
        self.v = [np.zeros(s) for s in shapes]
        self.t, self.lr, self.b1, self.b2, self.eps = 0, lr, b1, b2, eps

    def step(self, params, grads):
        self.t += 1
        for i, (p, g) in enumerate(zip(params, grads)):
            self.m[i] = self.b1 * self.m[i] + (1 - self.b1) * g
            self.v[i] = self.b2 * self.v[i] + (1 - self.b2) * g * g
            mh = self.m[i] / (1 - self.b1 ** self.t)
            vh = self.v[i] / (1 - self.b2 ** self.t)
            p -= self.lr * mh / (np.sqrt(vh) + self.eps)


def train(method, X, Y, steps=1500, lr=0.01, seed=0, gn_alpha=1.5, gn_lr=0.025):
    net = TwoTaskNet(X.shape[1], seed=seed)
    opt = Adam([p.shape for p in net.params()], lr=lr)
    w = np.array([1.0, 1.0])
    L0 = net.task_losses(X, Y)
    weights_hist = []
    for _ in range(steps):
        gs = net.task_grads(X, Y)
        if method == "equal":
            w = np.array([1.0, 1.0])
        elif method == "mgda":
            a = mgda_alpha(flat_shared(gs[0]), flat_shared(gs[1]))
            w = np.array([a, 1 - a]) * 2.0  # scaled so the weights sum to 2, like the others
        elif method == "gradnorm":
            G = np.array([np.linalg.norm(w[t] * flat_shared(gs[t])) for t in range(2)])
            L = net.task_losses(X, Y)
            r = (L / L0) / np.mean(L / L0)
            target = G.mean() * r ** gn_alpha
            # d/dw_i of sum_i |G_i - target_i|, with G_i proportional to w_i and target held constant
            gw = np.sign(G - target) * G / np.maximum(w, 1e-8)
            w = np.maximum(w - gn_lr * gw, 1e-3)
            w = 2.0 * w / w.sum()
        else:
            raise ValueError(method)
        grads = [w[0] * a + w[1] * b for a, b in zip(gs[0], gs[1])]
        opt.step(net.params(), grads)
        weights_hist.append(w.copy())
    return net, np.array(weights_hist)


def relative_mse(net, X, Y):
    """MSE of each task divided by the variance of its targets (1.0 = predicting the mean)."""
    return net.task_losses(X, Y) / Y.var(axis=0)
