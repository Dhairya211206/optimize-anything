# Track G: xv6 Kernel Optimization, Results

**All timings come from xv6 running under QEMU (software emulation, TCG) on a shared 2-core host.** Guest timer ticks are 10 MHz and are driven by host time, so they are noisy and are **not real-hardware performance**. Where possible the tables also report failed lock attempts ("spins"), which measure contention directly and do not depend on wall-clock. Numbers come from `python trackG_xv6/run_track_g.py` (about 25 minutes) and are in `results/results.json`.

Base: upstream `mit-pdos/xv6-riscv` (commit e93dabe). Our change: `xv6_changes.patch` (unified diff, 20 files, applies cleanly to that commit with `git apply`).

## Two features, two OS concepts

| | Feature 1 | Feature 2 |
|---|---|---|
| OS concept | Synchronization and lock contention in the physical-page allocator | CPU scheduling policy |
| Stock behavior | One global free list guarded by one spinlock (`kmem.lock`) | Round-robin: scan the process table, run the next RUNNABLE process |
| Change | Per-CPU free lists with batch stealing (`-DPERCPU_KALLOC`) | Lottery scheduler with `settickets()` system call (`-DLOTTERY_SCHED`) |
| Objective | Cut contention on `kalloc`/`kfree` as CPU count grows, without losing memory | CPU share proportional to tickets, i.e. proportional-share fairness |
| Honest outcome | Contention eliminated (failed lock attempts to 0); **no measurable wall-clock gain** | Shares track tickets much better than round-robin; **worse than round-robin when tickets are equal** |

### Feature 1 design (`kernel/kalloc.c`)
- `kmem[NCPU]`, each with its own lock and list. Pages are distributed round-robin among CPUs at boot. `kfree` returns a page to the current CPU's list (with interrupts off via `push_off`); `kalloc` takes from the local list and, if empty, steals up to `STEAL_BATCH` = 16 pages from other CPUs.
- **Deadlock avoidance:** a CPU never holds two `kmem` locks at once. It takes the victim's lock, detaches a batch into a local chain, releases it, then takes its own lock to splice the chain in. No lock ordering is needed because there is no nested locking.
- **No memory lost:** `memfull` (how many pages one process can obtain) gives 32,469 on both kernels.

### Feature 2 design (`kernel/proc.c`)
- Each process has `tickets` (default 1, inherited across `fork`). `scheduler()` sums tickets of RUNNABLE processes, draws a winner with an xorshift generator under `lottery_lock`, and runs the owner of the winning ticket. New syscalls: `settickets(n)`, plus instrumentation syscalls `rdtime` (23) and `kmemspins` (24).
- For the scheduler comparison the timer slice is shortened to 2 ms in **both** kernels (`base_t` and `lottery`, `-DTIMER_INTERVAL=20000`), otherwise a share measurement takes too long. So `base_t`, not `base`, is the baseline for feature 2.

### Instrumentation (present in all builds)
`spinlock.c` counts failed `amoswap` attempts per acquire and adds them to `lk->nspin`; `kmemspins` reads the allocator lock's counter. This adds a small overhead identically to both kernels.

## Correctness

| Kernel | `usertests -q` | `memfull` pages |
|---|---|---|
| base | ALL TESTS PASSED | 32,469 |
| opt (per-CPU allocator) | ALL TESTS PASSED | 32,469 |
| base_t (short timer) | ALL TESTS PASSED | n/a |
| lottery | ALL TESTS PASSED | n/a |

Logs: `results/usertests_*.log`. All four kernels boot and pass.

## Feature 1 results (3 CPUs unless noted, ticks = guest timer ticks, mean ± std over 20 runs)

New user programs: `membench` (processes repeatedly allocate and free pages via `sbrk`), `forkbench` (fork/exit loops), `pipebench` (pipe traffic, which allocates pipe pages). Arguments are processes and rounds (and pages for membench).

| Workload | Base ticks | Opt ticks | Difference | Failed lock attempts base | opt |
|---|---|---|---|---|---|
| membench 1 300 64 | 3.31M ± 0.45M | 3.47M ± 0.36M | within noise | 0 | 0 |
| membench 3 300 64 | 5.93M ± 0.29M | 5.93M ± 0.58M | none | 503,874 | **0** |
| membench 8 100 64 | 5.12M ± 0.49M | 5.11M ± 0.50M | none | 568,610 | **0** |
| forkbench 3 40 | 0.91M ± 0.25M | 0.88M ± 0.21M | within noise | 120 | 0 |
| forkbench 8 20 | 1.20M ± 0.26M | 1.28M ± 0.23M | within noise | 18,712 | 0 |
| pipebench 3 400 | 3.65M ± 0.39M | 3.40M ± 0.31M | -7%, about 1 std | 7,171 | 0 |
| pipebench 8 150 | 3.63M ± 0.21M | 3.70M ± 0.34M | within noise | 17,291 | 0 |
| membench 3 300 64, 1 CPU (control) | 9.69M ± 0.57M | 9.83M ± 0.84M | within noise | 0 | 0 |

**Reading:** the mechanism works, lock contention disappears in every multi-CPU workload. But the run time does not measurably improve, because in these benchmarks the time is dominated by zeroing and touching pages outside the lock, and by noisy emulated timing (std 8 to 15% of the mean). We therefore **do not claim a speedup from feature 1**. The correct claim is: contention removed, performance neutral under this emulator, memory capacity unchanged. Real multicore hardware, where cache-line bouncing on a shared lock is costly, might behave differently; this was not tested.

## Feature 2 results (1 CPU, 500-tick runs, 15 runs per row, mean CPU share in %)

Mean absolute error = average over the three processes of |measured share - ideal share|, in percentage points.

| Tickets | Ideal share | Round-robin (`base_t`) | Lottery | RR error | Lottery error |
|---|---|---|---|---|---|
| 1, 1, 1 | 33/33/33 | 32.8 / 34.0 / 33.1 | 34.0 / 35.4 / 30.5 | **0.6** | 2.5 |
| 1, 2, 4 | 14.3 / 28.6 / 57.1 | about 33 each | 14.0 / 28.6 / 57.2 | 15.9 | **1.2** |
| 10, 20, 70 | 10 / 20 / 70 | about 33 each | 10.7 / 19.6 / 69.6 | 24.5 | **2.6** |

**Reading:** round-robin cannot express priorities and ignores tickets; lottery follows them to within about 1 to 3 points. With equal tickets, round-robin is fairer (0.6 vs 2.5 points) because lottery is random and has variance. Lottery also has a per-decision cost (a pass over the process table plus random draw) that was not separately measured.

## A benchmark artifact that we caught

The first feature-2 run (kept in `results/results_first_run.json`) gave 61.9% for a 70-ticket process and an error of 6.1 points. The cause was the benchmark, not the scheduler: the 1-ticket parent forked children slowly, so the 70-ticket child started late and had less time. The fixed `schedbench` makes every child block on a pipe, then has the parent release them together with a shared absolute deadline. The corrected result is 69.6%. (Failure Log entry 11.)

## Limits

- QEMU TCG emulation, 2 host cores, 3 or 8 guest harts. Not hardware.
- The contention counter measures failed lock attempts, not time lost.
- Feature 2 changes the timer slice for both kernels; results do not apply to the default slice.
- Lottery scheduling is probabilistic; short runs have variance. No starvation proof is offered beyond the random draw.
- Only two kernel variants tested per feature, three or more workloads for feature 1, three ticket configurations for feature 2.

## Reproduce

```
bash trackG_xv6/build.sh                    # builds variants into /tmp/xv6-{base,opt,base_t,lottery}
python3 trackG_xv6/run_track_g.py correctness feature1 feature2
# or manually: cd trackG_xv6/xv6-riscv && make qemu CPUS=3 XCFLAGS=-DPERCPU_KALLOC
git apply trackG_xv6/xv6_changes.patch      # onto upstream xv6-riscv commit e93dabe
```
Needs `qemu-system-riscv64` and the RISC-V gcc toolchain.
