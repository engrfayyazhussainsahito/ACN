"""Week 15: WAN Traffic Engineering, MPLS, Overlays and Naming
Run: python3 lab.py"""


# ===== Code lab =====
import math
def waterfill(cap, demands):
    alloc, left = {}, sorted(range(len(demands)), key=lambda i: demands[i])
    for k, i in enumerate(left):
        share = cap / (len(left) - k)
        alloc[i] = min(demands[i], share); cap -= alloc[i]
    return [alloc[i] for i in range(len(demands))]
print("max-min allocation:", waterfill(20, [2, 4, 8, 8]))
print("split 6+6 on 10G paths: utilisation", 6 / 10, "; unsplit: drop", 2 / 12)
for N in (2**10, 2**16, 2**20): print(f"Chord N=2^{int(math.log2(N))}: avg {0.5*math.log2(N):.0f} hops, max {math.log2(N):.0f}")
for h in (0.9, 0.95, 0.99): print(f"DNS hit rate {h:.0%}: mean latency {h*1 + (1-h)*60:.2f} ms")


# ===== Constraint-based shortest path first (CSPF) =====
# A five-node WAN. Plain shortest-path routing sends every demand over the cheapest path and overloads it; CSPF (used by MPLS-TE) prunes links without enough residual capacity before running Dijkstra.
import heapq
edges = {("A", "B"): (1, 10), ("B", "D"): (1, 10), ("A", "C"): (2, 10), ("C", "D"): (2, 10), ("D", "E"): (1, 20)}
cost, cap0 = {}, {}
for (u, v), (c, k) in edges.items(): cost[(u, v)] = cost[(v, u)] = c; cap0[(u, v)] = cap0[(v, u)] = k
def cspf(src, dst, bw, cap):
    pq = [(0, src, [src])]; seen = set()
    while pq:
        d, u, p = heapq.heappop(pq)
        if u == dst: return p
        if u in seen: continue
        seen.add(u)
        for (a, b), c in cost.items():
            if a == u and cap[(a, b)] >= bw and b not in seen: heapq.heappush(pq, (d + c, b, p + [b]))
    return None
demands = [6, 6, 6]                                   # three A->E demands of 6 units
cap = dict(cap0); load = {k: 0 for k in cap0}
print("CSPF:")
for d in demands:
    p = cspf("A", "E", d, cap)
    print("  demand", d, "->", "-".join(p) if p else "BLOCKED")
    if p:
        for a, b in zip(p, p[1:]): cap[(a, b)] -= d; cap[(b, a)] -= d
for d in demands:
    p = cspf("A", "E", 0, cap0)
    for a, b in zip(p, p[1:]): load[(a, b)] += d
print("plain shortest path: all demands on", "-".join(p), "-> utilisation of link A-B:", f"{load[('A','B')]/cap0[('A','B')]:.0%}")


# ===== Chord lookups =====
# Build a Chord ring of N random identifiers in a 16-bit space, give every node finger tables and measure the number of hops for 500 random lookups; compare with ½·log₂N (our count includes the final hop to the successor, so expect about ½·log₂N + 1).
import random, bisect, math
def build(N, m=16, seed=1):
    random.seed(seed); return sorted(random.sample(range(2 ** m), N))
def succ(ids, x, M): return ids[bisect.bisect_left(ids, x % M) % len(ids)]
def lookup(ids, m, start, key):
    M = 2 ** m; n = start; hops = 0
    while True:
        s = succ(ids, n + 1, M)
        if n == s or 0 < (key - n) % M <= (s - n) % M: return hops + 1      # key lies in (n, successor]
        nxt = n
        for i in range(m - 1, -1, -1):                                       # closest preceding finger
            f = succ(ids, n + 2 ** i, M)
            if f != n and 0 < (f - n) % M < (key - n) % M: nxt = f; break
        if nxt == n: return hops + 1
        n = nxt; hops += 1
print("nodes    mean hops   max hops   0.5*log2(N)")
for N in (2 ** 6, 2 ** 8, 2 ** 10, 2 ** 12):
    ids = build(N); rnd = random.Random(2)
    h = [lookup(ids, 16, rnd.choice(ids), rnd.randrange(2 ** 16)) for _ in range(500)]
    print(f"{N:6d} {sum(h)/len(h):10.2f} {max(h):10d} {0.5 * math.log2(N):12.2f}")


# ===== DNS caching: TTL, popularity and latency =====
# 2,000 names with Zipf(1.0) popularity are queried at 1,000 queries/s. A resolver caches each answer for its TTL. Hit ratio and mean latency (1 ms hit, 60 ms miss) for several TTLs.
import random
def dns_hit(ttl, names=2000, alpha=1.0, T=200000, rate=1000.0, seed=1):
    rnd = random.Random(seed); w = [1 / (i + 1) ** alpha for i in range(names)]
    expiry = [-1.0] * names; hits = 0; t = 0.0
    for q in rnd.choices(range(names), w, k=T):
        t += rnd.expovariate(rate)
        if expiry[q] > t: hits += 1
        else: expiry[q] = t + ttl
    return hits / T
print("TTL(s)  hit ratio  mean latency")
for ttl in (1, 10, 60, 300, 3600):
    h = dns_hit(ttl); print(f"{ttl:6d} {h:9.1%} {h * 1 + (1 - h) * 60:9.2f} ms")
