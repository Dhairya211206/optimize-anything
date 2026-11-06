"""Random program generator for differential testing (Track F). Programs always terminate: every loop uses a
dedicated counter that is only incremented by the loop itself, with a small constant bound."""
import random

VARS = ["a", "b", "c", "d", "e"]


def rexpr(rng, depth, reuse):
    r = rng.random()
    if depth == 0 or r < 0.25:
        return ("num", rng.choice([0, 1, 2, 3, 4, 5, 8, 16, 7, -1, -3, 100, 2 ** 20]) ) if rng.random() < 0.45 else ("var", rng.choice(VARS))
    if r < 0.35 and reuse:
        return rng.choice(reuse)
    if r < 0.42:
        return ("neg", rexpr(rng, depth - 1, reuse))
    op = rng.choice(["add", "add", "sub", "mul", "mul", "lt", "eq", "ne"])
    return ("bin", op, rexpr(rng, depth - 1, reuse), rexpr(rng, depth - 1, reuse))


def rstmts(rng, depth, n, counters, reuse):
    out = []
    for _ in range(n):
        r = rng.random()
        if r < 0.55 or depth == 0:
            out.append(("assign", rng.choice(VARS), rexpr(rng, 3, reuse)))
        elif r < 0.65:
            out.append(("print", rexpr(rng, 2, reuse)))
        elif r < 0.82:
            out.append(("if", rexpr(rng, 2, reuse), rstmts(rng, depth - 1, rng.randint(1, 3), counters, reuse),
                        rstmts(rng, depth - 1, rng.randint(0, 2), counters, reuse)))
        else:
            c = f"i{len(counters)}"
            counters.append(c)
            bound = rng.randint(1, 6)
            body = rstmts(rng, depth - 1, rng.randint(1, 4), counters, reuse)
            body.append(("assign", c, ("bin", "add", ("var", c), ("num", 1))))
            out.append(("assign", c, ("num", 0)))
            out.append(("while", ("bin", "lt", ("var", c), ("num", bound)), body))
    return out


def random_program(seed, depth=2, size=6):
    rng = random.Random(seed)
    reuse = [("bin", "mul", ("var", "a"), ("var", "b")), ("bin", "add", ("var", "c"), ("num", 5))]  # repeated subexpressions
    prog = [("assign", v, ("num", rng.randint(-5, 20))) for v in VARS]
    prog += rstmts(rng, depth, size, [], reuse)
    prog += [("print", ("var", v)) for v in VARS]
    return prog
