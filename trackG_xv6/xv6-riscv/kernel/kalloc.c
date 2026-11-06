// Physical memory allocator, for user processes,
// kernel stacks, page-table pages,
// and pipe buffers. Allocates whole 4096-byte pages.

#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "spinlock.h"
#include "riscv.h"
#include "defs.h"

void freerange(void *pa_start, void *pa_end);

extern char end[]; // first address after kernel.
                   // defined by kernel.ld.

struct run {
  struct run *next;
};

#ifndef PERCPU_KALLOC
// ---- baseline: one global free list protected by one lock ----
struct {
  struct spinlock lock;
  struct run *freelist;
} kmem;

void
kinit()
{
  initlock(&kmem.lock, "kmem");
  freerange(end, (void *)PHYSTOP);
}

uint64
kmem_spins(void)
{
  return kmem.lock.nspin;
}

void
freerange(void *pa_start, void *pa_end)
{
  char *p;
  p = (char *)PGROUNDUP((uint64)pa_start);
  for (; p + PGSIZE <= (char *)pa_end; p += PGSIZE)
    kfree(p);
}

// Free the page of physical memory pointed at by pa,
// which normally should have been returned by a
// call to kalloc().  (The exception is when
// initializing the allocator; see kinit above.)
void
kfree(void *pa)
{
  struct run *r;

  if (((uint64)pa % PGSIZE) != 0 || (char *)pa < end || (uint64)pa >= PHYSTOP)
    panic("kfree");

  // Fill with junk to catch dangling refs.
  memset(pa, 1, PGSIZE);

  r = (struct run *)pa;

  acquire(&kmem.lock);
  r->next = kmem.freelist;
  kmem.freelist = r;
  release(&kmem.lock);
}

// Allocate one 4096-byte page of physical memory.
// Returns a pointer that the kernel can use.
// Returns 0 if the memory cannot be allocated.
void *
kalloc(void)
{
  struct run *r;

  acquire(&kmem.lock);
  r = kmem.freelist;
  if (r)
    kmem.freelist = r->next;
  release(&kmem.lock);

  if (r)
    memset((char *)r, 5, PGSIZE); // fill with junk
  return (void *)r;
}

#else
// ---- optimisation (Track G): one free list and one lock per CPU, with batch stealing ----
// kfree puts a page on the calling CPU's list; kalloc takes from the calling CPU's list. When the local
// list is empty, kalloc steals up to STEAL_BATCH pages from another CPU. A CPU never holds two of these
// locks at once, so there is no lock-ordering deadlock. Pages are handed out round-robin to the per-CPU
// lists at boot.
#define STEAL_BATCH 16

struct {
  struct spinlock lock;
  struct run *freelist;
} kmem[NCPU];

static char kmem_names[NCPU][8];

void
kinit()
{
  for (int i = 0; i < NCPU; i++) {
    kmem_names[i][0] = 'k'; kmem_names[i][1] = 'm'; kmem_names[i][2] = 'e';
    kmem_names[i][3] = 'm'; kmem_names[i][4] = '0' + (i % 10); kmem_names[i][5] = 0;
    initlock(&kmem[i].lock, kmem_names[i]);
  }
  freerange(end, (void *)PHYSTOP);
}

uint64
kmem_spins(void)
{
  uint64 s = 0;
  for (int i = 0; i < NCPU; i++)
    s += kmem[i].lock.nspin; // approximate: read without the lock, for statistics only
  return s;
}

static void
kfree_to(int id, void *pa)
{
  struct run *r = (struct run *)pa;
  acquire(&kmem[id].lock);
  r->next = kmem[id].freelist;
  kmem[id].freelist = r;
  release(&kmem[id].lock);
}

void
freerange(void *pa_start, void *pa_end)
{
  char *p;
  int i = 0;
  p = (char *)PGROUNDUP((uint64)pa_start);
  for (; p + PGSIZE <= (char *)pa_end; p += PGSIZE) {
    if (((uint64)p % PGSIZE) != 0 || p < end || (uint64)p >= PHYSTOP)
      panic("freerange");
    memset(p, 1, PGSIZE);
    kfree_to(i, p);
    i = (i + 1) % NCPU;
  }
}

void
kfree(void *pa)
{
  if (((uint64)pa % PGSIZE) != 0 || (char *)pa < end || (uint64)pa >= PHYSTOP)
    panic("kfree");

  memset(pa, 1, PGSIZE);

  push_off(); // cpuid() is only stable with interrupts off
  int id = cpuid();
  kfree_to(id, pa);
  pop_off();
}

void *
kalloc(void)
{
  struct run *r;

  push_off();
  int id = cpuid();

  acquire(&kmem[id].lock);
  r = kmem[id].freelist;
  if (r)
    kmem[id].freelist = r->next;
  release(&kmem[id].lock);

  if (!r) {
    // steal a batch from another CPU (own lock is not held while holding the victim's)
    for (int k = 1; k < NCPU && !r; k++) {
      int v = (id + k) % NCPU;
      struct run *chain = 0;
      int n = 0;
      acquire(&kmem[v].lock);
      while (kmem[v].freelist && n < STEAL_BATCH) {
        struct run *x = kmem[v].freelist;
        kmem[v].freelist = x->next;
        x->next = chain;
        chain = x;
        n++;
      }
      release(&kmem[v].lock);
      if (chain) {
        r = chain;
        chain = chain->next;
        acquire(&kmem[id].lock);
        while (chain) {
          struct run *x = chain;
          chain = x->next;
          x->next = kmem[id].freelist;
          kmem[id].freelist = x;
        }
        release(&kmem[id].lock);
      }
    }
  }
  pop_off();

  if (r)
    memset((char *)r, 5, PGSIZE); // fill with junk
  return (void *)r;
}
#endif
