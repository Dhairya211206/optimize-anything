"""Virtual machine for the IR with execution profiling (Track F).

Cost model (an ASSUMPTION, not a hardware measurement): every executed instruction costs 1 cycle except
`mul`, which costs 3. Labels cost 0. The dynamic instruction count is exact for the VM; the weighted cost
depends on the assumed weights.
"""
from frontend import apply_op, wrap32

MUL_COST = 3


def run(code, step_limit=3_000_000):
    labels = {ins[1]: i for i, ins in enumerate(code) if ins[0] == "label"}
    env, out = {}, []
    counts = [0] * len(code)
    pc, dyn, cost = 0, 0, 0
    val = lambda x: env.get(x, 0) if isinstance(x, str) else x
    n = len(code)
    while pc < n:
        ins = code[pc]
        op = ins[0]
        if op == "label":
            pc += 1
            continue
        counts[pc] += 1
        dyn += 1
        if dyn > step_limit:
            raise RuntimeError("step limit")
        cost += MUL_COST if (op == "bin" and ins[1] == "mul") else 1
        if op == "bin":
            env[ins[2]] = apply_op(ins[1], val(ins[3]), val(ins[4]))
        elif op == "neg":
            env[ins[1]] = wrap32(-val(ins[2]))
        elif op == "mov":
            env[ins[1]] = val(ins[2])
        elif op == "print":
            out.append(val(ins[1]))
        elif op == "jmp":
            pc = labels[ins[1]]
            continue
        elif op == "jz":
            if val(ins[1]) == 0:
                pc = labels[ins[2]]
                continue
        pc += 1
    return dict(out=out, dyn=dyn, cost=cost, counts=counts)


def static_count(code):
    return sum(1 for i in code if i[0] != "label")
