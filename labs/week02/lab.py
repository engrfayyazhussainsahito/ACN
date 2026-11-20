"""Week 2: Queueing Theory and Performance Modelling
Run: python3 lab.py"""


# ===== Code lab =====
def mm1(lam, mu):
    rho = lam / mu
    return dict(rho=rho, L=rho / (1 - rho), W_ms=1000 / (mu - lam))
for lam in (500, 900, 990):
    r = mm1(lam, 1000)
    print(f"rho={r['rho']:.2f}  L={r['L']:.1f} pkts  W={r['W_ms']:.0f} ms")

def pblock(rho, K): return 1 / (K + 1) if rho == 1 else (1 - rho) * rho ** K / (1 - rho ** (K + 1))
for K in (5, 10, 20): print(f"rho=0.9 K={K:2d}: loss = {pblock(0.9, K):.2%}")
print("rho=1.0 K=10:", f"{pblock(1.0, 10):.2%}")
print("BDP/sqrt(n) buffer:", 10e9 * 0.25 / 8 / 1e6 / 100, "MB")


# ===== Queue simulation with the Lindley recursion =====
# The waiting time of the next packet is W' = max(0, W + S − A), where S is the service time and A the next inter-arrival time. This three-line recursion simulates any single-server FIFO queue, so we can test M/M/1 theory and then break its assumptions with bursty (Pareto) arrivals.
import random
def lindley(n, arr, svc, seed=1):
    random.seed(seed); w = tot = 0.0
    for _ in range(n):
        s = svc(); a = arr()
        tot += w + s                 # response time = waiting + service
        w = max(0.0, w + s - a)      # waiting time of the next packet
    return tot / n
def pareto(mean, alpha=1.5):         # heavy-tailed, infinite variance for alpha <= 2
    xm = mean * (alpha - 1) / alpha
    return lambda: xm / (random.random() ** (1 / alpha))
mu = 1000.0
print("rho   M/M/1 sim   theory    Pareto arrivals (same mean)")
for rho in (0.5, 0.8, 0.9):
    lam = rho * mu
    a = lindley(300000, lambda: random.expovariate(lam), lambda: random.expovariate(mu))
    b = lindley(300000, pareto(1 / lam), lambda: random.expovariate(mu))
    print(f"{rho:.1f}  {a*1000:8.2f} ms {1000/(mu-lam):8.2f} ms  {b*1000:8.2f} ms")


# ===== Erlang-B and tandem queues =====
# Circuit-style resource dimensioning (how many channels for a given blocking probability) and the product-form result for queues in series.
def erlang_b(E, m):
    b = 1.0
    for k in range(1, m + 1): b = E * b / (k + E * b)
    return b
E = 10
m = next(m for m in range(1, 200) if erlang_b(E, m) < 0.01)
print(f"{E} Erlangs of offered load needs {m} channels for <1% blocking (B = {erlang_b(E, m):.4f})")
lam, mu = 500, 1000
print("3 tandem M/M/1 hops:", round(3 * 1000 / (mu - lam), 1), "ms in total (Burke + Jackson: each hop behaves as an independent M/M/1)")
