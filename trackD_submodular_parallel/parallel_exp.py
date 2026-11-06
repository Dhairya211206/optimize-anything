"""Parallel-computing experiments (Track D).

MEASURED results use real processes on this machine (it has only 2 CPU cores, so real speedup is
capped near 2). SIMULATED results use a discrete-event model and are labelled as such wherever they
are reported. No simulated number is a hardware measurement.
"""
import multiprocessing as mp
import time

import numpy as np


# ------------------------------------------------------------------ a CPU-bound task
def work(n):
    """Deterministic pure-Python CPU work whose cost is proportional to n."""
    s = 0
    for i in range(n):
        s += (i * i) % 7
    return s


def timed(fn, repeats=3):
    ts = []
    out = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t0)
    return out, float(np.median(ts))


# ------------------------------------------------------------------ data parallelism, speedup, laws
def run_data_parallel(tasks, workers):
    if workers == 1:
        return [work(n) for n in tasks]
    with mp.Pool(workers) as pool:
        return pool.map(work, tasks, chunksize=max(1, len(tasks) // (workers * 4)))


def amdahl_speedup(serial_fraction, p):
    return 1.0 / (serial_fraction + (1 - serial_fraction) / p)


def gustafson_speedup(serial_fraction, p):
    return p - serial_fraction * (p - 1)


def serial_fraction_from_speedup(speedup, p):
    """Invert Amdahl: S = 1 / (s + (1-s)/p)  ->  s = (1/S - 1/p) / (1 - 1/p)."""
    return (1.0 / speedup - 1.0 / p) / (1.0 - 1.0 / p)


# ------------------------------------------------------------------ real load balancing (2 workers)
def run_static_blocks(tasks, workers):
    with mp.Pool(workers) as pool:
        return pool.map(work, tasks, chunksize=int(np.ceil(len(tasks) / workers)))


def run_static_round_robin(tasks, workers):
    order = [i for w in range(workers) for i in range(w, len(tasks), workers)]
    reordered = [tasks[i] for i in order]
    with mp.Pool(workers) as pool:
        return pool.map(work, reordered, chunksize=int(np.ceil(len(tasks) / workers)))


def run_dynamic(tasks, workers, lpt=False):
    t = sorted(tasks, reverse=True) if lpt else list(tasks)
    with mp.Pool(workers) as pool:
        return list(pool.imap_unordered(work, t, chunksize=1))


# ------------------------------------------------------------------ SIMULATED scheduling
def simulate_schedule(costs, p, strategy, steal_cost=0.0, dispatch_cost=0.0, steal_locality_penalty=0.0, seed=0):
    """Discrete-event simulation of p workers.

    strategies:
      static_block   contiguous blocks of tasks, no balancing
      round_robin    task i goes to worker i mod p
      dynamic        one shared queue; idle worker takes the next task, paying dispatch_cost each time
      lpt            dynamic, tasks sorted longest-first
      work_stealing  initial block assignment; an idle worker steals the LAST task of a random non-empty
                     victim's deque, paying steal_cost plus steal_locality_penalty * task cost (data not
                     local). Returns the makespan and the number of steals.
    """
    rng = np.random.default_rng(seed)
    costs = np.asarray(costs, float)
    n = len(costs)
    if strategy == "static_block":
        parts = np.array_split(np.arange(n), p)
        return max(costs[x].sum() for x in parts), 0
    if strategy == "round_robin":
        return max(costs[w::p].sum() for w in range(p)), 0
    if strategy in ("dynamic", "lpt"):
        order = np.argsort(-costs) if strategy == "lpt" else np.arange(n)
        free = [0.0] * p
        import heapq
        heapq.heapify(free)
        for i in order:
            t = heapq.heappop(free)
            heapq.heappush(free, t + dispatch_cost + costs[i])
        return max(free), 0
    if strategy == "work_stealing":
        import heapq
        deques = [list(x) for x in np.array_split(np.arange(n), p)]
        heap = [(0.0, w) for w in range(p)]
        heapq.heapify(heap)
        finish = [0.0] * p
        steals = 0
        while heap:
            t, w = heapq.heappop(heap)
            if deques[w]:
                i = deques[w].pop(0)
                dt = costs[i]
            else:
                victims = [v for v in range(p) if deques[v]]
                if not victims:
                    finish[w] = t
                    continue
                v = int(rng.choice(victims))
                i = deques[v].pop()  # steal from the far end
                steals += 1
                dt = steal_cost + costs[i] * (1 + steal_locality_penalty)
            heapq.heappush(heap, (t + dt, w))
            finish[w] = t + dt
        return max(finish), steals
    raise ValueError(strategy)


# ------------------------------------------------------------------ pipeline parallelism (sleep-based stages)
def _stage(q_in, q_out, t_stage):
    while True:
        item = q_in.get()
        if item is None:
            q_out.put(None)
            return
        time.sleep(t_stage)  # stands in for the stage's work
        q_out.put(item)


def run_pipeline(stage_times, microbatches):
    """Real processes connected by queues; stage work is simulated with sleep, so this measures the
    pipeline overlap and queue overhead, not compute."""
    qs = [mp.Queue() for _ in range(len(stage_times) + 1)]
    procs = [mp.Process(target=_stage, args=(qs[i], qs[i + 1], stage_times[i])) for i in range(len(stage_times))]
    for p in procs:
        p.start()
    t0 = time.perf_counter()
    for m in range(microbatches):
        qs[0].put(m)
    qs[0].put(None)
    got = 0
    while True:
        x = qs[-1].get()
        if x is None:
            break
        got += 1
    elapsed = time.perf_counter() - t0
    for p in procs:
        p.join()
    return elapsed, got


# ------------------------------------------------------------------ model parallelism (split a layer)
_W = {}


def _init_half(w_half):
    _W["w"] = w_half


def _half_forward(x):
    return np.maximum(x @ _W["w"], 0.0)


def run_model_parallel(x, w, repeats=3):
    """Split the weight matrix of one layer column-wise over 2 worker processes. Returns
    (single_process_time, model_parallel_time). The x batch is sent to both workers every call, so
    communication cost is included."""
    h = w.shape[1] // 2
    single = timed(lambda: np.maximum(x @ w, 0.0), repeats)[1]
    # one single-worker pool per half, because each worker must hold a different half of the weights
    pools =[mp.Pool(1, initializer=_init_half, initargs=(w[:, :h],)),
             mp.Pool(1, initializer=_init_half, initargs=(w[:, h:],))]
    try:
        def call():
            r = [p.apply_async(_half_forward, (x,)) for p in pools]
            return np.hstack([a.get() for a in r])
        out, parallel = timed(call, repeats)
        ref = np.maximum(x @ w, 0.0)
        assert np.allclose(out, ref)
    finally:
        for p in pools:
            p.close()
            p.join()
    return single, parallel
