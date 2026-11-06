// Mutual exclusion lock.
struct spinlock {
  uint locked; // Is the lock held?
  uint64 nspin; // [Track G instrumentation] failed lock attempts, updated while holding the lock

  // For debugging:
  char *name;      // Name of lock.
  struct cpu *cpu; // The cpu holding the lock.
};
