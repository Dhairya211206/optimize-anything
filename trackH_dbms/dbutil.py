"""SQLite helpers for Track H: timing with a cap, result hashing, index sizes, query plans."""
import hashlib
import sqlite3
import time

import numpy as np

CAP_SECONDS = 60.0


def normalise(rows):
    out = []
    for r in rows:
        out.append(tuple(f"{x:.9g}" if isinstance(x, float) else str(x) for x in r))
    return out


def run_query(con, sql, cap=CAP_SECONDS):
    """Run one query; returns (rows, seconds, timed_out)."""
    t0 = time.perf_counter()
    con.set_progress_handler(lambda: 1 if time.perf_counter() - t0 > cap else 0, 20000)
    try:
        rows = con.execute(sql).fetchall()
        timed_out = False
    except sqlite3.OperationalError:
        rows, timed_out = [], True
    con.set_progress_handler(None, 0)
    return rows, time.perf_counter() - t0, timed_out


def result_hash(rows):
    return hashlib.md5(repr(normalise(rows)).encode()).hexdigest()


def measure(con, sql, reps=3, cap=CAP_SECONDS):
    """Minimum of `reps` runs after one warm-up run (the minimum is the least noisy estimate of the cost on a busy machine)."""
    rows, t, to = run_query(con, sql, cap)
    best = t
    for _ in range(reps):
        rows, t, to2 = run_query(con, sql, cap)
        best = min(best, t)
        to = to or to2
    return best, result_hash(rows), to


def index_size_bytes(con, name):
    try:
        v = con.execute("SELECT SUM(pgsize) FROM dbstat WHERE name = ?", (name,)).fetchone()[0]
        return int(v)
    except sqlite3.OperationalError:
        return None


def plan(con, sql):
    return [r[3] for r in con.execute("EXPLAIN QUERY PLAN " + sql).fetchall()]


def create_indexes(con, names, candidates):
    for n in names:
        con.execute(f"CREATE INDEX ix_{n} ON {candidates[n]}")
        con.execute(f"ANALYZE ix_{n}")
    con.commit()


def drop_indexes(con, names):
    for n in names:
        con.execute(f"DROP INDEX IF EXISTS ix_{n}")
    con.commit()
