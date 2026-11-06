// [Track G] allocator contention benchmark.
// usage: membench <procs> <rounds> <pages>
// Each of <procs> children runs <rounds> times: grow its heap by <pages> pages, then shrink it again.
// Growing/shrinking calls kalloc/kfree once per page. Prints elapsed timer ticks (10 MHz) and the number of
// failed attempts on the physical-allocator lock(s).
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int
main(int argc, char *argv[])
{
  if (argc != 4) {
    fprintf(2, "usage: membench procs rounds pages\n");
    exit(1);
  }
  int procs = atoi(argv[1]), rounds = atoi(argv[2]), pages = atoi(argv[3]);
  uint64 t0 = rdtime(), s0 = kmemspins();
  for (int i = 0; i < procs; i++) {
    int pid = fork();
    if (pid < 0) {
      fprintf(2, "fork failed\n");
      exit(1);
    }
    if (pid == 0) {
      for (int r = 0; r < rounds; r++) {
        if (sbrk(pages * 4096) == (char *)-1) {
          fprintf(2, "sbrk failed\n");
          exit(1);
        }
        sbrk(-pages * 4096);
      }
      exit(0);
    }
  }
  int bad = 0, st;
  for (int i = 0; i < procs; i++) {
    wait(&st);
    if (st != 0) bad++;
  }
  uint64 t1 = rdtime(), s1 = kmemspins();
  printf("RESULT procs=%d rounds=%d pages=%d ticks=%d spins=%d bad=%d\n", procs, rounds, pages,
         (int)(t1 - t0), (int)(s1 - s0), bad);
  exit(0);
}
