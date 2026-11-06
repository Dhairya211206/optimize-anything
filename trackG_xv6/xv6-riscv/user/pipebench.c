// [Track G] pipe churn: every pipe() allocates a kernel page (kalloc) and every close frees it.
// usage: pipebench <procs> <rounds>
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int
main(int argc, char *argv[])
{
  if (argc != 3) {
    fprintf(2, "usage: pipebench procs rounds\n");
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
      char buf[64];
      for (int r = 0; r < rounds; r++) {
        int fds[2];
        if (pipe(fds) < 0) exit(1);
        memset(buf, r, sizeof(buf));
        if (write(fds[1], buf, sizeof(buf)) != sizeof(buf)) exit(1);
        if (read(fds[0], buf, sizeof(buf)) != sizeof(buf)) exit(1);
        if (buf[0] != (char)r) exit(1);
        close(fds[0]);
        close(fds[1]);
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
