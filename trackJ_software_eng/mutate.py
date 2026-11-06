"""A small AST mutation tester (Track J): generates single-point mutants of Python modules and records which tests kill them."""
import ast
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add}
BOOL = {ast.And: ast.Or, ast.Or: ast.And}


class _Apply(ast.NodeTransformer):
    def __init__(self, k):
        self.k, self.i, self.done = k, -1, False

    def _hit(self):
        self.i += 1
        return self.i == self.k

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in BIN:
            if self._hit():
                node.op = BIN[type(node.op)]()
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in CMP:
            if self._hit():
                node.ops = [CMP[type(node.ops[0])]()]
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if type(node.op) in BOOL:
            if self._hit():
                node.op = BOOL[type(node.op)]()
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            if self._hit():
                return node.operand
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            if self._hit():
                return ast.copy_location(ast.Constant(node.value + 1), node)
        return node


def count_sites_visit_order(tree):
    a = _Apply(-1)
    a.visit(ast.parse(ast.unparse(tree)))
    return a.i + 1


def mutate_source(src, k):
    """Return the source with the k-th mutable site (in transformer visit order) mutated."""
    tree = ast.parse(src)
    a = _Apply(k)
    new = ast.fix_missing_locations(a.visit(tree))
    return ast.unparse(new)


def run_tests(pkg_dir, timeout=120):
    """Run pytest in pkg_dir; returns (status, failed_test_names). status: 'ok' | 'killed' | 'crash' | 'timeout'."""
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", pkg_dir, "-q", "-p", "no:cacheprovider", "--tb=no", "-rfE", "-W", "ignore"],
                           capture_output=True, text=True, timeout=timeout, cwd=os.path.dirname(pkg_dir))
    except subprocess.TimeoutExpired:
        return "timeout", set()
    failed = set(re.findall(r"^(?:FAILED|ERROR) \S*?::(\w+)", p.stdout, flags=re.M))
    if "error" in p.stdout.lower() and ("ERROR collecting" in p.stdout or "errors during collection" in p.stdout or "Interrupted" in p.stdout):
        return "crash", failed
    return ("killed" if failed else "ok"), failed


def kill_matrix(pkg_dir, modules, n_mutants, seed=0, timeout=120, log=print):
    """Sample n_mutants single-point mutants of the given modules (file names inside pkg_dir) and run the suite on each.
    Returns list of dicts {module, k, lineno?, status, killed_by}."""
    rng = random.Random(seed)
    pool = []
    for mod in modules:
        src = open(os.path.join(pkg_dir, mod)).read()
        n = count_sites_visit_order(ast.parse(src))
        pool += [(mod, k) for k in range(n)]
    chosen = rng.sample(pool, min(n_mutants, len(pool)))
    out = []
    for i, (mod, k) in enumerate(chosen):
        tmp = tempfile.mkdtemp()
        dst = os.path.join(tmp, os.path.basename(pkg_dir))
        shutil.copytree(pkg_dir, dst, ignore=shutil.ignore_patterns("__pycache__", "results", ".pytest_cache"))
        path = os.path.join(dst, mod)
        original = open(path).read()
        mutated = mutate_source(original, k)
        if ast.unparse(ast.parse(original)) == mutated:
            shutil.rmtree(tmp)
            continue  # no change
        open(path, "w").write(mutated)
        status, failed = run_tests(dst, timeout)
        out.append(dict(module=mod, site=k, status=status, killed_by=sorted(failed)))
        shutil.rmtree(tmp)
        log(f"mutant {i + 1}/{len(chosen)} {mod}#{k}: {status} ({len(failed)} tests fail)")
    return out
