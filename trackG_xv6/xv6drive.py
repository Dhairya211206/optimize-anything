"""Drive an xv6 build under QEMU: boot, type shell commands, wait for the shell prompt after each, return the console log.
usage: python xv6drive.py <built-xv6-dir> <cpus> <per-command-timeout-s> "<cmd1>" "<cmd2>" ...
Everything printed comes from the xv6 console; QEMU runs headless (make qemu)."""
import os
import signal
import subprocess
import sys
import threading
import time


def run(cmds, cwd, cpus=3, timeout=120):
    p = subprocess.Popen(f"make TOOLPREFIX=riscv64-linux-gnu- CPUS={cpus} qemu", shell=True, cwd=cwd, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=0, start_new_session=True)
    buf = []

    def reader():
        while True:
            c = p.stdout.read(1)
            if not c:
                break
            buf.append(c)

    threading.Thread(target=reader, daemon=True).start()
    t0 = time.time()
    while time.time() - t0 < 60 and "$ " not in "".join(buf[-200:]):
        time.sleep(0.1)
    for c in cmds:
        n = len(buf)
        p.stdin.write(c + "\n")
        p.stdin.flush()
        t0 = time.time()
        while time.time() - t0 < timeout:
            s = "".join(buf[n:])
            if s.rstrip().endswith("$") and len(s) > len(c) + 3:
                break
            time.sleep(0.2)
    out = "".join(buf)
    os.killpg(p.pid, signal.SIGKILL)
    return out


if __name__ == "__main__":
    print(run(sys.argv[4:], sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
