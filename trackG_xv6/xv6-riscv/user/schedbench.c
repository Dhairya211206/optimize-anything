// [Track G] proportional-share benchmark for the scheduler.
// usage: schedbench <tickets1> <tickets2> <tickets3> <duration_ticks>
// Three CPU-bound children each call settickets() and then block on a "go" pipe. Once all three exist, the parent sends every
// child the same absolute deadline (now + duration timer ticks); each child counts loop iterations until that deadline and
// reports its count. A child only counts while it is running, so its count is proportional to the CPU time it received.
// (An earlier version let each child time itself from its own start; the one-ticket parent then forked the children slowly
// and the last child started late, which biased the shares. The common deadline removes that artefact.)
// With a lottery scheduler the shares should follow the ticket ratio; with the stock round-robin scheduler they stay near 1/3.
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int
main(int argc, char *argv[])
{
  if (argc != 5) {
    fprintf(2, "usage: schedbench t1 t2 t3 duration\n");
    exit(1);
  }
  int dur = atoi(argv[4]);
  int res[3][2], go[3][2];
  for (int i = 0; i < 3; i++) {
    pipe(res[i]);
    pipe(go[i]);
    int pid = fork();
    if (pid == 0) {
      settickets(atoi(argv[1 + i]));
      uint deadline;
      read(go[i][0], &deadline, sizeof(deadline));
      uint64 count = 0;
      while (uptime() < deadline)
        count++;
      write(res[i][1], &count, sizeof(count));
      exit(0);
    }
  }
  uint deadline = uptime() + dur;
  for (int i = 0; i < 3; i++)
    write(go[i][1], &deadline, sizeof(deadline));
  uint64 c[3];
  for (int i = 0; i < 3; i++) {
    read(res[i][0], &c[i], sizeof(uint64));
    wait(0);
  }
  uint64 tot = c[0] + c[1] + c[2];
  printf("SHARE %d %d %d permille %d %d %d\n", atoi(argv[1]), atoi(argv[2]), atoi(argv[3]), (int)(c[0] * 1000 / tot),
         (int)(c[1] * 1000 / tot), (int)(c[2] * 1000 / tot));
  exit(0);
}
