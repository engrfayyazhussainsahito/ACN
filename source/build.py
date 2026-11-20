import math, random, html, io, contextlib, os, re, heapq
from collections import Counter
_B = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(_B, "..") if os.path.basename(_B) == "source" else os.path.join(_B, "site"))
os.makedirs(OUT + "/assets", exist_ok=True)
COL = ["#1f6f78", "#c0562b", "#6a4c93", "#8a8a2a"]
FIGS = {}

def tick(v): return f"{v:.3g}"
def plot(name, cap, series, xl, yl, logx=False, logy=False, labels=None):
    W, H, L, R, T, B = 640, 360, 70, 16, 16, 50
    xs = [x for s in series for x in s[1]]; ys = [y for s in series for y in s[2]]
    if labels: xlo, xhi = -0.5, len(labels) - 0.5
    elif logx: xlo, xhi = 10 ** math.floor(math.log10(min(xs))), 10 ** math.ceil(math.log10(max(xs)))
    else: xlo, xhi = min(xs), max(xs)
    if logy: ylo, yhi = 10 ** math.floor(math.log10(min(ys))), 10 ** math.ceil(math.log10(max(ys)))
    else: ylo, yhi = 0, max(ys) * 1.05
    def sc(v, lo, hi, a, b, lg): return a + ((math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) if lg else (v - lo) / (hi - lo)) * (b - a)
    X = lambda v: sc(v, xlo, xhi, L, W - R, logx); Y = lambda v: sc(v, ylo, yhi, H - B, T, logy)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(cap)}">']
    yt = [10 ** k for k in range(round(math.log10(ylo)), round(math.log10(yhi)) + 1)] if logy else [ylo + (yhi - ylo) * i / 5 for i in range(6)]
    for v in yt: o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="g"/><text x="{L-6}" y="{Y(v)+4:.1f}" text-anchor="end">{tick(v)}</text>')
    if labels:
        for i, lb in enumerate(labels): o.append(f'<text x="{X(i):.1f}" y="{H-B+16}" text-anchor="middle">{html.escape(lb)}</text>')
        bw = (W - L - R) / len(labels) * 0.55
        for i, v in enumerate(series[0][2]): o.append(f'<rect x="{X(i)-bw/2:.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{H-B-Y(v):.1f}" fill="{COL[i%4]}"/><text x="{X(i):.1f}" y="{Y(v)-5:.1f}" text-anchor="middle">{tick(v)}</text>')
    else:
        xt = [10 ** k for k in range(round(math.log10(xlo)), round(math.log10(xhi)) + 1)] if logx else [xlo + (xhi - xlo) * i / 5 for i in range(6)]
        for v in xt: o.append(f'<text x="{X(v):.1f}" y="{H-B+16}" text-anchor="middle">{tick(v)}</text>')
        for i, (n, px, py) in enumerate(series):
            o.append(f'<polyline fill="none" stroke="{COL[i%4]}" stroke-width="2.2" points="{" ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(px, py))}"/>')
            o.append(f'<text x="{L+10+i*150}" y="{T+12}" fill="{COL[i%4]}" class="lg">&#9644; {html.escape(n)}</text>')
    o.append(f'<line x1="{L}" x2="{L}" y1="{T}" y2="{H-B}" class="ax"/><line x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" class="ax"/>')
    o.append(f'<text x="{(L+W-R)/2}" y="{H-8}" text-anchor="middle" class="al">{html.escape(xl)}</text><text transform="translate(14 {(T+H-B)/2}) rotate(-90)" text-anchor="middle" class="al">{html.escape(yl)}</text></svg>')
    FIGS[name] = ("".join(o), cap)

# ---------- computed figures ----------
N = list(range(1, 11)); P = math.ceil(10e6 / 1500)
plot("pkt", "Time to move a 10 MB message over N store-and-forward hops at 100 Mb/s. Packetising turns hops from a multiplier into an additive term.",
     [("whole message", N, [n * 80e6 / 100e6 for n in N]), ("1500 B packets", N, [(n + P - 1) * 1500 * 8 / 100e6 for n in N])], "hops N", "transfer time (s)")
rho = [i / 100 for i in range(5, 98)]
plot("mm1", "Mean delay of an M/M/1 and an M/D/1 queue (service rate 1000 pkt/s). Delay explodes as utilisation nears 1; deterministic service halves the queueing term.",
     [("M/M/1", rho, [1000 / (1000 * (1 - r)) for r in rho]), ("M/D/1", rho, [1000 * (1 / 1000 + r / (2 * 1000 * (1 - r))) for r in rho])], "utilisation ρ", "mean delay (ms)")
a, b, A, Bv = 2, 1, [], []
for r in range(1, 16): b = a + 1; a = b + 1; A.append(min(a, 16)); Bv.append(min(b, 16))
plot("cti", "Count-to-infinity: after the B-C link fails, A and B keep raising their distance to C by 2 per exchange until they reach the 'infinity' value 16.",
     [("B's estimate", list(range(1, 16)), Bv), ("A's estimate", list(range(1, 16)), A)], "update exchange", "advertised cost to C")
cap, rt, w, reno, cub, tl = 400, 0.1, 200.0, [], [], 0
w = 200.0
for i in range(600):
    w += 1
    if w > cap: w /= 2
    reno.append(w)
w, tl, K = 280.0, 0, (cap * 0.3 / 0.4) ** (1 / 3)
for i in range(600):
    tl += rt; w = 0.4 * (tl - K) ** 3 + cap
    if w > cap: w, tl = 0.7 * cap, 0
    cub.append(w)
plot("cc", "Congestion window of Reno (+1 per RTT, halve on loss) versus CUBIC (cubic growth, ×0.7 on loss) on a path holding 400 packets, RTT 100 ms.",
     [("Reno", list(range(600)), reno), ("CUBIC", list(range(600)), cub)], "time (RTTs)", "cwnd (packets)")
pl = [10 ** (-6 + i * 0.1) for i in range(41)]
plot("mathis", "Mathis model throughput for 1460 B segments at three RTTs. A 100x drop in loss rate buys 10x throughput; doubling RTT halves it.",
     [(f"RTT {r} ms", pl, [1.22 * 1460 * 8 / (r / 1000) / math.sqrt(p) / 1e6 for p in pl]) for r in (20, 100, 200)], "loss probability p", "throughput (Mb/s)", True, True)
rr = list(range(10, 301, 10))
plot("hs", "Time until the first response byte for four connection setups. Each saved round trip is worth more as RTT grows (mobile, intercontinental).",
     [(n, rr, [k * r for r in rr]) for n, k in [("TCP+TLS1.2", 4), ("TCP+TLS1.3", 3), ("QUIC 1-RTT", 2), ("QUIC 0-RTT", 1)]], "RTT (ms)", "time to first byte (ms)")
ks = list(range(4, 65, 4))
plot("ft", "Fat-tree built from k-port switches: hosts = k³/4 and switches = 5k²/4. Commodity 48-port switches already reach 27,648 hosts.",
     [("hosts", ks, [k ** 3 / 4 for k in ks]), ("switches", ks, [5 * k * k / 4 for k in ks])], "ports per switch k", "count", False, True)
random.seed(1); wts = [1 / (i + 1) for i in range(5000)]; stream = random.choices(range(5000), wts, k=200000); tru = Counter(stream); top = [f for f, _ in tru.most_common(100)]
def cms_err(wd, d=4):
    ab = [(random.randrange(1, 10 ** 9), random.randrange(10 ** 9)) for _ in range(d)]; t = [[0] * wd for _ in range(d)]
    for x in stream:
        for j, (p_, q_) in enumerate(ab): t[j][(p_ * x + q_) % 1000003 % wd] += 1
    return sum((min(t[j][(p_ * f + q_) % 1000003 % wd] for j, (p_, q_) in enumerate(ab)) - tru[f]) / tru[f] for f in top) / 100
wds = [64, 128, 256, 512, 1024, 2048, 4096]
plot("cms", "Count-min sketch (4 rows) on a 200,000-packet Zipf stream of 5,000 flows: mean relative error of the 100 heaviest flows versus row width.",
     [("mean rel. error", wds, [cms_err(x) for x in wds])], "row width (counters)", "relative error", True, False)
sn = list(range(0, 41))
plot("shannon", "Shannon capacity C = B·log2(1+SNR) for three channel widths. Each +3 dB of SNR buys about one extra bit/s/Hz at high SNR.",
     [(f"{b_} MHz", sn, [b_ * math.log2(1 + 10 ** (s / 10)) for s in sn]) for b_ in (20, 40, 80)], "SNR (dB)", "capacity (Mb/s)")
Z = 100000; fr = [i / 200 for i in range(1, 41)]
def zh(al):
    cs = [0.0]
    for i in range(1, Z + 1): cs.append(cs[-1] + i ** -al)
    return [cs[int(f * Z)] / cs[Z] for f in fr]
plot("zipf", "CDN cache hit ratio for a 100,000-object catalogue with Zipf popularity exponent α. Skewed demand makes small caches very effective.",
     [(f"α = {al}", [f * 100 for f in fr], [h * 100 for h in zh(al)]) for al in (0.8, 1.0, 1.2)], "cache size (% of catalogue)", "hit ratio (%)")
plot("amp", "Maximum reported bandwidth amplification factors of UDP reflection vectors (log scale; figures vary by measurement and are approximate).",
     [("factor", [0, 1, 2], [54, 557, 51000])], "", "amplification (x)", False, True, ["DNS", "NTP monlist", "memcached"])
dk = list(range(500, 15001, 500))
plot("lat", "Round-trip propagation delay versus ground distance: fibre (1.5x route stretch, 2e8 m/s), LEO with laser links (550 km shell) and GEO bent-pipe.",
     [("fibre", dk, [2 * 1.5 * d / 200000 * 1000 for d in dk]), ("LEO", dk, [2 * (1.1 * d + 1100) / 300000 * 1000 for d in dk]), ("GEO", dk, [4 * 35786 / 300000 * 1000 for d in dk])], "ground distance (km)", "RTT (ms)")

# ---------- course content ----------
W_ = []
def wk(n, ph, title, src, summary, obj, key, body, code, ex, rd):
    W_.append(dict(n=n, ph=ph, title=title, src=src, summary=summary, obj=obj, key=key, body=body, code=code, ex=ex, rd=rd))
wk(1, 1, "Internet Architecture and Design Principles", "Stanford CS244, MIT 6.829, Berkeley CS268",
   "Layering, the narrow waist, the end-to-end argument and the delay model that every later week builds on.",
   ["Explain why the Internet's narrow waist enabled growth and also froze IP.", "State the end-to-end argument and apply it to a reliability design.", "Compute store-and-forward delay and the bandwidth-delay product."],
   "T = (N + P − 1)·L/R ;  BDP = R × RTT",
   r"""## Why architecture still matters
The Internet is a narrow waist: many applications over IP over many link types. Each layer evolves independently, which is also why IP itself is nearly impossible to change (IPv6 has needed over 25 years). Clark (1988) ranked the DARPA goals with survivability first and cost last; that ordering explains fate-sharing and stateless routers.

## The end-to-end argument
Saltzer, Reed and Clark (1984): a function such as reliability can be implemented completely only at the endpoints, so the network should offer it only as a performance optimisation. A file transfer over reliable hops still needs an end-to-end checksum, because a router's memory can corrupt data between two hop-level checks.

## The delay model
Per hop a packet suffers processing, queueing, transmission (L/R) and propagation delay. Switches are store-and-forward, so a packet must arrive fully before it moves on. Cutting a message of M bits into P = ⌈M/L⌉ packets over N links of rate R gives

$ T = (N + P − 1)·L/R      versus      T = N·M/R without packetising

!! Worked example: 10 MB over 5 hops at 100 Mb/s takes 4.00 s as one unit but only 0.80 s as 1500-byte packets, because the hops now work in a pipeline.

[[fig:pkt]]

## Bandwidth-delay product
BDP = R × RTT is the data in flight needed to keep a pipe full. A 1 Gb/s path with 80 ms RTT holds 10 MB. Nearly every transport and congestion-control idea in Weeks 4 to 6 is about filling this pipe without overflowing its buffers.""",
   """def transfer(M, L, N, R, packets=True):
    P = -(-M // L)
    return (N + P - 1) * L / R if packets else N * M / R
M = 10e6 * 8
print("whole message:", transfer(M, 1500 * 8, 5, 100e6, False), "s")
print("packetised   :", round(transfer(10_000_000, 1500, 5, 100e6 / 8), 3), "s")
print("BDP 1 Gb/s, 80 ms:", 1e9 * 0.08 / 8 / 1e6, "MB")""",
   [("A 2 Mb file crosses 3 links of 1 Mb/s as one unit. How long? With 10 packets of 0.2 Mb?", "One unit: 3 × 2 = 6 s. Packets: (3+10−1) × 0.2 = 2.4 s."),
    ("Why is hop-by-hop reliability not a substitute for an end-to-end check?", "Faults can occur between the hop checks (router memory, software bugs, middleboxes) and the end application is the only party that knows what 'correct' means.")],
   ["Clark (1988) The design philosophy of the DARPA Internet protocols.", "Saltzer, Reed, Clark (1984) End-to-end arguments in system design.", "Kurose & Ross, Computer Networking: A Top-Down Approach, ch. 1."])
wk(2, 1, "Queueing Theory and Performance Modelling", "MIT 6.829, CMU 15-744, Princeton COS 461",
   "Little's law, M/M/1 and M/D/1 queues, why delay explodes near full utilisation and why real traffic breaks Poisson assumptions.",
   ["Apply Little's law to any stable system.", "Derive and use the M/M/1 delay formula.", "Explain why self-similar traffic invalidates simple queueing predictions."],
   "L = λW ;  W(M/M/1) = 1/(μ − λ)",
   r"""## Little's law
For any stable system, the mean number in the system equals arrival rate times mean time in the system. It needs no assumption about the arrival or service distribution, which makes it the most useful identity in networking.

$ L = λ · W

## The M/M/1 queue
Poisson arrivals at rate λ, exponential service at rate μ, one server. With utilisation ρ = λ/μ the stationary probability of n packets is (1−ρ)ρⁿ, so L = ρ/(1−ρ) and by Little

$ W = 1/(μ − λ)

!! Worked example: μ = 1000 pkt/s. At ρ = 0.5 W = 2 ms. At ρ = 0.9 W = 10 ms, and by Little the queue holds L = 900 × 0.01 = 9 packets. At ρ = 0.99 W is 100 ms.

[[fig:mm1]]

## Beyond Poisson
M/D/1 (constant packet size) halves the queueing component. But Paxson and Floyd (1995) showed wide-area traffic is bursty at all time scales (self-similar), so real queues build up far more than Poisson models predict. Practical lessons: keep utilisation below roughly 70 to 80 percent for latency-sensitive traffic, and size buffers using measurements, not the M/M/1 formula.""",
   """def mm1(lam, mu):
    rho = lam / mu
    return dict(rho=rho, L=rho / (1 - rho), W_ms=1000 / (mu - lam))
for lam in (500, 900, 990):
    r = mm1(lam, 1000)
    print(f"rho={r['rho']:.2f}  L={r['L']:.1f} pkts  W={r['W_ms']:.0f} ms")""",
   [("A link serves 2000 pkt/s and receives 1800 pkt/s (M/M/1). Mean delay and mean queue length?", "W = 1/(2000−1800) = 5 ms; L = 1800 × 0.005 = 9 packets."),
    ("Why does doubling a saturated link's capacity cut delay by far more than half?", "W = 1/(μ−λ): at λ close to μ the denominator is tiny. Doubling μ greatly enlarges μ−λ, so delay can fall 10x or more.")],
   ["Paxson & Floyd (1995) Wide-area traffic: the failure of Poisson modeling.", "Kleinrock, Queueing Systems Vol. 1.", "Appenzeller, Keslassy, McKeown (2004) Sizing router buffers."])
wk(3, 1, "Routing: Link-State, Distance-Vector and BGP", "Princeton COS 561, CMU 15-744, Stanford CS244",
   "Shortest-path algorithms, the count-to-infinity problem, and BGP's policy-driven interdomain routing, including the 2008 YouTube hijack.",
   ["Run Dijkstra and Bellman-Ford and explain their message costs.", "Explain count-to-infinity and its mitigations.", "Describe BGP path selection and Gao-Rexford business policies."],
   "Dijkstra O(E log V) ;  valley-free paths",
   r"""## Intradomain routing
Link-state protocols (OSPF, IS-IS) flood link costs so every router runs Dijkstra on the same map: fast convergence, O(E) state. Distance-vector protocols (RIP) exchange only distance tables with neighbours via Bellman-Ford: small messages but slow convergence.

## Count-to-infinity
If B's link to C fails while A still believes it reaches C through B, they feed each other stale information and raise costs by 2 each exchange.

[[fig:cti]]

Fixes: define a small infinity (RIP uses 16), split horizon with poisoned reverse, hold-down timers, or path-vector routing, which carries the whole path so loops are detected directly.

## BGP and policy
Between ~75,000 autonomous systems the goal is not shortest paths but business policy. BGP is a path-vector protocol. Selection order is roughly: highest local preference, shortest AS path, lowest MED, then tie-breakers. Gao and Rexford (2001) observed that customer, provider and peer relationships imply valley-free paths and that following the 'prefer customer routes, export to customers only unless route is a customer route' rule guarantees convergence.

!! BGP has no origin authentication. In February 2008 Pakistan Telecom announced a more-specific /24 for YouTube's prefix to block it locally, the route leaked to the world, and YouTube was unreachable globally for about two hours. RPKI route-origin validation (Week 12) is the structural fix.""",
   """import heapq
G = {"A": {"B": 2, "C": 5}, "B": {"A": 2, "C": 1, "D": 4}, "C": {"A": 5, "B": 1, "D": 1}, "D": {"B": 4, "C": 1}}
def dijkstra(G, s):
    dist, prev, pq = {s: 0}, {}, [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v, w in G[u].items():
            if d + w < dist.get(v, 1e9): dist[v], prev[v] = d + w, u; heapq.heappush(pq, (d + w, v))
    return dist, prev
dist, prev = dijkstra(G, "A")
print(dist)
path, n = ["D"], "D"
while n != "A": n = prev[n]; path.append(n)
print("A->D:", " ".join(reversed(path)))""",
   [("Why does path-vector routing avoid count-to-infinity?", "Each route carries its AS path; a router rejects any route whose path contains its own AS, so loops are detected immediately."),
    ("A stub AS has two providers. Why can it accidentally become a transit AS, and how is it prevented?", "If it re-advertises one provider's routes to the other. Export filters (advertise only own and customer prefixes) prevent it.")],
   ["Gao & Rexford (2001) Stable Internet routing without global coordination.", "Labovitz et al. (2000) Delayed Internet routing convergence.", "RIPE NCC (2008) YouTube hijacking: a RIPE NCC RIS case study."])
wk(4, 2, "Congestion Control I: AIMD, Reno and CUBIC", "Stanford CS244, MIT 6.829, CMU 15-744",
   "Why AIMD converges to fairness, how Reno and CUBIC differ, and why loss-based control struggles on large-BDP paths.",
   ["Prove with Chiu-Jain geometry that AIMD converges to fair, efficient shares.", "Draw Reno's sawtooth and compute its average window.", "Explain how CUBIC decouples window growth from RTT."],
   "avg cwnd ≈ ¾·Wmax ;  CUBIC: W(t)=C(t−K)³+Wmax",
   r"""## The problem
Jacobson (1988) saved the Internet from congestion collapse by adding a sender window cwnd that probes for bandwidth: slow start doubles cwnd each RTT until ssthresh, then congestion avoidance adds 1 MSS per RTT; on loss cwnd is halved.

## Why additive-increase, multiplicative-decrease
Chiu and Jain (1989) plotted two users' rates (x₁, x₂). Additive increase moves along a 45° line (fairness unchanged, efficiency up); multiplicative decrease moves toward the origin along a ray (fairness improves). Alternating them spirals to the intersection of the fairness and efficiency lines. MIMD and AIAD do not converge.

## Reno's sawtooth
If the window oscillates between W/2 and W, the average is ¾W. Recovery after a halving takes W/2 RTTs. At 10 Gb/s and 100 ms RTT, W is about 85,000 packets and recovery takes over an hour, which motivated CUBIC.

## CUBIC
CUBIC (Ha, Rhee, Xu 2008; Linux default) grows the window as a cubic function of real time since the last loss, rising fast, flattening near the old maximum Wmax, then probing beyond it:

$ W(t) = C·(t − K)³ + Wmax,    K = ∛(Wmax·(1−β)/C),    β = 0.7

Because growth depends on time, not ACK clocking, flows with different RTTs are treated more equally.

[[fig:cc]]""",
   """x, y = 80.0, 10.0            # two flows, unequal start; capacity 100
for rtt in range(200):
    x += 1; y += 1                     # additive increase
    if x + y > 100: x *= 0.5; y *= 0.5 # multiplicative decrease
print(f"flow1={x:.1f}  flow2={y:.1f}  ratio={x/y:.2f}")""",
   [("Reno average window if Wmax = 100 packets, RTT = 50 ms, MSS = 1460 B? Throughput?", "Average ¾×100 = 75 packets. Throughput = 75×1460×8/0.05 ≈ 17.5 Mb/s."),
    ("Why do AIAD controls fail to converge to fairness?", "Both increase and decrease move parallel to the 45° line, so the difference x₁−x₂ never shrinks.")],
   ["Jacobson (1988) Congestion avoidance and control.", "Chiu & Jain (1989) Analysis of the increase and decrease algorithms.", "Ha, Rhee, Xu (2008) CUBIC: a new TCP-friendly high-speed TCP variant."])
wk(5, 2, "Congestion Control II: BBR, Delay-Based and Modelling", "MIT 6.829, CMU 15-744, Stanford CS244",
   "Throughput models, bufferbloat, and model-based control (BBR) that targets the bandwidth-delay product instead of loss.",
   ["Use the Mathis formula to predict TCP throughput.", "Explain bufferbloat and why loss is a poor congestion signal.", "Describe BBR's bottleneck-bandwidth and RTprop estimators."],
   "Thr ≈ (MSS/RTT)·1.22/√p",
   r"""## Predicting TCP throughput
Mathis et al. (1997) derived, from the Reno sawtooth with one loss per cycle, a steady-state throughput

$ Thr ≈ (MSS / RTT) · (1.22 / √p)

!! Worked example: MSS 1460 B, RTT 100 ms, p = 10⁻⁴ gives (11,680 bit / 0.1 s) × 122 ≈ 14.2 Mb/s. To fill 1 Gb/s at the same RTT you would need p ≈ 2×10⁻⁸, which is why loss-based TCP cannot fill long fat pipes.

[[fig:mathis]]

## Bufferbloat
Large buffers delay the loss signal: loss-based senders fill them, adding hundreds of milliseconds of queueing (Gettys 2011). Delay-based schemes (Vegas, FAST) back off when RTT rises, but lose to loss-based flows sharing the same queue. Active queue management (CoDel, FQ-CoDel) and ECN mark packets early based on sojourn time.

## BBR
Cardwell et al. (2016) observed that the optimum operating point is a full pipe with an empty queue: rate = BtlBw, inflight = BtlBw × RTprop. BBR estimates BtlBw (windowed max of delivery rate) and RTprop (windowed min of RTT) and paces at that rate, periodically probing up (gain 1.25) and draining. It is not loss-driven, so it performs well on shallow-buffered or lossy paths, but v1 can starve loss-based flows and ignores loss; BBRv2/v3 add loss and ECN signals.""",
   """from math import sqrt
def mathis(mss=1460, rtt=0.1, p=1e-4): return 1.22 * mss * 8 / rtt / sqrt(p) / 1e6
for rtt in (0.02, 0.1, 0.2): print(f"RTT {rtt*1000:>3.0f} ms  p=1e-4 -> {mathis(rtt=rtt):6.1f} Mb/s")
print("loss needed for 1 Gb/s at 100 ms: %.1e" % ((1.22 * 1460 * 8 / 0.1 / 1e9) ** 2))""",
   [("Why can a flow with 4x the RTT of another get only 1/4 of the throughput at equal loss?", "Throughput ∝ 1/RTT: window growth is clocked by ACKs, so long-RTT flows grow slowly."),
    ("Why does BBR keep a minimum-RTT filter for 10 s and periodically reduce inflight?", "To re-measure true propagation delay (RTprop) when queues are drained; otherwise standing queues would inflate the estimate.")],
   ["Mathis, Semke, Mahdavi, Ott (1997) The macroscopic behavior of the TCP congestion avoidance algorithm.", "Cardwell et al. (2016) BBR: congestion-based congestion control. ACM Queue.", "Nichols & Jacobson (2012) Controlling queue delay."])
wk(6, 2, "Modern Transport: QUIC, TLS 1.3 and Multipath", "Stanford CS244, Berkeley CS268",
   "Why transport moved to user space over UDP, how handshakes shrink from four round trips to one or zero, and head-of-line blocking.",
   ["Count round trips for TCP+TLS and QUIC setups.", "Explain head-of-line blocking and how QUIC streams avoid it.", "Describe connection migration and 0-RTT replay risk."],
   "TTFB = k·RTT ; k = 4, 3, 2, 1",
   r"""## Why a new transport
TCP is implemented in kernels and inspected by middleboxes, so extensions (TFO, MPTCP) deploy slowly: ossification. QUIC (Langley et al. 2017; RFC 9000) runs over UDP in user space with encrypted headers, so applications ship transport changes with a library update.

## Handshake cost
With RTT as the unit, time to first response byte is

$ TCP + TLS 1.2 = 4 RTT,  TCP + TLS 1.3 = 3 RTT,  QUIC = 2 RTT,  QUIC 0-RTT = 1 RTT

[[fig:hs]]

!! At RTT 150 ms (mobile or intercontinental) QUIC 1-RTT saves 300 ms versus TCP+TLS 1.2. 0-RTT data is replayable, so only idempotent requests may use it.

## Head-of-line blocking
HTTP/2 multiplexes streams over one TCP connection, but a single lost segment stalls every stream behind it. QUIC treats streams independently: loss stalls only the stream whose packet was lost. Connection IDs allow migration across networks (Wi-Fi to LTE) without a new handshake. Google reported meaningful latency gains at the tail (95th-percentile search latency) rather than the median.

## Multipath
MPTCP and multipath QUIC send over several paths simultaneously for bandwidth and resilience; the open problems are coupled congestion control (fairness at a shared bottleneck) and scheduling over heterogeneous RTTs.""",
   """def ttfb(rtt_ms, setup): return {"tcp+tls12": 4, "tcp+tls13": 3, "quic": 2, "quic0": 1}[setup] * rtt_ms
for s in ("tcp+tls12", "tcp+tls13", "quic", "quic0"): print(f"{s:10s} @150 ms RTT: {ttfb(150, s):4.0f} ms")""",
   [("Why can middleboxes block deployment of a new TCP option but not a new QUIC feature?", "TCP headers are visible and parsed; QUIC encrypts nearly everything above UDP, leaving middleboxes nothing to drop selectively."),
    ("What attack does 0-RTT enable and how do servers limit it?", "Replay of early data. Servers restrict 0-RTT to idempotent requests and use anti-replay caches or single-use tickets.")],
   ["Langley et al. (2017) The QUIC transport protocol: design and Internet-scale deployment. SIGCOMM.", "RFC 9000 (QUIC) and RFC 8446 (TLS 1.3).", "Raiciu et al. (2012) How hard can it be? Designing and implementing a deployable multipath TCP."])
wk(7, 3, "Data Center Networks", "Berkeley CS268, Stanford CS244, CMU 15-744",
   "Clos and fat-tree topologies, ECMP and its collisions, incast, and DCTCP.",
   ["Size a k-ary fat-tree.", "Explain ECMP hash collisions and alternatives.", "Describe incast and how DCTCP uses ECN."],
   "hosts = k³/4 ; switches = 5k²/4",
   r"""## From trees to Clos networks
Classic data centres used oversubscribed trees whose core links became bottlenecks. Al-Fares et al. (2008) built full-bisection bandwidth from identical commodity switches in a k-ary fat-tree: k pods, each with k/2 edge and k/2 aggregation switches, and (k/2)² core switches.

$ hosts = k³/4,      switches = 5k²/4

!! Worked example: k = 48 gives 27,648 hosts using 2,880 switches, with (k/2)² = 576 equal-cost paths between pods.

[[fig:ft]]

## ECMP and its limits
Equal-cost multipath hashes the 5-tuple so packets of a flow stay in order. Two elephant flows hashing onto one link collide while others idle; with few large flows, utilisation is poor. Remedies: flowlet switching (CONGA, LetFlow), per-packet spraying with reordering tolerance, and centralised scheduling (Hedera).

## Incast and DCTCP
Partition-aggregate workloads make many servers answer one client simultaneously, overflowing a shallow switch buffer and triggering 200 ms TCP timeouts: throughput collapse (incast). DCTCP (Alizadeh et al. 2010) marks packets with ECN above a small queue threshold K and senders reduce cwnd in proportion to the fraction of marked packets, α:

$ cwnd ← cwnd · (1 − α/2)

giving high throughput with queues of only a few packets. Recent work (Homa, NDP, HPCC) goes further with receiver-driven credits and in-network telemetry.""",
   """def fat_tree(k): return dict(hosts=k**3 // 4, switches=5 * k * k // 4, core_paths=(k // 2) ** 2)
for k in (4, 16, 48, 64): print(k, fat_tree(k))""",
   [("Why is full bisection bandwidth in a fat-tree not the same as no congestion?", "It guarantees capacity only for ideal load balancing; ECMP hashing collisions and incast can still congest individual links."),
    ("With α = 0.2 how much does DCTCP shrink cwnd, versus standard TCP?", "DCTCP cuts by α/2 = 10 %; standard ECN-TCP halves (50 %).")],
   ["Al-Fares, Loukissas, Vahdat (2008) A scalable, commodity data center network architecture.", "Greenberg et al. (2009) VL2.", "Alizadeh et al. (2010) Data center TCP (DCTCP)."])
wk(9, 3, "SDN and Programmable Data Planes", "Stanford CS244, Princeton COS 561, MIT 6.829",
   "Separating control and data planes, match-action abstractions, P4, and in-network telemetry with sketches.",
   ["Explain control/data plane separation and its trade-offs.", "Write match-action rules and longest-prefix semantics.", "Size a count-min sketch for a measurement task."],
   "CMS error ≤ ε·N with prob. 1−δ ; w=⌈e/ε⌉, d=⌈ln 1/δ⌉",
   r"""## Why SDN
Traditional routers bundle control and forwarding in closed boxes. OpenFlow (McKeown et al. 2008) exposes a table of match-action rules and a logically centralised controller computes them, so network-wide policy (traffic engineering, slicing) is software. Google's B4 WAN runs near 100% link utilisation with SDN-based traffic engineering versus 30-40% typical in conventional WANs.

## Match-action and P4
A switch pipeline parses headers, matches against tables (exact, ternary, longest-prefix) and applies actions (forward, rewrite, drop, meter). P4 (Bosshart et al. 2014) makes the parser and tables programmable, so new protocols or telemetry need no new silicon. Trade-offs: controller scalability and failure, consistent updates, and limited per-packet compute and memory.

## Measurement with sketches
Switches cannot keep per-flow counters for millions of flows. A count-min sketch (Cormode and Muthukrishnan 2005) uses d hash rows of w counters; an update increments one counter per row and the estimate is the minimum, which never underestimates. With w = ⌈e/ε⌉ and d = ⌈ln(1/δ)⌉ the overestimate is at most εN with probability 1−δ.

[[fig:cms]]

In this run the error falls about 2.5x per doubling of width (faster than the worst-case 1/w bound, because the Zipf stream is dominated by a few heavy flows), and the top flows are estimated to within 1% with 4,096 counters per row.""",
   """rules = [("10.0.0.0/8", "port1"), ("10.1.0.0/16", "port2"), ("10.1.2.0/24", "port3"), ("0.0.0.0/0", "drop")]
def ip(s): a = s.split("."); return sum(int(x) << (24 - 8 * i) for i, x in enumerate(a))
def lpm(addr):
    best = None
    for pre, act in rules:
        base, l = pre.split("/"); l = int(l); mask = (0xFFFFFFFF << (32 - l)) & 0xFFFFFFFF if l else 0
        if ip(addr) & mask == ip(base) & mask and (best is None or l > best[0]): best = (l, act)
    return best[1]
for a in ("10.1.2.7", "10.1.9.9", "10.200.0.1", "8.8.8.8"): print(a, "->", lpm(a))""",
   [("Choose CMS dimensions for ε = 0.001, δ = 0.01.", "w = ⌈e/0.001⌉ = 2719, d = ⌈ln 100⌉ = 5, i.e. about 13,600 counters."),
    ("Name two drawbacks of a logically centralised controller.", "Single point of failure/scalability and added control latency; mitigated by replicated, distributed controllers and proactive rule installation.")],
   ["McKeown et al. (2008) OpenFlow: enabling innovation in campus networks.", "Bosshart et al. (2014) P4: programming protocol-independent packet processors.", "Cormode & Muthukrishnan (2005) An improved data stream summary: the count-min sketch.", "Jain et al. (2013) B4."])
wk(10, 4, "Wireless and Mobile Networking", "MIT 6.829, Berkeley CS268, Stanford CS244",
   "Shannon capacity, fading and rate adaptation, 802.11 contention and why wireless TCP is hard.",
   ["Compute Shannon capacity for a given bandwidth and SNR.", "Explain CSMA/CA, hidden terminals and airtime fairness.", "Describe why loss-based TCP misinterprets wireless loss."],
   "C = B·log₂(1 + SNR)",
   r"""## Capacity limits
Shannon (1948): the error-free rate of a channel with bandwidth B and signal-to-noise ratio SNR is

$ C = B · log₂(1 + SNR)

!! Worked example: a 20 MHz Wi-Fi channel at 20 dB SNR (100x) has C = 20 × log₂(101) ≈ 133 Mb/s. Doubling the width doubles C; doubling power adds only +3 dB, about 1 b/s/Hz. MIMO adds spatial streams, multiplying C by min(Nt, Nr) at high SNR.

[[fig:shannon]]

## 802.11 medium access
Wi-Fi uses CSMA/CA with random backoff because radios cannot detect collisions while transmitting. Hidden terminals (A and C both reach B but not each other) are handled by optional RTS/CTS. Rate adaptation (Minstrel, SampleRate) chooses the modulation-and-coding scheme from observed delivery. The 802.11 anomaly: one slow client consuming most airtime drags down all others, which is why airtime fairness schedulers exist. OFDMA in Wi-Fi 6 divides a channel into resource units for scheduled uplink and downlink.

## Transport over wireless
Random corruption and handoff cause loss unrelated to congestion, and loss-based TCP wrongly halves its window. Link-layer retransmission, ECN/delay signals and BBR-style control help; for 5G, URLLC targets about 1 ms latency while eMBB targets Gb/s rates, with network slicing for isolation.""",
   """from math import log2
def shannon(B_mhz, snr_db): return B_mhz * log2(1 + 10 ** (snr_db / 10))
for s in (10, 20, 30): print(f"20 MHz @ {s} dB: {shannon(20, s):6.1f} Mb/s")
print("80 MHz @ 20 dB:", round(shannon(80, 20)), "Mb/s")""",
   [("Capacity of a 40 MHz channel at 30 dB?", "40 × log₂(1001) ≈ 399 Mb/s."),
    ("Why is RTS/CTS not enabled by default?", "Its overhead exceeds the collision cost for small frames; it helps mainly with long frames and hidden terminals.")],
   ["Shannon (1948) A mathematical theory of communication.", "Tse & Viswanath, Fundamentals of Wireless Communication.", "Heusse et al. (2003) Performance anomaly of 802.11b."])
wk(11, 4, "Content Delivery and Video Streaming", "Stanford CS244, CMU 15-744, Princeton COS 561",
   "CDN architecture, Zipf popularity and caching, DNS-based redirection and adaptive bitrate control.",
   ["Model cache hit ratio for Zipf-distributed demand.", "Explain DNS redirection and anycast.", "Compare throughput-based and buffer-based ABR."],
   "hit ratio = H(C,α)/H(N,α)",
   r"""## Why CDNs
Video is the majority of Internet traffic. CDNs place caches near users, cutting latency, backbone load and origin cost. Requests are steered to a cache by DNS (authoritative DNS answers by resolver location) or by anycast (same IP announced from many sites, BGP chooses the nearest).

## Caching and Zipf popularity
Web object popularity follows Zipf's law with exponent near 1 (Breslau et al. 1999): the i-th most popular object has request frequency ∝ i⁻ᵅ. An ideal cache of the C most popular items out of N has hit ratio

$ H(C,α) / H(N,α),    H(n,α) = Σ i⁻ᵅ,    i=1..n

!! Worked example: α = 1, N = 100,000. A cache holding the top 1% (1,000 objects) gets ≈ 62% hits.

[[fig:zipf]]

Long-tail content still misses, motivating hierarchical caches, consistent hashing for load spreading and prefetching.

## Adaptive bitrate (ABR)
Video is split into 2 to 6 s chunks at several bitrates (DASH/HLS). The player chooses each chunk's bitrate to avoid stalls while maximising quality. Throughput-based rules fluctuate with noisy estimates; buffer-based control (BBA, Huang et al. 2014) maps buffer occupancy to bitrate; model predictive control (MPC) and learned policies (Pensieve) optimise a QoE function combining bitrate, rebuffering and smoothness.""",
   """def H(n, a): return sum(i ** -a for i in range(1, n + 1))
N = 100000
for a in (0.8, 1.0, 1.2):
    print(f"alpha={a}: 1% cache hit ratio = {H(N // 100, a) / H(N, a):.1%}")""",
   [("Why does anycast not guarantee the closest server in latency terms?", "BGP picks by policy and AS-path length, not distance or load, so a user may reach a distant site."),
    ("In ABR, why is a conservative throughput estimate (e.g. harmonic mean) preferred to the arithmetic mean?", "Outliers of high throughput inflate the arithmetic mean and cause stalls; the harmonic mean is dominated by low values.")],
   ["Breslau et al. (1999) Web caching and Zipf-like distributions.", "Huang et al. (2014) A buffer-based approach to rate adaptation. SIGCOMM.", "Mao, Netravali, Alizadeh (2017) Neural adaptive video streaming with Pensieve."])
wk(12, 4, "Network Security: DDoS, DNS, TLS and BGP", "Stanford CS244, Berkeley CS268, CMU 15-744",
   "Reflection and amplification attacks, SYN floods, DNSSEC, TLS 1.3 and securing interdomain routing with RPKI.",
   ["Compute reflected attack bandwidth from an amplification factor.", "Explain SYN cookies and ingress filtering (BCP 38).", "Describe RPKI route-origin validation and its limits."],
   "attack bw = attacker bw × amplification",
   r"""## Reflection and amplification
Attackers send small UDP requests with a spoofed source address (the victim) to open servers that reply with large responses. The amplification factor is response size over request size.

$ attack bandwidth = attacker bandwidth × factor

[[fig:amp]]

!! Worked example: a 1 Gb/s botnet using a 50x vector hits the victim with 50 Gb/s. The 2018 memcached attack on GitHub peaked at about 1.35 Tb/s. Defences: BCP 38 ingress filtering stops spoofing at the source, rate-limiting and disabling open resolvers, and scrubbing or anycast absorption.

## SYN floods
A SYN flood fills the half-open connection table. SYN cookies encode state in the initial sequence number (a keyed hash of the 4-tuple and a timestamp), so the server stores nothing until the final ACK validates the cookie.

## Securing names and routes
DNSSEC signs records so resolvers can verify them, but gives integrity, not confidentiality (DoT/DoH provide that). TLS 1.3 removes legacy ciphers, makes forward secrecy mandatory and encrypts most of the handshake. RPKI binds IP prefixes to origin ASes with signed ROAs; routers drop origin-invalid announcements, preventing hijacks like the 2008 YouTube incident, but not path manipulation: BGPsec proposes path validation yet is barely deployed.""",
   """def attack(attacker_gbps, factor): return attacker_gbps * factor
for name, f in (("DNS", 54), ("NTP", 557), ("memcached", 51000)):
    print(f"{name:10s} 0.1 Gb/s botnet -> {attack(0.1, f):8.1f} Gb/s at victim")""",
   [("A DNS server returns a 3,000 B reply to a 60 B query. Amplification factor?", "3000/60 = 50x."),
    ("Why does RPKI not stop all hijacks?", "It validates only the origin AS; an attacker can forge the path and still appear to originate through the legitimate AS.")],
   ["Rossow (2014) Amplification hell: revisiting network protocols for DDoS abuse.", "RFC 6811 (BGP prefix origin validation), RFC 2827 (BCP 38).", "Cloudflare (2018) Memcached DDoS attack write-ups."])
wk(13, 4, "Measurement, Satellite Networks and the Future", "MIT 6.829, Stanford CS244, Berkeley CS268",
   "How the Internet is measured, LEO constellations versus fibre latency, and open research directions.",
   ["Compute propagation-limited RTTs for fibre, LEO and GEO.", "Explain active versus passive measurement and their biases.", "Identify open research problems for a course project."],
   "RTT ≥ 2·d·stretch / v",
   r"""## Measuring the Internet
Active measurement (ping, traceroute, RIPE Atlas, M-Lab NDT) injects probes; passive measurement (NetFlow, IPFIX, packet captures) observes real traffic. Pitfalls: vantage-point bias, load-balanced paths that confuse traceroute, ICMP rate limiting, and crowd-sourced speed tests that measure the access link, not the Internet.

## Propagation is a hard floor
Light in fibre travels at about 2×10⁸ m/s (c/1.5) and fibre routes are 1.5 to 2x longer than great-circle distance.

$ RTT_prop = 2 · stretch · d / v

LEO constellations (Starlink at about 550 km) use inter-satellite laser links through vacuum at c, so over long distances they can beat fibre (Handley 2018), while GEO satellites at 35,786 km impose about 480 ms of RTT from propagation alone, regardless of capacity.

[[fig:lat]]

!! Worked example: 10,000 km: fibre RTT ≈ 150 ms; LEO ≈ 80 ms; GEO ≈ 477 ms. Satellite handovers every few minutes make transport harder: BBR and CUBIC both react to the resulting RTT jumps and reordering.

## Open problems for projects
Learning-based congestion control that generalises, fair multi-flow behaviour with BBR, verification of network configurations, intent-based networking, in-network computing for ML training, energy-efficient networks, and measurement of QUIC/encrypted traffic.""",
   """def rtt_ms(d_km, kind):
    if kind == "fibre": return 2 * 1.5 * d_km / 200000 * 1000
    if kind == "leo": return 2 * (1.1 * d_km + 1100) / 300000 * 1000
    return 4 * 35786 / 300000 * 1000
for d in (1000, 5000, 10000): print(d, "km:", {k: round(rtt_ms(d, k)) for k in ("fibre", "leo", "geo")})""",
   [("At what distance does LEO beat fibre in the model above?", "Solve 3d/200000 = 2(1.1d+1100)/300000 for d: 0.015d = 0.00733d + 7.33 → d ≈ 960 km."),
    ("Why can a crowd-sourced speed test under-report a path's capacity?", "It often measures the home Wi-Fi/access link, server load, or a single TCP flow limited by loss and RTT.")],
   ["Handley (2018) Delay is not an option: low latency routing in space. HotNets.", "Bajpai & Schönwälder (2015) A survey on Internet performance measurement platforms.", "Sundaresan et al. (2011) Broadband Internet performance: a view from the gateway. SIGCOMM."])
BYN = {w["n"]: w for w in W_}
PH = {1: "Foundations", 2: "Transport & Congestion", 3: "Data Centers & Programmability", 4: "Access, Content & Security"}
mid = dict(n=8, ph=3, title="Midterm Review and Exam", src="All sources", summary="A cumulative review of Weeks 1 to 7 with a formula sheet and practice questions.",
           obj=[o for k in range(1, 8) for o in BYN[k]["obj"][:1]], key="", body="", code="", ex=[("Practice: a 100 ms RTT path with p = 10⁻⁶ and MSS 1460 B. Predict Reno throughput and compare with 10 Gb/s.", "1.22×11680/0.1/0.001 ≈ 142 Mb/s: about 1.4% of the link; loss-based Reno cannot fill it."),
           ("Practice: Why can M/M/1 delay at 95% load be 10x that at 50% load?", "W = 1/(μ−λ): (1−0.5)/(1−0.95) = 10.")], rd=["Re-read the Essential papers of Weeks 1 to 7."])
fin = dict(n=16, ph=5, title="Final Projects, Review and Exam", src="All sources", summary="Project talks, reproducibility and a final review of the whole semester.", obj=[o for k in range(9, 14) for o in BYN[k]["obj"][:1]],
           key="", body="", code="", ex=[("Practice: pick one paper from Weeks 4 to 7 and state its claim, method, a baseline you would add and one threat to validity.", "Open-ended: a good answer names a specific confound (e.g. a single topology, one seed, a buffer size favouring one scheme).")], rd=["Reproduce one SIGCOMM/NSDI paper figure with Mininet or ns-3."])
ALL = sorted(list(W_) + [mid, fin], key=lambda w: w["n"])
def srows(ws): return "".join(f"<tr><td>{w['n']}</td><td>{html.escape(w['title'])}</td><td><code>{html.escape(w['key'])}</code></td></tr>" for w in ws)
sheet = srows(W_); sheet1 = srows([w for w in W_ if w["n"] < 8])
mid["body"] = "## Formula sheet (Weeks 1 to 7)\n[[sheet1]]\n\n## Format\nA 75-minute in-class exam: five short derivations, one worked calculation per topic, and one paper-critique question. Weeks 1 to 7 only."
fin["body"] = "## Project\nTeams of 2 to 3 propose a measurement, simulation (ns-3, Mininet) or reproduction study in Week 3, submit a 6-page report and give a 10-minute talk. Rubric: question and novelty 20%, method 25%, results with baselines and error bars 30%, writing 15%, reproducibility 10%.\n\n## Full formula sheet\n[[sheet2]]\n\n## Final exam\nCumulative, with emphasis on Weeks 9 to 13: sketch sizing, Shannon capacity, Zipf caching, amplification, propagation delay."

exec(open(os.path.join(_B, 'extra.py'), encoding='utf-8').read())
exec(open(os.path.join(_B, 'deep.py'), encoding='utf-8').read())
for _f in ('book_core.py', 'book1.py', 'book2.py', 'book3.py', 'book4.py', 'book5.py', 'appendix.py', 'book_chat.py'):
    if os.path.exists(os.path.join(_B, _f)): exec(open(os.path.join(_B, _f), encoding='utf-8').read())
# ---------- rendering ----------
def inline(s): return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", re.sub(r"`(.+?)`", r"<code>\1</code>", html.escape(s)))))
def md(t):
    o, para, lst, tbl, code = [], [], [], [], None
    def fl():
        if para: o.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
        if lst: o.append(f"<{lst[0]}>" + "".join(f"<li>{inline(x)}</li>" for x in lst[1:]) + f"</{lst[0]}>"); lst.clear()
        if tbl:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl if not re.match(r"^\s*\|[\s:|-]+\|\s*$", r)]
            o.append('<div class="tw"><table><tr>' + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:]) + "</table></div>"); tbl.clear()
    for ln in t.strip().split("\n"):
        if code is not None:
            if ln.startswith("```"): o.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>"); code = None
            else: code.append(ln)
            continue
        if ln.startswith("```"): fl(); code = []
        elif ln.startswith("## "):
            fl(); h = ln[3:]; c = ' class="lv-b"' if h.startswith("Basics") else ' class="lv-a"' if h.startswith("Advanced") else ""
            o.append(f'<h2 id="{re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-")}"{c}>{inline(h)}</h2>')
        elif ln.startswith("### "): fl(); h = ln[4:]; o.append(f'<h3 id="{re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-")}">{inline(h)}</h3>')
        elif ln.startswith("$ "): fl(); o.append(f'<div class="eq">{html.escape(ln[2:])}</div>')
        elif ln.startswith("!! "): fl(); o.append(f'<div class="note">{inline(ln[3:])}</div>')
        elif ln.startswith("[[fig:"): fl(); k = ln[6:-2]; s_, c_ = FIGS[k]; o.append(f'<figure><span class="fn">Figure {FIGN[k]}</span>{s_}<figcaption>{html.escape(c_)}</figcaption></figure>')
        elif ln.startswith("[[demo:"): fl(); o.append(f'<div class="demo" data-demo="{ln[7:-2]}"></div>')
        elif ln.startswith("[[lab:"): fl(); o.append(render_labs(int(ln[6:-2])))
        elif ln.startswith("[[sheet"): fl(); o.append('<div class="tw"><table><tr><th>Wk</th><th>Topic</th><th>Key relation</th></tr>' + (sheet if ln == "[[sheet2]]" else sheet1) + "</table></div>")
        elif ln.startswith("- "):
            if tbl or para or (lst and lst[0] != "ul"): fl()
            if not lst: lst.append("ul")
            lst.append(ln[2:])
        elif re.match(r"^\d+\. ", ln):
            if tbl or para or (lst and lst[0] != "ol"): fl()
            if not lst: lst.append("ol")
            lst.append(re.sub(r"^\d+\. ", "", ln))
        elif ln.startswith("|"):
            if para or lst: fl()
            tbl.append(ln)
        elif not ln.strip(): fl()
        else:
            if lst or tbl: fl()
            para.append(ln)
    fl(); return "\n".join(o)
LABS = globals().get('LABS', {})
def render_labs(n):
    r = ""
    for i, (title, desc, code) in enumerate(LABS.get(n, [])):
        r += f'<h3 id="lab-{n}-{i+1}">Lab {n}.{i+1}: {html.escape(title)}</h3><p>{inline(desc)}</p><pre><code>{html.escape(code)}</code></pre><div class="out"><b>Output</b><pre>{html.escape(run(code))}</pre></div>'
    return r
FIGN = {}
for n, k in enumerate(FIGS, 1): FIGN[k] = n
def run(code):
    b = io.StringIO()
    with contextlib.redirect_stdout(b): exec(code, {})
    return b.getvalue().strip()
def sidebar(cur):
    o = ['<input id="q" placeholder="Search topics ( / )" aria-label="Search"><nav>', f'<a href="index.html" class="{"on" if cur=="home" else ""}">Home</a><a href="syllabus.html" class="{"on" if cur=="syl" else ""}">Syllabus</a><a href="glossary.html" class="{"on" if cur=="glo" else ""}">Glossary</a><a href="reading.html" class="{"on" if cur=="rd" else ""}">Reading list</a><a href="assignments.html" class="{"on" if cur=="as" else ""}">Assignments</a><a href="chatbot.html" class="{"on" if cur=="chat" else ""}">Ask the course (chatbot)</a>']
    for p in PH:
        o.append(f'<h4>{p} · {PH[p]}</h4>')
        for w in ALL:
            if w["ph"] == p: o.append(f'<a data-w="{w["n"]}" href="week-{w["n"]:02d}.html" class="{"on" if cur==w["n"] else ""}"><span>{w["n"]:02d}</span>{html.escape(w["title"])}</a>')
    ap = globals().get("APPX", [])
    if ap: o.append("<h4>Appendices</h4>" + "".join(f'<a href="{k}.html" class="{"on" if cur==k else ""}">{html.escape(t)}</a>' for k, t, _ in ap))
    o.append('<h4>Downloads</h4><a href="downloads.html" class="' + ("on" if cur == "dl" else "") + '">PDFs and lab files</a>')
    return "".join(o) + "</nav>"
def page(fn, title, cur, body, desc=""):
    open(f"{OUT}/{fn}", "w", encoding="utf-8").write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | Advanced Computer Networks</title><meta name="description" content="{html.escape(desc)}"><link rel="stylesheet" href="assets/style.css"></head><body><aside><a class="brand" href="index.html">Advanced Computer Networks</a>{sidebar(cur)}</aside><main>{body}<footer>Open course · Text and figures CC BY 4.0 · code MIT.</footer></main><script src="assets/app.js"></script><script src="assets/demos.js"></script><script src="assets/chatbot-config.js"></script><script src="assets/chatbot.js" defer></script></body></html>')
PB = {}; words = 0; nex = 0; nfig = len(FIGS)
for w in ALL:
    nav = ""
    if w["n"] > 1: p_ = BYN.get(w["n"] - 1, mid if w["n"] - 1 == 8 else None) or next(x for x in ALL if x["n"] == w["n"] - 1); nav += f'<a href="week-{p_["n"]:02d}.html">← Week {p_["n"]}: {html.escape(p_["title"])}</a>'
    if w["n"] < 16: n_ = next(x for x in ALL if x["n"] == w["n"] + 1); nav += f'<a class="r" href="week-{n_["n"]:02d}.html">Week {n_["n"]}: {html.escape(n_["title"])} →</a>'
    b = f'<div class="kick">Week {w["n"]} · Phase {w["ph"]}: {PH[w["ph"]]}</div><h1>{html.escape(w["title"])}</h1><p class="lead">{html.escape(w["summary"])}</p><p class="meta">Based on: {html.escape(w["src"])}</p>'
    b += '<div class="box"><b>Learning objectives</b><ul>' + "".join(f"<li>{html.escape(o)}</li>" for o in w["obj"]) + "</ul></div><!--TOC-->" + md(w["body"])
    if w["code"]: b += f'<h2 id="lab">Code lab (runs as-is in Python 3)</h2><pre><code>{html.escape(w["code"])}</code></pre><div class="out"><b>Output</b><pre>{html.escape(run(w["code"]))}</pre></div>'
    b += '<h2 id="exercises">Exercises</h2>' + "".join(f"<details><summary>Exercise {i+1}: {inline(q)}</summary><p>{inline(a)}</p></details>" for i, (q, a) in enumerate(w["ex"]))
    if w["key"]: b += f'<h2 id="takeaway">Key takeaway</h2><div class="note">{html.escape(w["key"])}</div>'
    b += '<h2 id="reading">Further reading</h2><ul>' + "".join(f"<li>{html.escape(r)}</li>" for r in w["rd"]) + "</ul>"
    _t = re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', b); b = b.replace("<!--TOC-->", '<div class="toc"><b>On this page</b>' + "".join(f'<a href="#{i}">{t}</a>' for i, t in _t) + "</div>"); PB[w["n"]] = b
    b += f'<button id="done" data-w="{w["n"]}">Mark week {w["n"]} as complete</button><div class="pn">{nav}</div>'
    words += len(re.findall(r"\w+", b)); nex += len(w["ex"])
    page(f'week-{w["n"]:02d}.html', f'Week {w["n"]}: {w["title"]}', w["n"], b, w["summary"])
cards = "".join(f'<a class="card" href="week-{w["n"]:02d}.html"><span>{w["n"]:02d}</span><b>{html.escape(w["title"])}</b><p>{html.escape(w["summary"])}</p></a>' for w in ALL)
phs = "".join(f'<div><h3>Phase {p}: {PH[p]}</h3><p>Weeks ' + ", ".join(str(w["n"]) for w in ALL if w["ph"] == p) + "</p></div>" for p in PH)
home = f'<div class="kick">Open course · MS level · 16 weeks</div><h1>Understand networks the way they are <i>actually</i> built.</h1><p class="lead">A graduate course in advanced computer networking: from queueing and routing to congestion control, QUIC, data centers, SDN, wireless, CDNs, security and satellites. Each chapter runs from the basics to advanced material, with derivations, worked examples, computed charts, interactive demos, runnable labs, exercises with solutions, a programming assignment and a paper-reading guide. Appendices cover the maths, networking fundamentals and lab tools, and every chapter is available as a PDF.</p><p><a class="btn" href="week-01.html">Start with Week 1</a> <a class="btn alt" href="syllabus.html">View the syllabus</a> <a class="btn alt" href="chatbot.html">Ask the course chatbot</a></p><div class="stats"><div><b>16</b>weeks</div><div><b>{nfig}</b>computed figures</div><div><b>{sum(1 for w in W_ if w["code"]) + sum(len(v) for v in LABS.values())}</b>runnable labs</div><div><b>{nex}</b>exercises with solutions</div></div><div class="phases">{phs}</div><h2>All weeks</h2><div class="cards">{cards}</div><h2>How to study</h2><ol><li>Read each derivation and try the worked example on paper first.</li><li>Run every lab and change one parameter at a time.</li><li>Do the exercises before opening the solutions.</li><li>Read the Essential papers: networking is a paper-driven field.</li></ol><p><b>Prerequisites:</b> an undergraduate networking course (TCP/IP), probability, Python.</p>'
page("index.html", "Home", "home", home, "Open graduate course in advanced computer networks.")
rows = "".join(f'<tr><td>{w["n"]}</td><td><a href="week-{w["n"]:02d}.html">{html.escape(w["title"])}</a></td><td>{html.escape(w["src"])}</td></tr>' for w in ALL)
page("syllabus.html", "Syllabus", "syl", f'<h1>Syllabus</h1><p class="lead">16 weeks, two lectures plus one lab or discussion per week. Grading: problem sets 25%, midterm (Week 8) 20%, paper critiques 15%, project 25%, final 15%.</p><table><tr><th>Wk</th><th>Topic</th><th>Informed by</th></tr>{rows}</table><div class="note">The outline was synthesised from the publicly known structure of Stanford CS244/CS144, MIT 6.829, CMU 15-744, UC Berkeley CS268 and Princeton COS 461/561. Check each university\'s current syllabus page for their latest reading lists.</div>')
GL = {"AIMD": "Additive-increase, multiplicative-decrease window control.", "BDP": "Bandwidth-delay product: data in flight to fill a path.", "BGP": "Border Gateway Protocol, the interdomain path-vector protocol.", "Bufferbloat": "Excess queueing delay from oversized buffers.", "CDN": "Content delivery network of distributed caches.", "cwnd": "Congestion window: sender's limit on unacknowledged data.", "ECMP": "Equal-cost multipath: hash flows over equal-cost routes.", "ECN": "Explicit congestion notification: marks instead of drops.", "Incast": "Throughput collapse when many senders answer one receiver.", "Little's law": "L = λW.", "P4": "Language for programming switch data planes.", "QUIC": "Encrypted, multiplexed transport over UDP.", "RPKI": "Public-key infrastructure that authenticates prefix origins.", "SDN": "Software-defined networking: separate control and data planes.", "Sketch": "Small probabilistic summary of a data stream."}
GL.update(globals().get("GL_EXTRA", {}))
page("glossary.html", "Glossary", "glo", "<h1>Glossary</h1><dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in sorted(GL.items())) + "</dl>")
open(OUT + "/assets/style.css", "w").write("""*{box-sizing:border-box}body{margin:0;font:17px/1.65 Georgia,'Times New Roman',serif;background:#faf7f2;color:#222;display:flex}aside{width:300px;height:100vh;position:sticky;top:0;overflow:auto;padding:18px;border-right:1px solid #e3ddd0;background:#f3eee4;font:14px/1.35 system-ui,sans-serif;flex:none}.brand{font:700 18px Georgia;color:#1f6f78;text-decoration:none;display:block;margin-bottom:10px}#q{width:100%;padding:7px;border:1px solid #cfc7b6;border-radius:6px;margin-bottom:8px}nav a{display:block;padding:5px 6px;color:#333;text-decoration:none;border-radius:5px}nav a span{color:#999;margin-right:8px;font-variant-numeric:tabular-nums}nav a:hover,nav a.on{background:#e4dccb}nav a.done::after{content:' ✓';color:#1f6f78}h4{margin:14px 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#8a7f68}main{max-width:820px;padding:36px 44px;flex:1;min-width:0}h1{font-size:2.3rem;line-height:1.15;margin:.2em 0}h2{margin-top:2em;border-bottom:1px solid #e3ddd0;padding-bottom:4px}.kick{font:600 13px system-ui;color:#c0562b;text-transform:uppercase;letter-spacing:.06em}.lead{font-size:1.15rem;color:#444}.meta{font:13px system-ui;color:#888}.box,.note,.out{background:#fff;border:1px solid #e3ddd0;border-left:4px solid #1f6f78;padding:10px 16px;border-radius:6px;margin:1em 0}.note{border-left-color:#c0562b}.eq{font:italic 1.05rem 'Cambria Math',Georgia,serif;text-align:center;background:#fff;padding:10px;border-radius:6px;margin:1em 0;overflow-x:auto}pre{background:#23272e;color:#e8e6df;padding:14px;border-radius:8px;overflow:auto;font-size:14px;line-height:1.45}.out pre{background:#f1ede3;color:#222}code{font-family:ui-monospace,Menlo,monospace;font-size:.88em;background:#eee8da;padding:1px 5px;border-radius:4px}pre code{background:none;padding:0}figure{margin:1.6em 0;background:#fff;border:1px solid #e3ddd0;border-radius:8px;padding:10px}figure svg{width:100%;height:auto;font:12px system-ui;fill:#555}figure .g{stroke:#e6e1d4}figure .ax{stroke:#555}figure .al{font-size:13px;fill:#222}figure .lg{font-size:12px;font-weight:600}.fn{font:700 12px system-ui;color:#1f6f78}figcaption{font:14px/1.4 system-ui;color:#555;margin-top:6px}table{border-collapse:collapse;width:100%;font:15px system-ui;margin:1em 0}td,th{border:1px solid #e3ddd0;padding:7px 10px;text-align:left}th{background:#efe9dc}details{background:#fff;border:1px solid #e3ddd0;border-radius:6px;padding:8px 14px;margin:8px 0}summary{cursor:pointer;font-weight:600}button,.btn{background:#1f6f78;color:#fff;border:0;padding:10px 18px;border-radius:7px;font:600 15px system-ui;cursor:pointer;text-decoration:none;display:inline-block}.btn.alt{background:#fff;color:#1f6f78;border:1px solid #1f6f78}.stats{display:flex;gap:14px;flex-wrap:wrap;margin:24px 0}.stats div{flex:1;min-width:120px;background:#fff;border:1px solid #e3ddd0;border-radius:8px;padding:12px;font:13px system-ui;color:#666}.stats b{display:block;font:700 28px Georgia;color:#c0562b}.phases{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.phases div{background:#fff;border:1px solid #e3ddd0;border-radius:8px;padding:4px 14px}.phases h3{font-size:1rem}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}.card{display:block;background:#fff;border:1px solid #e3ddd0;border-radius:8px;padding:12px 14px;color:#222;text-decoration:none}.card span{font:700 13px system-ui;color:#c0562b}.card b{display:block}.card p{font:13.5px/1.4 system-ui;color:#666;margin:6px 0 0}.card:hover{border-color:#1f6f78}.pn{display:flex;justify-content:space-between;gap:12px;margin-top:28px;font:14px system-ui}.pn a{color:#1f6f78}dt{font-weight:700;margin-top:10px}dd{margin-left:0;color:#444}footer{margin-top:50px;font:13px system-ui;color:#999}@media(max-width:900px){body{display:block}aside{width:auto;height:auto;position:static}main{padding:22px}}""" + globals().get("CSS_EXTRA", ""))
open(OUT + "/assets/app.js", "w").write("""(function(){var K='acn-done',d=[];try{d=JSON.parse(localStorage.getItem(K)||'[]')}catch(e){}
function paint(){document.querySelectorAll('nav a[data-w]').forEach(function(a){a.classList.toggle('done',d.indexOf(a.dataset.w)>-1)});var b=document.getElementById('done');if(b){var x=d.indexOf(b.dataset.w)>-1;b.textContent=x?'Completed ✓ (click to undo)':'Mark week '+b.dataset.w+' as complete'}}
var b=document.getElementById('done');if(b)b.onclick=function(){var w=b.dataset.w,i=d.indexOf(w);i>-1?d.splice(i,1):d.push(w);try{localStorage.setItem(K,JSON.stringify(d))}catch(e){}paint()};paint();
var q=document.getElementById('q');q.oninput=function(){var s=q.value.toLowerCase();document.querySelectorAll('nav a').forEach(function(a){a.style.display=a.textContent.toLowerCase().indexOf(s)>-1?'':'none'})};
document.addEventListener('keydown',function(e){if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus()}})})();""")
open(OUT + "/README.md", "w").write("# Advanced Computer Networks: open course\nOpen `index.html` in a browser, or publish this folder with GitHub Pages. Offline material: `pdf/` (chapter PDFs, complete notes, reference cards) and `labs/` (runnable lab scripts and notebooks, Mininet labs).\nChatbot: a floating Ask-the-course button on every page and `chatbot.html`; it searches an index of the whole site (`assets/chatbot-data.js`, regenerated on every build) and runs fully in the browser with no server. RAG answers: retrieval picks the relevant passages and an AI model (in-browser WebGPU model, your cloud proxy in `worker/`, or any OpenAI-compatible endpoint such as Ollama) writes a cited answer from them; choose the mode with the AI mode button, or set the site default with `ACN_PROXY_URL=... python build.py` (see `worker/README.md`). Tests: `source/tests/README.md`.\nRebuild: `cd source && python build.py` (Python 3.12+; the PDF step needs `pip install weasyprint`, everything else is pure Python). Course text lives in `source/build.py` (core), `extra.py`, `deep.py`, `book1-5.py` (basics, advanced sections, labs), `appendix.py`; the chatbot in `book_chat.py`.\n")
post()
print("pages:", len(ALL) + 5, "figures:", nfig, "words:", words)
