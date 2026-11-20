# ---------------- Week 1 ----------------
LAB(1, "A packet pipeline simulator", "Simulate store-and-forward over N equal links and compare with the closed-form (N+P−1)·L/R + N·prop. Then see which delay component dominates as the link gets faster.", """
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
""")
LAB(1, "Statistical multiplexing and network calculus", "How many bursty users can share a link, and what worst-case delay does a token-bucket flow see through a rate-latency server?", """
from math import comb
n, p, cap = 35, 0.1, 10
tail = sum(comb(n, k) * p**k * (1 - p)**(n - k) for k in range(cap + 1, n + 1))
print(f"{n} users active {p:.0%} of the time on a link that fits {cap}: P(overload) = {tail:.4%}")
print("circuit switching would admit only", cap, "users")
sigma, rho, R, T = 80_000, 5e6, 10e6, 0.001      # burst (bits), rate (b/s), service rate, latency (s)
print("delay bound   :", round((T + sigma / R) * 1000, 2), "ms")
print("backlog bound :", round((sigma + rho * T) / 8), "bytes")
""")
deepen(1, r"""
## Basics: what a network delivers
Before any protocol, understand the three numbers that describe every network path. **Latency** is how long one bit (or packet) takes to arrive. **Throughput** (or bandwidth) is how many bits per second can be sent. **Loss** is the fraction of packets that never arrive. A common mistake is to treat these as one thing: a satellite link can have enormous throughput and terrible latency, and a short wireless hop can have low latency but high loss.

### The four delays, with a highway analogy
Imagine a convoy of 10 cars (a packet) driving through a toll booth to a town 100 km away (one network hop).
- **Transmission delay (L/R):** the toll booth lets one car through every 12 seconds; releasing all 10 cars takes 120 seconds. This is the packet length divided by the link rate. Faster links shrink it.
- **Propagation delay (d/v):** each car then drives 100 km at its speed. This depends only on distance and the medium, never on the booth. In fibre signals travel at about 2×10⁸ m/s, which is 5 µs per kilometre.
- **Queueing delay:** if other convoys are waiting at the booth, you wait. It varies packet by packet and is the only delay that is random.
- **Processing delay:** the booth operator checks your papers (reads the header and looks up the route), usually microseconds.

!! Quick check: a 1500 B packet on a 100 Mb/s link, 2,000 km of fibre. Transmission 120 µs; propagation 2,000 × 5 µs = 10 ms. Propagation is about 80 times larger, so a faster link would not help this packet at all.

### Circuit switching versus packet switching
The telephone network reserved a fixed-rate circuit for each call: simple, predictable, but wasteful because a silent call still holds its capacity. The Internet instead cuts data into packets and lets all flows share links on demand (**statistical multiplexing**). Because most users are idle most of the time, a link shared by packets can serve many more users. The first lab computes it: with 35 users who are each active 10% of the time on a link that fits 10 active users, overload is very rare, yet circuit switching would admit only 10. The price is that packets sometimes queue or are dropped, which is why congestion control exists.

### Bandwidth-delay product, intuitively
Think of a pipe. Its width is the bandwidth and its length is the delay. The BDP is the volume of the pipe, the number of bits that must be in flight to keep it full. A sender that waits for an acknowledgment after every packet uses only one packet per round trip, a tiny fraction of the pipe on long paths. That one idea explains windows, pipelining and most of transport-layer design.

### Self-check
Which delay grows with distance but not with link rate? Which grows with load? Why can a faster link not reduce the time of a 1 KB request across the Atlantic much?
""", r"""
## Advanced: design principles and their tensions
The architecture rests on a few principles, each with a cost.

- **Fate-sharing** (Clark 1988): keep a connection's state in the endpoints that use it, so the connection survives router failures. The cost is that the network cannot help with things that need per-flow state, such as fairness or accounting.
- **Soft state:** state in the network that expires unless refreshed (DNS caches, RSVP, ARP). It tolerates failures without explicit cleanup but adds refresh traffic and staleness.
- **The robustness principle** ('be conservative in what you send, liberal in what you accept') made early interoperability easy but encouraged sloppy implementations that later became de facto standards; RFC 9413 (2023) argues for a more careful reading.
- **Tussle** (Clark et al. 2002): the Internet is shared by parties with conflicting interests (users, ISPs, governments, advertisers), so designs should isolate tussles rather than hard-wire one party's preference.
- **Ossification:** once middleboxes depend on header fields, those fields cannot change. This is why QUIC encrypts its headers (Week 6) and why new IP options rarely work. Deployment, not invention, is the bottleneck.

## Advanced: network calculus, deterministic performance bounds
Queueing theory gives averages under probabilistic assumptions. Network calculus (Cruz; Le Boudec and Thiran) gives worst-case guarantees under deterministic ones. A flow is described by an **arrival curve** α(t) = σ + ρ·t (a token bucket: burst σ bits, long-term rate ρ). A server is described by a **service curve** β(t) = R·(t − T)⁺ (a rate-latency server: it serves at rate R after a latency T). If ρ ≤ R then

$ delay ≤ T + σ/R,      backlog ≤ σ + ρ·T,      output burstiness ≤ σ + ρ·T

The bounds are the maximum horizontal and vertical distances between α and β. Two rate-latency servers in tandem combine into one with rate min(R₁,R₂) and latency T₁+T₂, so the burst σ is paid for only once, not at every hop ('pay bursts only once'). This is why per-flow guarantees (IntServ, time-sensitive networking in cars and factories) can be computed without simulation.

!! Worked example: σ = 80,000 bits, ρ = 5 Mb/s through a server with R = 10 Mb/s and T = 1 ms. Delay ≤ 1 ms + 80,000/10⁷ s = 9 ms. Backlog ≤ 80,000 + 5,000 = 85,000 bits ≈ 10.6 KB. The lab reproduces both numbers.

## Advanced: why evolvability matters
IPv6 (specified 1998) is still being deployed; IP multicast never reached the global Internet because it needed per-group state in every router and had no business model; ECN took about 20 years to see broad use. In contrast, protocols that deploy at the edge or inside applications (HTTPS, QUIC, BBR) spread in months. The lesson for protocol design is to ask, before technical merit, who must change and what do they gain.
""")

# ---------------- Week 2 ----------------
LAB(2, "Queue simulation with the Lindley recursion", "The waiting time of the next packet is W' = max(0, W + S − A), where S is the service time and A the next inter-arrival time. This three-line recursion simulates any single-server FIFO queue, so we can test M/M/1 theory and then break its assumptions with bursty (Pareto) arrivals.", """
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
""")
LAB(2, "Erlang-B and tandem queues", "Circuit-style resource dimensioning (how many channels for a given blocking probability) and the product-form result for queues in series.", """
def erlang_b(E, m):
    b = 1.0
    for k in range(1, m + 1): b = E * b / (k + E * b)
    return b
E = 10
m = next(m for m in range(1, 200) if erlang_b(E, m) < 0.01)
print(f"{E} Erlangs of offered load needs {m} channels for <1% blocking (B = {erlang_b(E, m):.4f})")
lam, mu = 500, 1000
print("3 tandem M/M/1 hops:", round(3 * 1000 / (mu - lam), 1), "ms in total (Burke + Jackson: each hop behaves as an independent M/M/1)")
""")
deepen(2, r"""
## Basics: what a queue is and why it matters
A queue forms whenever work arrives faster than it can be served, even briefly. A router output port is the textbook case: packets arrive from several inputs, but the link sends one at a time. If two packets arrive together, one waits.

### Vocabulary
- **Arrival rate λ** (packets/s) and **service rate μ** (packets/s the link can send). The average service time is 1/μ.
- **Utilisation ρ = λ/μ**: the fraction of time the server is busy. If ρ ≥ 1 the queue grows without bound.
- **Kendall notation A/S/c/K**: arrival process / service process / number of servers / buffer size. M means Markovian (Poisson arrivals, exponential service), D deterministic, G general. M/M/1 is one server, Poisson arrivals, exponential service times.

### Why queues build even below capacity
Suppose packets arrive exactly every 1 ms and take 0.8 ms to send (ρ = 0.8). Nothing ever waits. Now suppose the same average rate but packets come in pairs every 2 ms: the second packet of each pair waits 0.8 ms. Same utilisation, different delay: **burstiness**, not average load alone, creates queueing. This is why a link at 80% utilisation can feel perfectly fine on average and still produce latency spikes.

### Reading the M/M/1 delay curve
The mean time in system is W = 1/(μ − λ). At ρ = 0.5 it is two service times, at ρ = 0.9 ten service times, at ρ = 0.99 one hundred. The curve is gentle until about 70% load and then bends sharply upward, which is why operators plan to keep important links below that range.

### Little's law in everyday terms
If a coffee shop serves 30 customers an hour and each stays 20 minutes, there are 30 × (1/3) = 10 people inside on average. L = λW holds for any stable system; use it to move between average queue length and average waiting time.

### Self-check
If utilisation doubles from 40% to 80%, by what factor does M/M/1 delay grow? (Answer: W ∝ 1/(1−ρ): from 1/0.6 to 1/0.2, a factor of 3.)
""", r"""
## Advanced: M/G/1, priorities and heavy tails
**Pollaczek-Khinchine.** For Poisson arrivals and general service time S with mean E[S] and second moment E[S²], the mean waiting time in queue is

$ W_q = λ·E[S²] / (2·(1 − ρ)),     ρ = λ·E[S]

Waiting depends on the variability of service, not just its mean: with the squared coefficient of variation c² = Var(S)/E[S]², W_q = ρ·E[S]·(1 + c²) / (2(1−ρ)). Deterministic service (c² = 0) halves the M/M/1 wait (c² = 1); mixed packet sizes (c² > 1) make it worse.

**Priority queueing.** With two classes under non-preemptive priority, high-priority packets wait only for the packet in service plus other high-priority packets, so their delay is nearly independent of low-priority load; the low class absorbs the congestion. Preemptive priority makes the high class see an M/G/1 queue of its own. Weighted fair queueing and deficit round robin approximate generalised processor sharing and give each class a guaranteed share while remaining work-conserving.

**Tandem queues and product form.** Burke's theorem says the departure process of a stable M/M/1 queue is Poisson with the same rate, so a chain of M/M/1 queues behaves as independent queues and mean delays add (Jackson networks). Real networks violate this (Kleinrock's independence assumption fails when packet sizes are preserved across hops) but it remains a useful approximation.

**Heavy tails and long-range dependence.** If service or ON-period lengths are Pareto with shape α ∈ (1,2), the queue length has a polynomial rather than exponential tail: P(Q > x) decays like x^(−(α−1)) in the fluid limit. Aggregates of such ON/OFF sources are self-similar with Hurst parameter H = (3 − α)/2 (Taqqu et al.), which explains why Paxson and Floyd observed burstiness at every time scale. Practical consequence: average-based dimensioning underestimates tail latency, and buffers cannot be sized from mean-value formulas. The first lab shows Pareto arrivals producing much larger delays than the M/M/1 formula at the same load.

**Fluid and diffusion approximations.** For large systems it is easier to analyse the queue as a continuous fluid, Q(t) = sup over s ≤ t of the net input A(s,t) − C·(t−s) (the Lindley/Reich formula). Heavy-traffic analysis shows that as ρ → 1 the queue behaves like a reflected Brownian motion whose mean is about σ²/(2(μ−λ)), where σ² is the variance rate of the net input (Kingman's bound has the same shape), which again shows that variance, not only the mean, controls delay.

**Loss systems.** For circuits with no waiting room the Erlang-B formula gives the blocking probability of m channels offered E = λ/μ Erlangs: B(E, m) = (E^m/m!) / Σₖ₌₀ᵐ Eᵏ/k!, computed stably by B(m) = E·B(m−1) / (m + E·B(m−1)). It is the basis of telephony dimensioning and of call-admission control; the second lab finds the number of channels needed for 1% blocking.
""")

# ---------------- Week 3 ----------------
LAB(3, "Distance-vector count-to-infinity", "Replay the classic two-router failure and measure how many exchanges it takes with and without poisoned reverse.", """
INF = 16
def count_to_infinity(poison):
    a, b = 2, INF          # B just lost its direct route to C (cost 1); A still believes 'B can reach C' (cost 2)
    msgs = 0
    while not (a >= INF and b >= INF):
        # A advertises its cost to B; with poison reverse A reports INF because A's next hop is B
        adv_a = INF if poison else a
        nb = min(INF, adv_a + 1); msgs += 1
        if nb == b and poison: break
        b = nb
        adv_b = INF if poison else b
        a = min(INF, adv_b + 1); msgs += 1
    return a, b, msgs
for poison in (False, True):
    print("poisoned reverse" if poison else "plain DV         ", "-> final costs (A,B) and messages:", count_to_infinity(poison))
""")
LAB(3, "The BGP decision process", "A toy router with candidate routes to one prefix. BGP prefers (1) highest local preference, (2) shortest AS path, (3) lowest origin type, (4) lowest MED (same neighbour AS), (5) eBGP over iBGP, (6) lowest IGP cost to next hop, (7) lowest router ID.", """
routes = [
    dict(via="provider-1", lp=100, aspath=[701, 3356, 15169], origin=0, med=0, ebgp=True, igp=10, rid="1.1.1.1"),
    dict(via="peer-1",     lp=200, aspath=[2914, 15169],       origin=0, med=0, ebgp=True, igp=20, rid="2.2.2.2"),
    dict(via="customer-1", lp=300, aspath=[64500, 64501, 64502, 15169], origin=0, med=0, ebgp=True, igp=5, rid="3.3.3.3"),
]
def key(r): return (-r["lp"], len(r["aspath"]), r["origin"], r["med"], not r["ebgp"], r["igp"], r["rid"])
for r in sorted(routes, key=key): print(f"{r['via']:11s} lp={r['lp']} path_len={len(r['aspath'])}")
print("best:", min(routes, key=key)["via"], "(local-pref encodes business policy and overrides path length)")
""")
LAB(3, "Valley-free path checker", "Check whether an AS path respects Gao-Rexford export rules, given relationship labels between consecutive ASes.", """
# 'c2p' = customer->provider (going up), 'p2p' = peer, 'p2c' = provider->customer (going down)
def valley_free(rels):
    phase = 0                      # 0 = climbing, 1 = crossed the single peer link, 2 = descending
    for r in rels:
        if r == "c2p":
            if phase != 0: return False
        elif r == "p2p":
            if phase != 0: return False
            phase = 1
        else: phase = 2
    return True
tests = {"up,peer,down": ["c2p", "p2p", "p2c"], "up,up,down": ["c2p", "c2p", "p2c"], "down,up (valley)": ["p2c", "c2p"], "two peers": ["p2p", "p2p"]}
for name, rels in tests.items(): print(f"{name:18s} valley-free: {valley_free(rels)}")
""")
deepen(3, r"""
## Basics: how routers find paths
A router has one job per packet: choose the outgoing link. It does so with a **forwarding table** mapping destination prefixes to next hops. The table is filled by a **routing protocol**, which is the distributed algorithm by which routers learn the network. Keep the two ideas apart: *forwarding* is the fast per-packet lookup; *routing* is the slower process that computes the table.

### The network as a graph
Routers are nodes, links are edges, and each edge has a **cost** (hop count, delay, or an administrator's weight). The routing goal is usually the lowest-cost path from every router to every destination.

### Dijkstra, step by step
Dijkstra's algorithm grows a set of settled nodes outward from the source. Keep a distance estimate for every node, initially ∞ (0 for the source). Repeatedly pick the unsettled node with the smallest estimate, settle it, and relax each of its edges: if going through it gives a shorter distance to a neighbour, update the neighbour. On the example graph A–B (2), A–C (5), B–C (1), B–D (4), C–D (1): from A, B is settled at 2; relaxing gives C = 3 (via B) which beats 5; settle C at 3; relax gives D = 4 (via C). The shortest path to D is A, B, C, D with cost 4. With a heap the cost is O(E log V).

### Two families of protocols
- **Link-state** (OSPF, IS-IS): every router floods its local links to everyone, so everyone has the same map and runs Dijkstra. Fast and loop-free once flooding completes, but each router stores the whole map.
- **Distance-vector** (RIP): each router tells its neighbours its current distance to every destination and applies d(x,y) = min over neighbours of c(x,v) + d(v,y). Simple and light, but slow to converge and vulnerable to count-to-infinity.

### Why the Internet needs two levels
No single protocol can scale to hundreds of thousands of networks owned by competing companies. So the Internet is split into **autonomous systems (ASes)**, each run by one organisation. Inside an AS an **interior gateway protocol** (OSPF/IS-IS) finds the best paths. Between ASes the **Border Gateway Protocol (BGP)** exchanges reachability, and each AS applies its own business policy: which neighbours it prefers, which routes it will announce to whom. BGP therefore selects *policy-preferred* paths, not necessarily the shortest.

### Self-check
What is the difference between routing and forwarding? Why does a router that learns a /16 and a /24 for the same area use the /24? What does an AS path list contain? (Answer: the sequence of ASes the announcement crossed.)
""", r"""
## Advanced: link-state in practice
OSPF organises a large AS into **areas**. Area 0 is the backbone; area border routers summarise routes between areas, limiting flooding and SPF runs to the area. Each router originates a router-LSA describing its links; designated routers on broadcast LANs reduce adjacency count from O(n²) to O(n). Convergence time is the sum of failure detection (BFD can detect in tens of milliseconds, versus seconds for hello timers), LSA flooding, SPF computation (with throttling timers to avoid churn) and FIB update. Equal-cost multipath installs several next hops and a flow-hash chooses among them. **Loop-free alternates** and MPLS fast reroute pre-compute a backup next hop so forwarding can switch in under 50 ms before the protocol reconverges; micro-loops during reconvergence are avoided with ordered FIB updates or segment-routing based protection.

## Advanced: BGP mechanics
**eBGP and iBGP.** eBGP runs between ASes and prepends the local AS to the path. iBGP distributes external routes inside an AS; to avoid loops iBGP does not re-advertise routes learned from one iBGP peer to another, so ASes need a full mesh or **route reflectors** (which can cause persistent oscillations and inconsistent views if misconfigured, as Griffin and Wilfong analysed).

**Attributes.** LOCAL_PREF (inside the AS, encodes business preference: customer > peer > provider is the usual setting), AS_PATH (loop prevention and a length metric), MED (a hint to a neighbour about the preferred entry point), ORIGIN, NEXT_HOP and **communities** (tags that signal policy, such as 'do not export to peers' or 'blackhole this prefix'). The decision process is the ordered list implemented in the second lab; note that the AS-path length comes second, so local preference lets business policy override performance.

**Stability.** Griffin, Shepherd and Wilfong showed that policy-rich BGP can have no stable solution (the 'bad gadget') or several (wedgies). Gao and Rexford proved that if every AS ranks customer routes above peer and provider routes and exports peer or provider routes only to customers, the system converges and all paths are valley-free; the third lab checks the valley-free property.

**Convergence.** After a withdrawal, routers may explore many longer alternatives before concluding a prefix is gone (path exploration); in the worst case the number of messages grows factorially in clique size, and Labovitz et al. measured minutes of delay in practice. The MRAI timer, route flap damping, and recent proposals such as consistent-assertions or ghost-flushing reduce churn.

**Security incidents.** Prefix hijacks (YouTube/Pakistan Telecom 2008), route leaks (a mid-size provider re-announcing customer routes to its peers caused a large 2019 outage affecting major content providers) and mistaken originations show why RPKI origin validation, ASPA (path verification of customer-provider relationships) and IRR-based filtering matter (Week 12).

## Advanced: scaling and traffic engineering at the edge
The IPv4 table has about a million prefixes, so routers use TCAM or algorithmic LPM structures such as multibit tries and Poptrie; the lookup cost is an engineering constraint on how deaggregation is tolerated. Operators steer traffic with prefix deaggregation, AS-path prepending (lengthen the path to repel traffic), selective announcement and communities; these tools are blunt, which is one motivation for the centralised WAN traffic engineering covered in Week 15 and for programmable data planes in Week 9.
""")

# ---------------- Week 4 ----------------
LAB(4, "AIMD with several flows: fairness and RTT bias", "Synchronised AIMD flows share a bottleneck of 1000 packets/s. Window growth is 1 packet per RTT, and all flows halve when the aggregate rate exceeds capacity. Jain's index J = (Σx)²/(n·Σx²) is 1 for perfect fairness.", """
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
""")
LAB(4, "Fluid model of Reno", "Integrate dW/dt = 1/R − (W/2)·(W/R)·p and compare the equilibrium window with √(2/p) (fluid model) and √(8/(3p)) (sawtooth model).", """
import math
def fluid(p, R=0.1, T=300.0, dt=0.001):
    W = 1.0
    for _ in range(int(T / dt)): W += dt * (1 / R - (W / 2) * (W / R) * p)
    return W
print("loss p   fluid sim   sqrt(2/p)   sqrt(8/3p) (sawtooth peak)")
for p in (1e-2, 1e-3, 1e-4): print(f"{p:7.0e} {fluid(p):10.1f} {math.sqrt(2 / p):11.1f} {math.sqrt(8 / (3 * p)):11.1f}")
""")
deepen(4, r"""
## Basics: why the network needs congestion control
Suppose every sender transmits as fast as it likes. Packets overflow router buffers and are dropped. Senders retransmit the lost packets, adding more load, which causes more drops. Throughput actually *falls* as offered load rises: **congestion collapse**, first seen on the Internet in October 1986 when throughput on a link between two Berkeley sites dropped by a factor of about a thousand. The cure is for senders to slow down when the network is congested.

### Flow control versus congestion control
**Flow control** protects the *receiver*: it advertises a window (rwnd) of how much data it can buffer. **Congestion control** protects the *network*: the sender keeps a congestion window (cwnd) and may have at most min(cwnd, rwnd) unacknowledged bytes in flight. Throughput ≈ window / RTT.

### The sender's three questions
1. *How much can I send right now?* Ask cwnd.
2. *How do I find the right cwnd?* Probe: increase slowly while no loss occurs.
3. *How do I know it is too much?* Loss (or an ECN mark) signals congestion; decrease.

### Slow start, congestion avoidance and loss
Start with a small window (10 segments today). In **slow start** cwnd increases by one segment per ACK, doubling each RTT (10, 20, 40, ...) until it reaches a threshold ssthresh or a loss. In **congestion avoidance** cwnd grows by one segment per RTT. On a loss detected by three duplicate ACKs the sender halves cwnd (**fast retransmit / fast recovery**); on a timeout it restarts from one segment.

!! Worked example: MSS 1460 B, RTT 100 ms, cwnd 40 segments. Throughput ≈ 40 × 1460 × 8 / 0.1 = 4.7 Mb/s. At cwnd 400 it is 47 Mb/s: window and rate are linked through the RTT.

### ACK clocking
Acknowledgments return at the rate packets cross the bottleneck, so a window-based sender automatically spaces new packets at about the bottleneck rate. This self-clocking is why TCP is stable, and why bursty ACK compression or pacing issues matter.

### Self-check
Why is slow start called slow when it doubles every RTT? (Compared with sending a whole window at once, it starts at a small window.) What is the relation between window, RTT and throughput?
""", r"""
## Advanced: congestion control as distributed optimisation
Kelly, Maulloo and Tan (1998) cast rate control as maximising total utility Σᵢ Uᵢ(xᵢ) subject to link capacity constraints. The network's loss or delay signal acts as a **price** (a Lagrange multiplier), and each sender adjusts its rate in response to its path price: a dual-gradient algorithm that no one needs to run centrally. Different utility functions give different fairness: α-fairness uses U(x) = x^(1−α)/(1−α), with α = 1 proportional fairness (log utility), α → ∞ max-min fairness, and α = 2 minimum potential delay fairness. Low's analysis shows Reno roughly corresponds to α = 2 with RTT weighting, Vegas to proportional fairness; it explains the 1/RTT² rate ratio you observe in the first lab (long-RTT flows are penalised twice: they grow slowly and their share is proportional to 1/RTT² in a synchronised model).

## Advanced: fluid models and stability
Misra, Gong and Towsley modelled Reno as dW/dt = 1/R − (W/2)·(W/R)·p, where p is the loss probability seen at time t−R. The equilibrium W = √(2/p) differs from the Mathis constant (√(8/3p) at peak, 1.22/√p average) only because of the modelling assumption about when losses occur. Linearising around the equilibrium with feedback delay R shows that stability requires the loop gain to be small enough relative to the delay: with RED-like AQM this gives stability conditions on capacity, round-trip time and number of flows (Hollot et al. 2001). Intuition: high capacity C and long delay R make the loop unstable, which explains why standard Reno oscillates and why high-speed variants and ECN-based protocols (XCP, DCTCP) change the control law.

## Advanced: loss recovery details
**Fast retransmit** triggers after 3 duplicate ACKs, but with SACK the sender knows precisely which segments are missing; RFC 6675 recovers multiple losses per window, and **RACK-TLP** (RFC 8985) uses time rather than counts to detect loss and adds a tail loss probe to avoid RTOs when the last packets are lost. The retransmission timeout follows Jacobson's estimator: SRTT ← (7/8)·SRTT + (1/8)·R; RTTVAR ← (3/4)·RTTVAR + (1/4)·|SRTT − R|; RTO = SRTT + 4·RTTVAR (minimum 1 s in RFC 6298, 200 ms in Linux). Karn's algorithm forbids sampling RTT from retransmitted segments, since the ACK is ambiguous.

## Advanced: window scaling, buffers and high-speed variants
The 16-bit window field limits rwnd to 64 KB, which at 100 ms RTT caps throughput at about 5 Mb/s; the window-scale option (RFC 7323) multiplies by up to 2¹⁴. Filling a 10 Gb/s, 100 ms path needs a 125 MB window, so autotuning of socket buffers matters. Reno's slow additive increase needs thousands of RTTs to recover, motivating HighSpeed TCP, Scalable TCP, H-TCP, FAST, Compound TCP and finally CUBIC (default in Linux since 2.6.19 and in other platforms), whose cubic growth makes the window an RTT-independent function of elapsed time since the last loss; CUBIC also includes a **TCP-friendly region** that falls back to Reno-like growth when that would be faster, and a hybrid slow start (HyStart) that exits slow start when delay begins to rise, avoiding bursts of loss.

## Advanced: what the sawtooth means for buffers
With one Reno flow, after a halving the window is (BDP + B)/2 where B is the buffer. The link stays busy only if that is at least the BDP, i.e. B ≥ BDP. With n desynchronised flows the aggregate window fluctuates much less and B = BDP/√n is enough (Week 2). If buffers are bigger than needed, standing queues add latency (Week 5); if smaller, utilisation drops. Congestion control and buffer sizing must be designed together.
""")
