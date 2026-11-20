"""Week 5: Congestion Control II: BBR, Delay-Based and Modelling
Run: python3 lab.py"""


# ===== Code lab =====
from math import sqrt
def mathis(mss=1460, rtt=0.1, p=1e-4): return 1.22 * mss * 8 / rtt / sqrt(p) / 1e6
for rtt in (0.02, 0.1, 0.2): print(f"RTT {rtt*1000:>3.0f} ms  p=1e-4 -> {mathis(rtt=rtt):6.1f} Mb/s")
print("loss needed for 1 Gb/s at 100 ms: %.1e" % ((1.22 * 1460 * 8 / 0.1 / 1e9) ** 2))

bw, rt = 50e6, 0.08
bdp = bw * rt / 8
print(f"BDP = {bdp/1e3:.0f} KB, BBR inflight cap = {2*bdp/1e6:.1f} MB = {2*bdp/1460:.0f} packets")
import math; print("Startup gain 2/ln2 =", round(2 / math.log(2), 3))


# ===== Buffer size versus utilisation and delay =====
# One Reno flow fills a bottleneck of 400-packet BDP. Sweep the buffer size B and measure link utilisation and the average queueing delay (queue ÷ capacity, capacity = 4000 packets/s).
def reno_buffer(bdp, B, steps=30000):
    W = bdp / 2; util = qsum = 0.0
    for _ in range(steps):
        q = min(B, max(0.0, W - bdp))            # standing queue when window exceeds the pipe
        util += min(1.0, W / bdp); qsum += q
        W += 1                                   # additive increase, once per RTT
        if W - bdp > B: W /= 2                   # buffer overflow -> loss -> halve
    return util / steps, qsum / steps
bdp, C = 400, 4000
print("buffer(xBDP)  utilisation  mean queue delay")
for f in (0.1, 0.25, 0.5, 1, 2, 4, 8):
    u, q = reno_buffer(bdp, f * bdp)
    print(f"{f:10.2f}  {u:11.1%}  {q / C * 1000:10.1f} ms")


# ===== Checking the Mathis model by simulation =====
# Simulate Reno with independent per-packet loss probability p (one window of W packets suffers a loss with probability 1−(1−p)^W) and compare the mean window with 1.22/√p.
import random, math
def mathis_sim(p, rounds=300000, seed=7):
    random.seed(seed); W = 10.0; tot = 0.0
    for _ in range(rounds):
        tot += W
        if random.random() < 1 - (1 - p) ** W: W = max(2.0, W / 2)
        else: W += 1
    return tot / rounds
print("p        simulated mean window   1.22/sqrt(p)")
for p in (1e-2, 1e-3, 1e-4): print(f"{p:6.0e}  {mathis_sim(p):12.1f} {1.22 / math.sqrt(p):18.1f}")
