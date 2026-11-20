"""Week 4: Congestion Control I: AIMD, Reno and CUBIC
Run: python3 lab.py"""


# ===== Code lab =====
x, y = 80.0, 10.0            # two flows, unequal start; capacity 100
for rtt in range(200):
    x += 1; y += 1                     # additive increase
    if x + y > 100: x *= 0.5; y *= 0.5 # multiplicative decrease
print(f"flow1={x:.1f}  flow2={y:.1f}  ratio={x/y:.2f}")

import math
def slow_start_rtts(segments, iw=10):
    sent, w, rtt = 0, iw, 0
    while sent < segments: sent += w; w *= 2; rtt += 1
    return rtt
print("100 KB (69 segs):", slow_start_rtts(69), "RTTs;  1 MB (685 segs):", slow_start_rtts(685), "RTTs")
p = 1e-4; W = math.sqrt(8 / (3 * p)); print(f"Reno W={W:.0f}  avg cwnd={0.75 * W:.0f} packets")


# ===== AIMD with several flows: fairness and RTT bias =====
# Synchronised AIMD flows share a bottleneck of 1000 packets/s. Window growth is 1 packet per RTT, and all flows halve when the aggregate rate exceeds capacity. Jain's index J = (Σx)²/(n·Σx²) is 1 for perfect fairness.
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
def aimd(rtts, cap, T=300.0, dt=0.002):
    n = len(rtts); w = [5.0] * n; acc = [0.0] * n; k = 0
    for step in range(int(T / dt)):
        for i in range(n): w[i] += dt / rtts[i]
        if sum(w[i] / rtts[i] for i in range(n)) > cap: w = [x / 2 for x in w]
        if step * dt > T / 2:
            for i in range(n): acc[i] += w[i] / rtts[i]
            k += 1
    return [a / k for a in acc]
for rtts in ([0.05, 0.05], [0.02, 0.08], [0.05] * 4):
    r = aimd(rtts, 1000)
    print("RTTs(ms)", [int(x * 1000) for x in rtts], "-> rates", [round(x) for x in r], f" Jain={jain(r):.3f}")


# ===== Fluid model of Reno =====
# Integrate dW/dt = 1/R − (W/2)·(W/R)·p and compare the equilibrium window with √(2/p) (fluid model) and √(8/(3p)) (sawtooth model).
import math
def fluid(p, R=0.1, T=300.0, dt=0.001):
    W = 1.0
    for _ in range(int(T / dt)): W += dt * (1 / R - (W / 2) * (W / R) * p)
    return W
print("loss p   fluid sim   sqrt(2/p)   sqrt(8/3p) (sawtooth peak)")
for p in (1e-2, 1e-3, 1e-4): print(f"{p:7.0e} {fluid(p):10.1f} {math.sqrt(2 / p):11.1f} {math.sqrt(8 / (3 * p)):11.1f}")
