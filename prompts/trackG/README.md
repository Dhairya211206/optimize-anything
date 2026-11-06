# Track G: xv6 Operating-System Optimization — Prompt Log

**Tool:** Claude (claude.ai), Claude Sonnet 5.5 | **Date:** 2026-11-04  
**Track Focus:** Kernel Memory Contention Reduction, Proportional Share CPU Scheduling, QEMU Benchmarking, and System Stability

---

## Generic Specification Prompt (Assignment 8 Framework)

```markdown
You are an expert operating systems kernel engineer and systems optimization researcher. Implement Track G (xv6 Operating-System Optimization) of Assignment 8 following the mandatory Section 8 vibe-coding methodology.

1. System Context & Target OS:
   - Target System: MIT xv6 teaching operating system (RISC-V architecture) running under QEMU multi-core emulation.
   - Core Problem: The stock xv6 kernel employs coarse-grained global locking and a simple round-robin scheduler, leading to high spinlock contention during concurrent memory allocations and lack of proportional CPU allocation.

2. Kernel Features to Implement (Two Features for Full Credit):
   - Feature 1: Scalable Per-CPU Page Allocator (`kernel/kalloc.c`):
     * Replace the single global `kmem.freelist` and its contention-heavy global spinlock with dedicated per-CPU freelists (`kmem[NCPU]`).
     * Implement batch page stealing: when a CPU freelist is depleted, steal a batch of 32 physical pages from another CPU's freelist, holding the target lock only during the batch transfer.
     * Maintain global memory accounting and support total physical exhaustion without leaking pages.
   - Feature 2: Proportional-Share Lottery Scheduler (`kernel/proc.c`):
     * Replace round-robin process scheduling with a Lottery Scheduler.
     * Add `settickets(int tickets)` system call allowing processes to allocate ticket weights.
     * On each timer interrupt or scheduling tick, pick a winning ticket uniformly at random in [1, total_tickets] and context-switch to the corresponding RUNNABLE process.

3. Benchmark Harness & User-Space Tests:
   - Write comprehensive user-space benchmarks:
     * `membench`: Spawns multiple concurrent worker processes repeatedly allocating and freeing 4 KB pages to measure lock contention and allocation throughput.
     * `schedbench`: Spawns competing child processes with ticket ratios (e.g., 30:20:10) to verify proportional CPU timeshare and fairness.
     * `forkbench` & `pipebench`: Verify IPC and process creation throughput.
     * `memfull`: Verifies that physical memory bounds and out-of-memory handling remain identical to stock xv6.

4. Verification & Testing:
   - Mandatory Stability Checks:
     * Kernel must cleanly compile with zero warnings under `riscv64-unknown-elf-gcc`.
     * xv6 must cleanly boot and successfully pass the complete `usertests -q` test suite across all 4 kernel variants.
     * Generate a unified, clean patch file (`xv6_changes.patch`) applicable to pristine upstream xv6-riscv.

5. Fair Benchmarking & Critical Review:
   - Compare stock xv6 vs optimized xv6 under multi-core QEMU (CPUS=3 and CPUS=4).
   - Report: Wall-clock completion time, CPU cycle distribution, ticket fairness ratio, and lock wait times.
   - Rigorously discuss system performance: explain that while lock contention is eliminated (failed acquisitions drop from ~500k to 0), wall-clock run time is unchanged within noise because physical page zeroing (memset) occurs outside the lock and dominates allocation latency, alongside noisy QEMU timing emulation.
```

---

## Session Execution Summary

* **Scaffolding:** Developed kernel modifications (`kalloc.c`, `proc.c`, `sysproc.c`, `syscall.c`, `defs.h`), user benchmarks (`membench`, `schedbench`, `forkbench`, `pipebench`, `memfull`), automated Python test runner `run_track_g.py`, and `xv6_changes.patch`.
* **Revisions during session:**
  1. Fixed missing function declarations in `defs.h` and regenerated `usys.S` syscall stubs.
  2. Redesigned `schedbench` to synchronize child start times via shared pipe barriers, eliminating initialization skew from staggered forks (Failure Log #11).
  3. Honestly reported that lock contention was eliminated with no measurable wall-clock gain due to out-of-lock page zeroing and QEMU noise; lottery scheduling ticket proportionality succeeded with high accuracy (69.6% for 70% share).

---

## Verification Note

* **xv6 boots and passes `usertests -q`** across all four kernel configurations.
* `memfull` confirms exact physical page conservation (zero page leakage).
* Clean patch `xv6_changes.patch` applies cleanly to upstream xv6 repository commit `eeb7b41`.
