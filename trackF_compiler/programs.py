"""Benchmark programs in the mini language (Track F)."""
PROGRAMS = {
    "sumsq_invariant": """
        n = 200; s = 0; i = 0; k = 3;
        while (i < n) { c = k * 8 + 2 * 5; s = s + i * i + c; i = i + 1; }
        print s;""",
    "repeated_subexpr": """
        x = 7; acc = 0; i = 0;
        while (i < 100) { t = x * x; u = x * x; acc = acc + t * 3 + u * 4 + i * 16; i = i + 1; }
        print acc;""",
    "nested_loops": """
        n = 30; m = 30; total = 0; i = 0;
        while (i < n) { j = 0; base = i * 64;
          while (j < m) { total = total + base + j * 4 + n * m; j = j + 1; }
          i = i + 1; }
        print total;""",
    "fib_dead_code": """
        a = 0; b = 1; i = 0; dead = 0;
        while (i < 40) { t = a + b; a = b; b = t; dead = dead + i * 5; unused = a * a; i = i + 1; }
        print a;""",
    "constant_chain": """
        a = 2 + 3; b = a * 4; c = b - a * 4 + 7; d = c * c; e = d * 1 + 0; f = e * 8;
        print f; print a + b + c;""",
    "branchy": """
        i = 0; odds = 0; w = 0;
        while (i < 60) {
          r = i - i * 1;
          if (i < 30) { w = w + i * 2; } else { w = w + i * 4; }
          if (i == 10) { odds = odds + 1; }
          i = i + 1; }
        print w; print odds;""",
    "register_pressure": """
        a = 1; b = 2; c = 3; d = 4; e = 5; f = 6; g = 7; h = 8; i = 0;
        while (i < 50) { a = a + b; b = b + c; c = c + d; d = d + e; e = e + f; f = f + g; g = g + h; h = h + a; i = i + 1; }
        print a + b + c + d + e + f + g + h;""",
}
