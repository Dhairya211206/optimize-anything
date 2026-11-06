// [Track G] fork/exit churn: every fork allocates a page table, a trapframe page and copies memory (kalloc/kfree heavy).
// usage: forkbench <procs> <rounds>
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int
main(int argc, char *argv[])
{
  if (argc != 3) {
    fprintf(2, "usage: forkbench procs rounds\n");
    exit(1);
  }
  int procs = atoi(argv[1]), rounds = atoi(argv[2]);
  uint64 t0 = rdtime(), s0 = kmemspins();
  for (int i = 0; i < procs; i++) {
    int pid = fork();
    if (pid < 0) {
      fprintf(2, "fork failed\n");
      exit(1);
    }
    if (pid == 0) {
      for (int r = 0; r < rounds; r++) {
        int c = fork();
        if (c < 0) exit(1);
        if (c == 0) exit(0);
        wait(0);
      }
      exit(0);
    }
  }
  int bad = 0, st;
  for (int i = 0; i < procs; i++) {
    wait(&st);
    if (st != 0) bad++;
  }
  printf("RESULT procs=%d rounds=%d pages=0 ticks=%d spins=%d bad=%d\n", procs, rounds, (int)(rdtime() - t0), (int)(kmemspins() - s0), bad);
  exit(0);
}
