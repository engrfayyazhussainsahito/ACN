"""Week 7: Data Center Networks
Run: python3 lab.py"""


# ===== Code lab =====
def fat_tree(k): return dict(hosts=k**3 // 4, switches=5 * k * k // 4, core_paths=(k // 2) ** 2)
for k in (4, 16, 48, 64): print(k, fat_tree(k))

print("oversubscription 48x10G / 4x40G =", (48 * 10) / (4 * 40), ":1")
resp, n, buf = 32e3, 40, 128e3
print(f"incast burst {n*resp/1e6:.2f} MB vs buffer {buf/1e3:.0f} KB -> {1 - buf/(n*resp):.0%} overflow")
print("RTO/RTT mismatch:", 0.2 / 100e-6)


# ===== ECMP hash collisions =====
# Hash n equal-rate flows uniformly onto 8 equal-cost links 2,000 times. The busiest link determines completion time, so compare the mean maximum load with the perfectly balanced load n/8.
import random, collections
def ecmp_max(flows, links, trials=2000, seed=1):
    random.seed(seed); tot = 0
    for _ in range(trials):
        c = collections.Counter(random.randrange(links) for _ in range(flows))
        tot += max(c.values())
    return tot / trials
print("flows  ideal  mean max load  overload factor")
for f in (8, 32, 128, 1024, 8192):
    m = ecmp_max(f, 8); print(f"{f:5d} {f/8:6.1f} {m:11.1f} {m/(f/8):12.2f}x")


# ===== TCP incast collapse =====
# N servers each return a 32 KB block through one 10 Gb/s port with a 128 KB buffer (about 85 packets). If the synchronised burst exceeds buffer + BDP, a loss occurs and the stalled flows wait for the minimum retransmission timeout.
def incast(N, rto, block=32_000, mss=1460, buf=85, rtt=100e-6, rate=10e9):
    pk = -(-block // mss) * N
    bdp_pk = rate * rtt / 8 / mss
    t = rtt + pk * mss * 8 / rate
    if pk > buf + bdp_pk: t += rto                      # overflow -> loss -> RTO stall
    return N * block * 8 / t / 1e9                      # goodput in Gb/s
print("servers  RTO=200ms  RTO=1ms")
for N in (2, 4, 6, 8, 16, 32, 64): print(f"{N:7d} {incast(N, 0.2):9.3f} {incast(N, 0.001):9.3f}  Gb/s")
print("tail at scale: P(at least one of 100 backends slow) with p99/p99.9 =", f"{1 - 0.99**100:.1%} / {1 - 0.999**100:.1%}")
