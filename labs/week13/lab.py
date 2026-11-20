"""Week 13: Measurement, Satellite Networks and the Future
Run: python3 lab.py"""


# ===== Code lab =====
def rtt_ms(d_km, kind):
    if kind == "fibre": return 2 * 1.5 * d_km / 200000 * 1000
    if kind == "leo": return 2 * (1.1 * d_km + 1100) / 300000 * 1000
    return 4 * 35786 / 300000 * 1000
for d in (1000, 5000, 10000): print(d, "km:", {k: round(rtt_ms(d, k)) for k in ("fibre", "leo", "geo")})

import math
def period_min(h_km, R=6371, mu=398600): a = R + h_km; return 2 * math.pi * math.sqrt(a ** 3 / mu) / 60
for h in (550, 1200, 35786): print(f"altitude {h:5d} km: period {period_min(h):7.1f} min")
print("CI half-width (n=100, s=20 ms):", round(1.96 * 20 / math.sqrt(100), 1), "ms")


# ===== Why report medians: bootstrap confidence intervals =====
# RTT samples are heavy-tailed (lognormal here). Compare the sample mean and median and their bootstrap 95% confidence intervals for n = 50, 200 and 1000.
import random, statistics, math
def boot(data, stat, B=1000, seed=3):
    rnd = random.Random(seed); n = len(data)
    vals = sorted(stat([rnd.choice(data) for _ in range(n)]) for _ in range(B))
    return vals[int(0.025 * B)], vals[int(0.975 * B)]
rnd = random.Random(9)
print("true median RTT: 40 ms; true mean:", round(40 * math.exp(0.8 ** 2 / 2), 1), "ms")
for n in (50, 200, 1000):
    d = [rnd.lognormvariate(math.log(40), 0.8) for _ in range(n)]
    m = boot(d, statistics.mean); md = boot(d, statistics.median)
    print(f"n={n:4d}  mean {statistics.mean(d):5.1f} CI [{m[0]:5.1f},{m[1]:5.1f}] width {m[1]-m[0]:5.1f}   median {statistics.median(d):5.1f} CI [{md[0]:5.1f},{md[1]:5.1f}] width {md[1]-md[0]:5.1f}")


# ===== LEO geometry: visibility, slant range and pass time =====
# For a satellite at altitude h seen at minimum elevation ε: central angle λ = arccos(R·cosε/(R+h)) − ε, slant range d = −R·sinε + √((R·sinε)² + h² + 2Rh), maximum pass time = 2λ/ω with ω = 2π/T and T = 2π√((R+h)³/μ).
import math
R, mu = 6371.0, 398600.0
for h in (550, 1200):
    T = 2 * math.pi * math.sqrt((R + h) ** 3 / mu)
    for eps_deg in (25, 40, 60):
        e = math.radians(eps_deg)
        lam = math.acos(R * math.cos(e) / (R + h)) - e
        d = -R * math.sin(e) + math.sqrt((R * math.sin(e)) ** 2 + h * h + 2 * R * h)
        print(f"h={h:4d} km  min elevation {eps_deg:2d} deg: slant range {d:7.0f} km  one-way {d/299792.458*1000:5.2f} ms  max pass {2*lam/(2*math.pi/T)/60:5.1f} min")
    print(f"        orbital period {T/60:.1f} min")
