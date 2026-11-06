#!/bin/bash
# Build every kernel variant from one source tree into /tmp/xv6-<variant>.
#   base     stock allocator, stock scheduler, stock 0.1 s timer slice
#   opt      + per-CPU allocator (feature 1)
#   base_t   stock allocator and scheduler, timer slice shortened to 2 ms (the baseline for feature 2)
#   lottery  + lottery scheduler, 2 ms timer slice (feature 2)
set -e
SRC="$(cd "$(dirname "$0")/xv6-riscv" && pwd)"
declare -A FLAGS=( [base]="" [opt]="-DPERCPU_KALLOC" [base_t]="-DTIMER_INTERVAL=20000" [lottery]="-DTIMER_INTERVAL=20000 -DLOTTERY_SCHED" )
for v in base opt base_t lottery; do
  rm -rf /tmp/xv6-$v; cp -r "$SRC" /tmp/xv6-$v
  (cd /tmp/xv6-$v && make clean >/dev/null 2>&1; rm -f user/usys.S; make TOOLPREFIX=riscv64-linux-gnu- XCFLAGS="${FLAGS[$v]}" kernel/kernel fs.img >/tmp/build-$v.log 2>&1 && echo "built $v") || { tail -20 /tmp/build-$v.log; exit 1; }
done
