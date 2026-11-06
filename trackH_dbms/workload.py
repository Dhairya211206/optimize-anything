"""Twelve TPC-H-inspired queries (written for this project; simplified, not the official TPC-H text) with weights,
and the candidate index set for the index-selection problem."""

QUERIES = {
    "Q1_pricing": ("SELECT l_returnflag, SUM(l_quantity), SUM(l_extendedprice), COUNT(*) FROM lineitem "
                   "WHERE l_shipdate <= 2000 GROUP BY l_returnflag ORDER BY l_returnflag", 1),
    "Q3_shipping_priority": ("SELECT l_orderkey, SUM(l_extendedprice * (1 - l_discount)) AS rev, o_orderdate FROM customer, orders, lineitem "
                             "WHERE c_mktsegment = 'BUILDING' AND c_custkey = o_custkey AND l_orderkey = o_orderkey "
                             "AND o_orderdate < 1200 AND l_shipdate > 1200 GROUP BY l_orderkey, o_orderdate "
                             "ORDER BY rev DESC, o_orderdate LIMIT 10", 2),
    "Q4_order_priority": ("SELECT o_orderpriority, COUNT(*) FROM orders WHERE o_orderdate >= 1000 AND o_orderdate < 1090 "
                          "AND EXISTS (SELECT 1 FROM lineitem WHERE l_orderkey = o_orderkey AND l_shipdate > o_orderdate + 60) "
                          "GROUP BY o_orderpriority ORDER BY o_orderpriority", 2),
    "Q5_local_supplier": ("SELECT n_name, SUM(l_extendedprice * (1 - l_discount)) AS rev FROM customer, orders, lineitem, supplier, nation "
                          "WHERE c_custkey = o_custkey AND l_orderkey = o_orderkey AND l_suppkey = s_suppkey AND c_nationkey = s_nationkey "
                          "AND s_nationkey = n_nationkey AND n_regionkey = 2 AND o_orderdate >= 700 AND o_orderdate < 1065 "
                          "GROUP BY n_name ORDER BY rev DESC", 1),
    "Q6_forecast_revenue": ("SELECT SUM(l_extendedprice * l_discount) FROM lineitem WHERE l_shipdate >= 800 AND l_shipdate < 1165 "
                            "AND l_discount BETWEEN 0.05 AND 0.07 AND l_quantity < 24", 3),
    "Q10_returned_items": ("SELECT c_custkey, SUM(l_extendedprice * (1 - l_discount)) AS rev FROM customer, orders, lineitem "
                           "WHERE c_custkey = o_custkey AND l_orderkey = o_orderkey AND o_orderdate >= 900 AND o_orderdate < 990 "
                           "AND l_returnflag = 'R' GROUP BY c_custkey ORDER BY rev DESC LIMIT 20", 2),
    "Q12_shipmode": ("SELECT l_shipmode, COUNT(*) FROM orders, lineitem WHERE o_orderkey = l_orderkey AND l_shipmode IN ('MAIL', 'SHIP') "
                     "AND l_shipdate >= 1500 AND l_shipdate < 1865 AND o_orderpriority IN ('1-URGENT', '2-HIGH') "
                     "GROUP BY l_shipmode ORDER BY l_shipmode", 1),
    "Q14_promo_part": ("SELECT SUM(CASE WHEN p_type = 'PROMO' THEN l_extendedprice * (1 - l_discount) ELSE 0 END), "
                       "SUM(l_extendedprice * (1 - l_discount)) FROM lineitem, part WHERE l_partkey = p_partkey "
                       "AND l_shipdate >= 1200 AND l_shipdate < 1230", 1),
    "P1_customer_orders": ("SELECT COUNT(*), SUM(o_totalprice) FROM orders WHERE o_custkey = 4242", 20),
    "P2_order_lines": ("SELECT COUNT(*), SUM(l_extendedprice) FROM lineitem WHERE l_orderkey = 77777", 20),
    "P3_segment_nation": ("SELECT COUNT(*), AVG(c_acctbal) FROM customer WHERE c_nationkey = 7 AND c_mktsegment = 'MACHINERY'", 10),
    "P4_part_search": ("SELECT COUNT(*) FROM part WHERE p_brand = 'Brand#23' AND p_size = 15", 10),
}

CANDIDATES = {
    "li_orderkey_shipdate": "lineitem(l_orderkey, l_shipdate)",
    "li_shipdate": "lineitem(l_shipdate)",
    "li_shipdate_disc_qty": "lineitem(l_shipdate, l_discount, l_quantity)",
    "li_partkey": "lineitem(l_partkey)",
    "li_partkey_shipdate": "lineitem(l_partkey, l_shipdate)",
    "li_suppkey": "lineitem(l_suppkey)",
    "li_returnflag_orderkey": "lineitem(l_returnflag, l_orderkey)",
    "li_shipmode_shipdate": "lineitem(l_shipmode, l_shipdate)",
    "li_shipmode": "lineitem(l_shipmode)",
    "li_returnflag": "lineitem(l_returnflag)",
    "o_custkey": "orders(o_custkey)",
    "o_custkey_orderdate": "orders(o_custkey, o_orderdate)",
    "o_orderdate": "orders(o_orderdate)",
    "o_orderdate_custkey": "orders(o_orderdate, o_custkey)",
    "o_orderpriority": "orders(o_orderpriority)",
    "o_orderdate_priority": "orders(o_orderdate, o_orderpriority)",
    "c_mktsegment": "customer(c_mktsegment)",
    "c_nationkey": "customer(c_nationkey)",
    "c_nation_segment": "customer(c_nationkey, c_mktsegment)",
    "c_segment_custkey": "customer(c_mktsegment, c_custkey)",
    "p_brand": "part(p_brand)",
    "p_size": "part(p_size)",
    "p_brand_size": "part(p_brand, p_size)",
    "s_nationkey": "supplier(s_nationkey)",
    "n_regionkey": "nation(n_regionkey)",
}
