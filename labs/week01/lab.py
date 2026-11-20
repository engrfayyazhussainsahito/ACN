"""Week 1: Internet Architecture and Design Principles
Run: python3 lab.py"""


# ===== Code lab =====
def transfer(M, L, N, R, packets=True):
    P = -(-M // L)
    return (N + P - 1) * L / R if packets else N * M / R
M = 10e6 * 8
print("whole message:", transfer(M, 1500 * 8, 5, 100e6, False), "s")
print("packetised   :", round(transfer(10_000_000, 1500, 5, 100e6 / 8), 3), "s")
print("BDP 1 Gb/s, 80 ms:", 1e9 * 0.08 / 8 / 1e6, "MB")

def goodput(mtu=1500, ip=20, l4=20, wire=38): return (mtu - ip - l4) / (mtu + wire)
print(f"IPv4/TCP {goodput():.1%}   IPv6/TCP {goodput(ip=40):.1%}   jumbo {goodput(9000):.1%}")
print("1-byte payload:", f"{1 / (46 + 38):.1%}")


# ===== A packet pipeline simulator =====
# Simulate store-and-forward over N equal links and compare with the closed-form (N+P−1)·L/R + N·prop. Then see which delay component dominates as the link gets faster.
def pipeline(P, L, N, R, prop):
    free = [0.0] * N; done = 0.0          # free[h]: when link h can start its next packet
    for p in range(P):
        t = 0.0                           # all packets are ready at the source at t = 0
        for h in range(N):
            start = max(t, free[h]); free[h] = start + L / R; t = start + L / R + prop
        done = max(done, t)
    return done
M, L, N = 10e6 * 8, 1500 * 8, 5
P = int(M // L) + (M % L > 0)
print("packets:", P)
for R in (1e6, 1e9, 100e9):
    sim = pipeline(P, L, N, R, 0.005)
    tx = (N + P - 1) * L / R
    print(f"R={R:8.0e} b/s  simulated {sim:9.4f} s  formula {tx + N * 0.005:9.4f} s  transmission share {tx / sim:6.1%}")


# ===== Statistical multiplexing and network calculus =====
# How many bursty users can share a link, and what worst-case delay does a token-bucket flow see through a rate-latency server?
from math import comb
n, p, cap = 35, 0.1, 10
tail = sum(comb(n, k) * p**k * (1 - p)**(n - k) for k in range(cap + 1, n + 1))
print(f"{n} users active {p:.0%} of the time on a link that fits {cap}: P(overload) = {tail:.4%}")
print("circuit switching would admit only", cap, "users")
sigma, rho, R, T = 80_000, 5e6, 10e6, 0.001      # burst (bits), rate (b/s), service rate, latency (s)
print("delay bound   :", round((T + sigma / R) * 1000, 2), "ms")
print("backlog bound :", round((sigma + rho * T) / 8), "bytes")
