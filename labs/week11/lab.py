"""Week 11: Content Delivery and Video Streaming
Run: python3 lab.py"""


# ===== Code lab =====
def H(n, a): return sum(i ** -a for i in range(1, n + 1))
N = 100000
for a in (0.8, 1.0, 1.2):
    print(f"alpha={a}: 1% cache hit ratio = {H(N // 100, a) / H(N, a):.1%}")

def sim(fixed=None, n=8, thr=3.0, chunk=4.0, b=8.0):
    stalls = 0
    for _ in range(n):
        bit = fixed or max(x for x in (1.0, 2.5, 5.0) if x <= 0.9 * thr)
        dl = bit * chunk / thr
        if dl > b: stalls += 1
        b = max(0, b - dl) + chunk
    return stalls, round(b, 1)
print("fixed 5 Mb/s (stalls, final buffer):", sim(5.0))
print("adaptive     (stalls, final buffer):", sim())


# ===== Cache replacement policies on a Zipf workload =====
# LRU versus LFU for a 5,000-object catalogue with Zipf(1.0) popularity, 100,000 requests and a cache holding 1%, 5% or 10% of the catalogue. The 'ideal' policy keeps the most popular objects.
import random
from collections import OrderedDict, Counter
random.seed(4); N, R = 5000, 100000
w = [1 / (i + 1) for i in range(N)]
req = random.choices(range(N), w, k=R)
def lru(c):
    cache = OrderedDict(); hit = 0
    for x in req:
        if x in cache: hit += 1; cache.move_to_end(x)
        else:
            cache[x] = 1
            if len(cache) > c: cache.popitem(last=False)
    return hit / R
def lfu(c):
    cache, freq, hit = set(), Counter(), 0
    for x in req:
        freq[x] += 1
        if x in cache: hit += 1
        else:
            if len(cache) >= c:
                victim = min(cache, key=lambda y: freq[y])
                if freq[victim] < freq[x]: cache.remove(victim); cache.add(x)
            else: cache.add(x)
    return hit / R
tot = sum(w)
print("cache  LRU     LFU     ideal")
for pc in (0.01, 0.05, 0.10):
    c = int(pc * N); print(f"{pc:4.0%}  {lru(c):6.1%}  {lfu(c):6.1%}  {sum(w[:c]) / tot:6.1%}")


# ===== Throughput-based versus buffer-based adaptive bitrate =====
# A Markov-modulated bandwidth trace drives two players with the same ladder and 4 s chunks. The throughput player picks the highest bitrate under 80% of the last chunk's throughput; the buffer player maps buffer level (5 s reservoir, 15 s cushion) to a bitrate.
import random
ladder = [0.3, 0.75, 1.2, 2.4, 4.5]; CH = 4.0
def trace(n, seed):
    rnd = random.Random(seed); states = [0.8, 1.5, 3.0, 6.0]; i = 2; out = []
    for _ in range(n):
        if rnd.random() > 0.85: i = max(0, min(3, i + rnd.choice((-1, 1))))
        out.append(states[i] * rnd.uniform(0.8, 1.2))
    return out
def play(policy, bw):
    b, last, stall, tot, sw, prev = 8.0, bw[0], 0.0, 0.0, 0, None
    for x in bw:
        if policy == "throughput": r = max([l for l in ladder if l <= 0.8 * last] or [ladder[0]])
        else: r = ladder[round(min(1, max(0, (b - 5) / 15)) * (len(ladder) - 1))]
        dl = r * CH / x
        if dl > b: stall += dl - b; b = 0
        else: b -= dl
        b = min(30, b + CH); last = x; tot += r; sw += prev is not None and r != prev; prev = r
    return tot / len(bw), stall, sw
for pol in ("throughput", "buffer"):
    res = [play(pol, trace(150, s)) for s in range(60)]
    print(f"{pol:10s} mean bitrate {sum(r[0] for r in res)/60:5.2f} Mb/s   stall {sum(r[1] for r in res)/60:6.1f} s per session   switches {sum(r[2] for r in res)/60:5.1f}")
