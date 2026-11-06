"""Mini language front end (Track F): lexer, parser, reference AST interpreter, and three-address IR generation.

Language: 32-bit signed integers, variables default to 0.
  stmt := id = expr ; | print expr ; | while ( expr ) { stmt* } | if ( expr ) { stmt* } [ else { stmt* } ]
  expr := add [ (< | == | !=) add ] ; add := mul ((+|-) mul)* ; mul := unary (* unary)* ; unary := - unary | primary
All arithmetic wraps to 32 bits. '#' starts a comment.

IR (list of tuples; operands are int constants or variable-name strings; temporaries are named '%tN'):
  ('bin', op, d, a, b)  op in add sub mul lt eq ne shl      ('neg', d, a)      ('mov', d, a)
  ('print', a)          ('label', L)      ('jmp', L)        ('jz', a, L)  # jump if a == 0
"""
import re

KEYWORDS = {"while", "if", "else", "print"}
OPNAME = {"+": "add", "-": "sub", "*": "mul", "<": "lt", "==": "eq", "!=": "ne"}
TOKEN = re.compile(r"\s*(?:(\d+)|([A-Za-z_]\w*)|(==|!=|[-+*<(){}=;]))")


def wrap32(x):
    return ((x + 2 ** 31) % 2 ** 32) - 2 ** 31


def apply_op(op, a, b):
    if op == "add":
        return wrap32(a + b)
    if op == "sub":
        return wrap32(a - b)
    if op == "mul":
        return wrap32(a * b)
    if op == "lt":
        return int(a < b)
    if op == "eq":
        return int(a == b)
    if op == "ne":
        return int(a != b)
    if op == "shl":
        return wrap32(a << b)
    raise ValueError(op)


def tokenize(src):
    src = re.sub(r"#.*", "", src).rstrip()
    pos, toks = 0, []
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:
            raise SyntaxError(f"bad character near {src[pos:pos + 12]!r}")
        pos = m.end()
        if m.group(1) is not None:
            toks.append(("num", int(m.group(1))))
        elif m.group(2) is not None:
            toks.append(("kw" if m.group(2) in KEYWORDS else "id", m.group(2)))
        else:
            toks.append(("op", m.group(3)))
    return toks


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("eof", None)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, kind, val=None):
        tok = self.next()
        if tok[0] != kind or (val is not None and tok[1] != val):
            raise SyntaxError(f"expected {val or kind}, got {tok}")
        return tok

    def program(self):
        out = []
        while self.peek()[0] != "eof":
            out.append(self.stmt())
        return out

    def block(self):
        self.expect("op", "{")
        out = []
        while self.peek() != ("op", "}"):
            if self.peek()[0] == "eof":
                raise SyntaxError("unterminated block")
            out.append(self.stmt())
        self.expect("op", "}")
        return out

    def stmt(self):
        k, v = self.peek()
        if k == "kw" and v == "print":
            self.next(); e = self.expr(); self.expect("op", ";")
            return ("print", e)
        if k == "kw" and v == "while":
            self.next(); self.expect("op", "("); c = self.expr(); self.expect("op", ")")
            return ("while", c, self.block())
        if k == "kw" and v == "if":
            self.next(); self.expect("op", "("); c = self.expr(); self.expect("op", ")")
            then = self.block()
            els = []
            if self.peek() == ("kw", "else"):
                self.next(); els = self.block()
            return ("if", c, then, els)
        if k == "id":
            self.next(); self.expect("op", "="); e = self.expr(); self.expect("op", ";")
            return ("assign", v, e)
        raise SyntaxError(f"unexpected token {self.peek()}")

    def expr(self):
        left = self.add()
        if self.peek()[0] == "op" and self.peek()[1] in ("<", "==", "!="):
            op = self.next()[1]
            left = ("bin", OPNAME[op], left, self.add())
        return left

    def add(self):
        left = self.mul()
        while self.peek()[0] == "op" and self.peek()[1] in ("+", "-"):
            op = self.next()[1]
            left = ("bin", OPNAME[op], left, self.mul())
        return left

    def mul(self):
        left = self.unary()
        while self.peek() == ("op", "*"):
            self.next()
            left = ("bin", "mul", left, self.unary())
        return left

    def unary(self):
        if self.peek() == ("op", "-"):
            self.next()
            return ("neg", self.unary())
        return self.primary()

    def primary(self):
        k, v = self.next()
        if k == "num":
            return ("num", v)
        if k == "id":
            return ("var", v)
        if (k, v) == ("op", "("):
            e = self.expr(); self.expect("op", ")")
            return e
        raise SyntaxError(f"unexpected token {(k, v)}")


def parse(src):
    return Parser(tokenize(src)).program()


# ---------------------------------------------------------------- reference interpreter (on the AST)
def interpret(ast, step_limit=500_000):
    env, out, steps = {}, [], [0]

    def tick():
        steps[0] += 1
        if steps[0] > step_limit:
            raise RuntimeError("step limit")

    def ev(e):
        tick()
        if e[0] == "num":
            return wrap32(e[1])
        if e[0] == "var":
            return env.get(e[1], 0)
        if e[0] == "neg":
            return wrap32(-ev(e[1]))
        return apply_op(e[1], ev(e[2]), ev(e[3]))

    def run(stmts):
        for s in stmts:
            tick()
            if s[0] == "assign":
                env[s[1]] = ev(s[2])
            elif s[0] == "print":
                out.append(ev(s[1]))
            elif s[0] == "while":
                while ev(s[1]) != 0:
                    run(s[2])
            else:
                run(s[2] if ev(s[1]) != 0 else s[3])

    run(ast)
    return out


# ---------------------------------------------------------------- IR generation
class CodeGen:
    def __init__(self):
        self.code, self.nt, self.nl = [], 0, 0

    def temp(self):
        self.nt += 1
        return f"%t{self.nt}"

    def label(self):
        self.nl += 1
        return f"L{self.nl}"

    def expr(self, e):
        if e[0] == "num":
            return wrap32(e[1])
        if e[0] == "var":
            return e[1]
        if e[0] == "neg":
            a = self.expr(e[1]); d = self.temp()
            self.code.append(("neg", d, a))
            return d
        a, b = self.expr(e[2]), self.expr(e[3])
        d = self.temp()
        self.code.append(("bin", e[1], d, a, b))
        return d

    def stmts(self, ss):
        for s in ss:
            if s[0] == "assign":
                v = self.expr(s[2])
                self.code.append(("mov", s[1], v))
            elif s[0] == "print":
                self.code.append(("print", self.expr(s[1])))
            elif s[0] == "while":
                l1, l2 = self.label(), self.label()
                self.code.append(("label", l1))
                c = self.expr(s[1])
                self.code.append(("jz", c, l2))
                self.stmts(s[2])
                self.code.append(("jmp", l1))
                self.code.append(("label", l2))
            else:
                le, lend = self.label(), self.label()
                c = self.expr(s[1])
                self.code.append(("jz", c, le))
                self.stmts(s[2])
                self.code.append(("jmp", lend))
                self.code.append(("label", le))
                self.stmts(s[3])
                self.code.append(("label", lend))


def compile_ast(ast):
    g = CodeGen()
    g.stmts(ast)
    return g.code


def compile_source(src):
    return compile_ast(parse(src))
