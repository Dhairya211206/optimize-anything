"""Documented SYNTHETIC TPC-H-like dataset for SQLite (Track H). NOT the official TPC-H dbgen output.

Scale factor SF follows TPC-H row counts: customer 150000*SF, orders 1500000*SF, lineitem about 6000000*SF, part 200000*SF,
supplier 10000*SF, nation 25, region 5. Default SF = 0.1 (15,000 customers, 150,000 orders, about 600,000 line items).
Dates are integer day numbers 0..2555 (seven years). Value distributions are simple (uniform or small categorical sets,
with a skew on order priority and ship mode) and fixed by a seed, so the data are reproducible."""
import os
import sqlite3

import numpy as np

SCHEMA = """
CREATE TABLE region(r_regionkey INTEGER PRIMARY KEY, r_name TEXT);
CREATE TABLE nation(n_nationkey INTEGER PRIMARY KEY, n_name TEXT, n_regionkey INTEGER);
CREATE TABLE supplier(s_suppkey INTEGER PRIMARY KEY, s_nationkey INTEGER, s_acctbal REAL);
CREATE TABLE customer(c_custkey INTEGER PRIMARY KEY, c_nationkey INTEGER, c_acctbal REAL, c_mktsegment TEXT);
CREATE TABLE part(p_partkey INTEGER PRIMARY KEY, p_brand TEXT, p_type TEXT, p_size INTEGER);
CREATE TABLE orders(o_orderkey INTEGER PRIMARY KEY, o_custkey INTEGER, o_orderstatus TEXT, o_totalprice REAL,
                    o_orderdate INTEGER, o_orderpriority TEXT);
CREATE TABLE lineitem(l_orderkey INTEGER, l_linenumber INTEGER, l_partkey INTEGER, l_suppkey INTEGER, l_quantity INTEGER,
                      l_extendedprice REAL, l_discount REAL, l_returnflag TEXT, l_shipdate INTEGER, l_shipmode TEXT,
                      PRIMARY KEY(l_orderkey, l_linenumber)) WITHOUT ROWID;
"""
SEGMENTS = ["AUTOMOBILE", "BUILDING", "FURNITURE", "HOUSEHOLD", "MACHINERY"]
PRIORITIES = ["1-URGENT", "2-HIGH", "3-MEDIUM", "4-NOT SPECIFIED", "5-LOW"]
MODES = ["AIR", "FOB", "MAIL", "RAIL", "REG AIR", "SHIP", "TRUCK"]
TYPES = ["STANDARD", "SMALL", "MEDIUM", "LARGE", "ECONOMY", "PROMO"]


def build(path, sf=0.1, seed=0):
    if os.path.exists(path):
        os.remove(path)
    rng = np.random.default_rng(seed)
    n_cust, n_ord, n_part, n_supp = int(150000 * sf), int(1500000 * sf), int(200000 * sf), max(10, int(10000 * sf))
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO region VALUES(?,?)", [(i, f"REGION{i}") for i in range(5)])
    con.executemany("INSERT INTO nation VALUES(?,?,?)", [(i, f"NATION{i}", i % 5) for i in range(25)])
    con.executemany("INSERT INTO supplier VALUES(?,?,?)",
                    [(i + 1, int(rng.integers(25)), float(rng.uniform(-999, 9999))) for i in range(n_supp)])
    con.executemany("INSERT INTO customer VALUES(?,?,?,?)",
                    [(i + 1, int(rng.integers(25)), float(rng.uniform(-999, 9999)), SEGMENTS[int(rng.integers(5))]) for i in range(n_cust)])
    con.executemany("INSERT INTO part VALUES(?,?,?,?)",
                    [(i + 1, f"Brand#{int(rng.integers(1, 6))}{int(rng.integers(1, 6))}", TYPES[int(rng.integers(6))], int(rng.integers(1, 51)))
                     for i in range(n_part)])
    odate = rng.integers(0, 2406, n_ord)
    oprio = rng.choice(5, n_ord, p=[0.3, 0.25, 0.2, 0.15, 0.1])
    ocust = rng.integers(1, n_cust + 1, n_ord)
    ostat = rng.choice(["F", "O", "P"], n_ord, p=[0.49, 0.49, 0.02])
    con.executemany("INSERT INTO orders VALUES(?,?,?,?,?,?)",
                    [(i + 1, int(ocust[i]), str(ostat[i]), float(rng.uniform(1000, 400000)), int(odate[i]), PRIORITIES[oprio[i]])
                     for i in range(n_ord)])
    rows = []
    nlines = rng.integers(1, 8, n_ord)
    for o in range(n_ord):
        for ln in range(nlines[o]):
            ship = int(odate[o] + rng.integers(1, 122))
            rows.append((o + 1, ln + 1, int(rng.integers(1, n_part + 1)), int(rng.integers(1, n_supp + 1)), int(rng.integers(1, 51)),
                         float(rng.uniform(900, 105000)), float(round(rng.integers(0, 11) / 100, 2)),
                         "R" if (ship < 1700 and rng.uniform() < 0.5) else ("A" if ship < 1700 else "N"), ship,
                         MODES[int(rng.choice(7, p=[0.2, 0.1, 0.15, 0.15, 0.1, 0.1, 0.2]))]))
    con.executemany("INSERT INTO lineitem VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.execute("ANALYZE")
    con.commit()
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("region", "nation", "supplier", "customer", "part", "orders", "lineitem")}
    con.close()
    return counts
