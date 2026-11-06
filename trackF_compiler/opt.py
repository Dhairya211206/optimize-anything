"""IR optimisation passes (Track F).

Passes: const_fold, strength (algebraic simplification + strength reduction), copy_prop, cse (local value
numbering), licm (loop-invariant code motion), dce (liveness-based dead code + unreachable code removal).
All local passes work within basic blocks; dce and licm use global liveness over the CFG.
Every pass takes and returns a list of IR tuples and must preserve the program's printed output.
"""
from frontend import apply_op

COMM = {"add", "mul", "eq", "ne"}


def is_var(x):
    return isinstance(x, str)


def dst(ins):
    op = ins[0]
    if op == "bin":
        return ins[2]
    if op in ("neg", "mov"):
        return ins[1]
    return None


def operands(ins):
    op = ins[0]
    if op == "bin":
        return [ins[3], ins[4]]
    if op in ("neg", "mov"):
        return [ins[2]]
    if op in ("print", "jz"):
        return [ins[1]]
    return []


def uses(ins):
    return [x for x in operands(ins) if is_var(x)]


def subst(ins, f):
    """Return ins with every operand x replaced by f(x)."""
    op = ins[0]
    if op == "bin":
        return ("bin", ins[1], ins[2], f(ins[3]), f(ins[4]))
    if op in ("neg", "mov"):
        return (op, ins[1], f(ins[2]))
    if op == "print":
        return ("print", f(ins[1]))
    if op == "jz":
        return ("jz", f(ins[1]), ins[2])
    return ins


# ------------------------------------------------------------------ CFG and liveness
def split_blocks(code):
    blocks, cur = [], []
    for ins in code:
        if ins[0] == "label":
            if cur:
                blocks.append(cur)
            cur = [ins]
        else:
            cur.append(ins)
            if ins[0] in ("jmp", "jz"):
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    return blocks


def successors(blocks):
    lab = {b[0][1]: i for i, b in enumerate(blocks) if b[0][0] == "label"}
    succ = []
    for i, b in enumerate(blocks):
        last = b[-1]
        s = []
        if last[0] == "jmp":
            s = [lab[last[1]]]
        else:
            if last[0] == "jz":
                s.append(lab[last[2]])
            if i + 1 < len(blocks):
                s.append(i + 1)
        succ.append(s)
    return succ


def block_liveness(blocks):
    succ = successors(blocks)
    use, dfn = [], []
    for b in blocks:
        u, d = set(), set()
        for ins in b:
            for x in uses(ins):
                if x not in d:
                    u.add(x)
            if dst(ins) is not None:
                d.add(dst(ins))
        use.append(u)
        dfn.append(d)
    live_in = [set() for _ in blocks]
    live_out = [set() for _ in blocks]
    changed = True
    while changed:
        changed = False
        for i in reversed(range(len(blocks))):
            out = set().union(*[live_in[s] for s in succ[i]]) if succ[i] else set()
            new_in = use[i] | (out - dfn[i])
            if out != live_out[i] or new_in != live_in[i]:
                live_out[i], live_in[i] = out, new_in
                changed = True
    return live_in, live_out


def liveness_by_instr(code):
    """live_after[i] = set of variables live immediately after instruction i."""
    blocks = split_blocks(code)
    _, live_out = block_liveness(blocks)
    res = []
    for b, lo in zip(blocks, live_out):
        live = set(lo)
        after = []
        for ins in reversed(b):
            after.append(set(live))
            d = dst(ins)
            if d is not None:
                live.discard(d)
            live.update(uses(ins))
        res.extend(reversed(after))
    return res


# ------------------------------------------------------------------ passes
def const_fold(code):
    out, env = [], {}
    for ins in code:
        op = ins[0]
        if op == "label":
            env = {}
            out.append(ins)
            continue
        ins = subst(ins, lambda x: env.get(x, x) if is_var(x) else x)
        op = ins[0]
        if op == "bin" and not is_var(ins[3]) and not is_var(ins[4]):
            ins = ("mov", ins[2], apply_op(ins[1], ins[3], ins[4]))
        elif op == "neg" and not is_var(ins[2]):
            ins = ("mov", ins[1], apply_op("sub", 0, ins[2]))
        elif op == "jz" and not is_var(ins[1]):
            if ins[1] == 0:
                ins = ("jmp", ins[2])
            else:
                continue  # never jumps
        d = dst(ins)
        if d is not None:
            if ins[0] == "mov" and not is_var(ins[2]):
                env[d] = ins[2]
            else:
                env.pop(d, None)
        if ins[0] == "jmp":
            env = {}
        out.append(ins)
    return out


def strength(code):
    out = []
    for ins in code:
        if ins[0] == "bin":
            _, op, d, a, b = ins
            if op in COMM and not is_var(a) and is_var(b):
                a, b = b, a
            if op == "mul" and not is_var(b):
                if b == 0:
                    ins = ("mov", d, 0)
                elif b == 1:
                    ins = ("mov", d, a)
                elif b == -1:
                    ins = ("neg", d, a)
                elif b > 1 and b & (b - 1) == 0 and b <= 2 ** 30:
                    ins = ("bin", "shl", d, a, b.bit_length() - 1)
                else:
                    ins = ("bin", op, d, a, b)
            elif op in ("add", "sub", "shl") and b == 0 and not is_var(b):
                ins = ("mov", d, a)
            elif op == "sub" and is_var(a) and a == b:
                ins = ("mov", d, 0)
            else:
                ins = ("bin", op, d, a, b)
        out.append(ins)
    return out


def copy_prop(code):
    out, copies = [], {}

    def kill(v):
        copies.pop(v, None)
        for k in [k for k, s in copies.items() if s == v]:
            del copies[k]

    for ins in code:
        if ins[0] == "label":
            copies = {}
            out.append(ins)
            continue
        ins = subst(ins, lambda x: copies.get(x, x) if is_var(x) else x)
        d = dst(ins)
        if d is not None:
            if ins[0] == "mov" and ins[2] == d:
                continue  # self copy
            kill(d)
            if ins[0] == "mov" and is_var(ins[2]):
                copies[d] = ins[2]
        if ins[0] == "jmp":
            copies = {}
        out.append(ins)
    return out


def cse(code):
    out, table = [], {}

    def kill(v):
        for k in [k for k, h in table.items() if h == v or v in k[1:]]:
            del table[k]

    for ins in code:
        if ins[0] == "label":
            table = {}
            out.append(ins)
            continue
        d = dst(ins)
        key = None
        if ins[0] == "bin":
            a, b = ins[3], ins[4]
            if ins[1] in COMM and str(a) > str(b):
                a, b = b, a
            key = ("bin:" + ins[1], a, b)
        elif ins[0] == "neg":
            key = ("neg", ins[2])
        if key is not None and key in table and table[key] != d:
            ins = ("mov", d, table[key])
            kill(d)
        else:
            if d is not None:
                kill(d)
            if key is not None and d not in key[1:]:
                table[key] = d
        if ins[0] == "jmp":
            table = {}
        out.append(ins)
    return out


def _references(code):
    refs = {}
    for i, ins in enumerate(code):
        if ins[0] == "jmp":
            refs.setdefault(ins[1], []).append(i)
        elif ins[0] == "jz":
            refs.setdefault(ins[2], []).append(i)
    return refs


def _remove_unreachable(code):
    blocks = split_blocks(code)
    succ = successors(blocks)
    seen, stack = set(), [0] if blocks else []
    while stack:
        b = stack.pop()
        if b in seen:
            continue
        seen.add(b)
        stack.extend(succ[b])
    return [ins for i, b in enumerate(blocks) if i in seen for ins in b]


def _cleanup_jumps(code):
    changed = True
    while changed:
        changed = False
        out = []
        for i, ins in enumerate(code):
            if ins[0] == "jmp" and i + 1 < len(code) and code[i + 1] == ("label", ins[1]):
                changed = True
                continue
            out.append(ins)
        refs = _references(out)
        out2 = [ins for ins in out if not (ins[0] == "label" and ins[1] not in refs)]
        changed = changed or len(out2) != len(out)
        code = out2
    return code


def dce(code):
    code = _remove_unreachable(code)
    while True:
        la = liveness_by_instr(code)
        new = [ins for i, ins in enumerate(code) if dst(ins) is None or dst(ins) in la[i]]
        if len(new) == len(code):
            break
        code = new
    return _cleanup_jumps(code)


def licm(code):
    """Hoist loop-invariant pure instructions out of one loop per call (the driver iterates).
    A loop is a back edge `jmp H` with label H earlier in the code. Instruction `d = f(args)` in the loop
    is hoisted to just before H when: d has exactly one definition in the loop, no argument is defined in
    the loop, d is not live at the loop header (so no iteration reads a pre-loop value) and d is not live
    at any loop exit (so running it when the loop executes zero times is harmless). Every IR operation is
    pure and cannot trap, so executing it speculatively is safe."""
    lab = {ins[1]: i for i, ins in enumerate(code) if ins[0] == "label"}
    refs = _references(code)
    la = None
    for j, ins in enumerate(code):
        if ins[0] != "jmp" or lab.get(ins[1], j + 1) >= j:
            continue
        h = lab[ins[1]]
        if any(not (h <= r <= j) for r in refs[ins[1]]):
            continue  # entered from outside other than by fall-through: leave alone
        if la is None:
            la = liveness_by_instr(code)
        live_header = la[h]
        exit_live = set()
        for r in range(h, j + 1):
            t = code[r]
            target = t[1] if t[0] == "jmp" else t[2] if t[0] == "jz" else None
            if target is not None and not (h <= lab[target] <= j):
                exit_live |= la[lab[target]]
        defcount = {}
        for r in range(h, j + 1):
            d = dst(code[r])
            if d is not None:
                defcount[d] = defcount.get(d, 0) + 1
        hoist = [r for r in range(h + 1, j)
                 if dst(code[r]) is not None
                 and defcount[dst(code[r])] == 1
                 and all(defcount.get(x, 0) == 0 for x in uses(code[r]))
                 and dst(code[r]) not in live_header
                 and dst(code[r]) not in exit_live]
        if hoist:
            hs = set(hoist)
            return code[:h] + [code[r] for r in hoist] + [c for r, c in enumerate(code[h:j + 1], start=h) if r not in hs] + code[j + 1:]
    return code


PASSES = dict(const_fold=const_fold, strength=strength, copy_prop=copy_prop, cse=cse, licm=licm, dce=dce)
DEFAULT_ORDER = ["const_fold", "strength", "copy_prop", "cse", "licm", "dce"]


def optimize(code, passes=DEFAULT_ORDER, max_iter=30):
    """Apply the given passes in order, repeatedly, until the code stops changing."""
    for _ in range(max_iter):
        before = code
        for name in passes:
            code = PASSES[name](code)
        if code == before:
            break
    return code
