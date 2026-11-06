// [Track G] correctness check for the allocator: how many pages can ONE process obtain before sbrk fails?
// With per-CPU free lists this only equals the baseline if stealing really reaches every CPU's list.
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int
main(void)
{
  int n = 0;
  while (sbrk(4096) != (char *)-1)
    n++;
  sbrk(-n * 4096);
  printf("RESULT pages=%d\n", n);
  exit(0);
}
