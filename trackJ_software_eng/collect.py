"""Collect per-test line coverage and per-test run time for a pytest suite (Track J)."""
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def test_durations(root, paths):
    """Run the suite without instrumentation and return {module.test_name: seconds}."""
    xml = tempfile.mktemp(suffix=".xml")
    subprocess.run([sys.executable, "-m", "pytest", *paths, "-q", "-p", "no:cacheprovider", "--junitxml", xml, "-W", "ignore"],
                   cwd=root, capture_output=True, text=True)
    out = {}
    for tc in ET.parse(xml).getroot().iter("testcase"):
        mod = tc.get("classname").split(".")[-1]
        out[f"{mod}.{tc.get('name')}"] = float(tc.get("time"))
    return out


def test_coverage(root, paths, source_globs_omit=("*/test_*.py", "*/run_*.py", "*/conftest.py", "*/fuzz.py")):
    """Run the suite under coverage.py with one context per test function; return {test: set((file, line))}.
    Lines executed only outside any test (module import) are not counted."""
    from coverage import CoverageData
    d = tempfile.mkdtemp()
    rc = os.path.join(d, "rc")
    open(rc, "w").write("[run]\ndynamic_context = test_function\ndata_file = %s\nomit =\n%s\n"
                        % (os.path.join(d, ".cov"), "\n".join("    " + g for g in source_globs_omit)))
    subprocess.run([sys.executable, "-m", "coverage", "run", f"--rcfile={rc}", "--source", root, "-m", "pytest", *paths, "-q",
                    "-p", "no:cacheprovider", "-W", "ignore"], cwd=root, capture_output=True, text=True)
    data = CoverageData(os.path.join(d, ".cov"))
    data.read()
    cover = {}
    for f in data.measured_files():
        rel = os.path.relpath(f, root)
        for line, ctxs in data.contexts_by_lineno(f).items():
            for c in ctxs:
                if c:
                    cover.setdefault(c, set()).add((rel, line))
    return cover


def normalise_name(ctx):
    """Context names look like 'test_track_f.test_x'; keep the last two dotted parts."""
    return ".".join(ctx.split(".")[-2:])
