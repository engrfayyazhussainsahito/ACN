"""Week 10: Wireless and Mobile Networking
Run: python3 lab.py"""


# ===== Code lab =====
from math import log2
def shannon(B_mhz, snr_db): return B_mhz * log2(1 + 10 ** (snr_db / 10))
for s in (10, 20, 30): print(f"20 MHz @ {s} dB: {shannon(20, s):6.1f} Mb/s")
print("80 MHz @ 20 dB:", round(shannon(80, 20)), "Mb/s")

import math
def fspl(d_m, f_mhz): return 20 * math.log10(d_m / 1000) + 20 * math.log10(f_mhz) + 32.44
def cap(B_mhz, snr_db): return B_mhz * math.log2(1 + 10 ** (snr_db / 10))
for f in (2400, 5000):
    loss = fspl(100, f); rx = 20 - loss; snr = rx - (-96)
    print(f"{f/1000:g} GHz @100 m: loss {loss:.1f} dB, rx {rx:.1f} dBm, SNR {snr:.1f} dB, Shannon {cap(20, snr):.0f} Mb/s")


# ===== BPSK bit errors versus theory =====
# Send random bits as ±1 over additive white Gaussian noise and count errors at several Eb/N0 values. Theory: BER = ½·erfc(√(Eb/N0)).
import math, random
def ber_bpsk(ebn0_db, n=300000, seed=1):
    random.seed(seed); ebn0 = 10 ** (ebn0_db / 10); sigma = math.sqrt(1 / (2 * ebn0)); err = 0
    for _ in range(n):
        bit = random.random() < 0.5
        r = (1.0 if bit else -1.0) + random.gauss(0, sigma)
        err += (r > 0) != bit
    return err / n
print("Eb/N0(dB)  simulated BER   theory")
for db in (0, 2, 4, 6, 8):
    print(f"{db:8d}  {ber_bpsk(db):13.2e} {0.5 * math.erfc(math.sqrt(10 ** (db / 10))):10.2e}")


# ===== Wi-Fi contention: slotted CSMA/CA with binary exponential backoff =====
# N saturated stations with CWmin = 16 and up to 6 doublings. In each slot every station whose counter is zero transmits: one transmitter succeeds, two or more collide and double their windows. Reports the collision probability seen by a transmission attempt and the fraction of slots carrying a success.
import random
def csma(N, slots=60000, cwmin=16, stages=6, seed=1):
    random.seed(seed); cw = [cwmin] * N; cnt = [random.randrange(cwmin) for _ in range(N)]; ok = col = 0
    for _ in range(slots):
        tx = [i for i in range(N) if cnt[i] == 0]
        if len(tx) == 1:
            ok += 1; i = tx[0]; cw[i] = cwmin; cnt[i] = random.randrange(cw[i])
        elif len(tx) > 1:
            col += 1
            for i in tx: cw[i] = min(cw[i] * 2, cwmin * 2**stages); cnt[i] = random.randrange(cw[i])
        for i in range(N):
            if cnt[i] > 0 and i not in tx: cnt[i] -= 1
    return col / max(1, ok + col), ok / slots
print("stations  P(collision | busy slot)  success slots")
for N in (2, 5, 10, 20, 50): c, s = csma(N); print(f"{N:8d} {c:22.1%} {s:15.1%}")


# ===== Schedulers: round robin, max rate and proportional fair =====
# Three users with average SNR of 20, 10 and 0 dB and Rayleigh fading (instantaneous rate = log2(1 + SNR·X), X ~ exponential). Proportional fair serves the user with the highest instantaneous-to-average rate ratio.
import random, math
def sched(policy, snr=(100, 10, 1), T=60000, seed=2, tc=100):
    random.seed(seed); n = len(snr); avg = [1e-3] * n; tot = [0.0] * n
    for t in range(T):
        r = [math.log2(1 + snr[i] * random.expovariate(1)) for i in range(n)]
        if policy == "round robin": k = t % n
        elif policy == "max rate": k = max(range(n), key=lambda i: r[i])
        else: k = max(range(n), key=lambda i: r[i] / avg[i])
        for i in range(n): avg[i] = (1 - 1 / tc) * avg[i] + (1 / tc) * (r[k] if i == k else 0)
        tot[k] += r[k]
    return [x / T for x in tot]
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
for pol in ("round robin", "max rate", "proportional fair"):
    th = sched(pol); print(f"{pol:18s} per-user bits/s/Hz {[round(v, 2) for v in th]}  total {sum(th):.2f}  Jain {jain(th):.2f}")
