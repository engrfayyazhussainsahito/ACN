# ---------------- Week 14 ----------------
LAB(14, "A cost calculator for collective operations", "Time models for the collectives used in training (per-GPU message size S, per-GPU bandwidth B, per-step latency α), then a two-level hierarchical all-reduce (fast links inside a server, rails across servers) versus one flat ring over the network.", """
def ring_allreduce(N, S, B, a): return 2 * (N - 1) / N * S / B + 2 * (N - 1) * a
def reduce_scatter(N, S, B, a): return (N - 1) / N * S / B + (N - 1) * a
def all_gather(N, S, B, a): return (N - 1) / N * S / B + (N - 1) * a
def all_to_all(N, S, B, a): return (N - 1) / N * S / B + (N - 1) * a
N, S, B, a = 64, 1e9, 50e9, 5e-6
for name, f in (("ring all-reduce", ring_allreduce), ("reduce-scatter", reduce_scatter), ("all-gather", all_gather), ("all-to-all", all_to_all)):
    print(f"{name:16s} N={N}, S=1 GB: {f(N, S, B, a) * 1e3:8.2f} ms")
g, B_in, B_out, S = 8, 300e9, 50e9, 10e9
print("\\nhierarchical vs flat all-reduce, 10 GB gradients, 8 GPUs/server")
for M in (8, 32, 128):
    flat = ring_allreduce(g * M, S, B_out, a)
    hier = 2 * (g - 1) / g * S / B_in + ring_allreduce(M, S / g, B_out, a)
    print(f"  {g*M:5d} GPUs: flat {flat*1e3:7.1f} ms   hierarchical {hier*1e3:7.1f} ms   speed-up {flat/hier:4.1f}x")
""")
LAB(14, "Spraying beats hashing for elephants", "Eight equal elephant flows share 8 equal-cost links. Split each flow into `split` independently routed sub-flows (flowlets or packet spraying) and measure how much the busiest link exceeds the ideal load.", """
import random, collections
def slowdown(flows, links, split, trials=4000, seed=1):
    random.seed(seed); tot = 0.0
    for _ in range(trials):
        c = collections.Counter(random.randrange(links) for _ in range(flows * split))
        tot += max(c.values()) / split / (flows / links)
    return tot / trials
print("sub-flows per flow   busiest link / ideal load (collective slows by this factor)")
for split in (1, 4, 16, 64, 256): print(f"{split:18d} {slowdown(8, 8, split):10.2f}x")
step_comp = 0.100
for comm in (0.04, 0.10, 0.20):
    print(f"compute 100 ms, communication {comm*1000:3.0f} ms: scaling efficiency overlapped {step_comp/max(step_comp, comm):5.1%}, not overlapped {step_comp/(step_comp+comm):5.1%}")
""")
deepen(14, r"""
## Basics: how a neural network gets trained on many machines
Training adjusts a model's parameters (billions of numbers) to reduce an error. One **step** takes a batch of data, computes a prediction error (forward pass), computes how each parameter should change (backward pass, giving **gradients**) and updates the parameters. A single GPU is far too slow for large models, so many GPUs work together.

### Parallelism in one paragraph each
- **Data parallelism:** every GPU holds a full copy of the model and processes different data. After the backward pass the GPUs must average their gradients so all copies stay identical: this is an **all-reduce** over the gradient size.
- **Tensor (model) parallelism:** one layer's matrices are split across GPUs; partial results are combined at every layer, so communication happens many times per step and needs very high bandwidth.
- **Pipeline parallelism:** consecutive layers sit on different GPUs and activations flow between them (point-to-point).
- **Expert parallelism (mixture of experts):** tokens are routed to experts on other GPUs, an **all-to-all** exchange.

### The collective operations
| Collective | What happens | Data each GPU sends (approx) |
|---|---|---|
| Broadcast | one GPU's data goes to all | S |
| Reduce | sum of all GPUs' data lands on one | S |
| All-reduce | every GPU gets the sum | 2·S·(N−1)/N (ring) |
| Reduce-scatter | sum, split so each GPU holds one shard | S·(N−1)/N |
| All-gather | every GPU gets all shards | S·(N−1)/N |
| All-to-all | each GPU sends a distinct piece to every other | S·(N−1)/N |

All-reduce equals reduce-scatter followed by all-gather, which is exactly why the ring algorithm sends 2·S·(N−1)/N bytes.

### What is RDMA?
Normal networking passes through the operating system: system calls, copies and interrupts cost microseconds and CPU. **Remote direct memory access** lets the network card read and write application memory directly, bypassing the kernel (kernel bypass) and avoiding copies (zero copy). The application posts work requests to queue pairs; the NIC does the rest. InfiniBand is a complete RDMA-native network; **RoCEv2** carries RDMA over UDP/IP so it works on Ethernet.

### Why the network matters so much
If computing a step takes 100 ms and communicating takes 40 ms, with no overlap the step takes 140 ms: scaling efficiency 71%. With perfect overlap it stays 100%. As models and cluster sizes grow, communication is the part that does not shrink, so cluster networks became a first-class design problem. In the second lab you can compute the efficiency for different communication times.

### Self-check
Why is all-reduce the same as reduce-scatter plus all-gather? Why does tensor parallelism need a faster network than data parallelism? (It communicates every layer rather than once per step.)
""", r"""
## Advanced: collective algorithms in practice
Libraries such as NCCL choose among **ring** (bandwidth-optimal; latency grows with N), **tree** and **double binary tree** (latency grows with log N; two complementary trees keep every link busy in both directions), and **halving-doubling** (log N steps; best for power-of-two N) depending on message size, topology and GPU count; small messages favour trees, large messages rings. Hierarchical algorithms exploit the bandwidth hierarchy: reduce-scatter inside the server over NVLink-class links, run the inter-server all-reduce on only 1/g of the data over g parallel rails, then all-gather inside the server; the first lab shows a speed-up of roughly 4× at every scale for g = 8, because the slow network carries only 1/g of the data per link and the fast intra-server phases are cheap. **In-network reduction** (e.g. NVIDIA SHARP and similar) lets switches perform the summation, cutting the data each GPU sends and receives from 2S to S and the number of steps to the tree depth, at the cost of switch memory and software complexity.

## Advanced: mapping parallelism to topology
Bandwidth is tiered: inside a server GPUs share a high-bandwidth NVLink/NVSwitch domain (hundreds of GB/s); across servers each GPU has its own NIC (e.g. 200 to 800 Gb/s); across racks the fabric may be oversubscribed. A common placement puts tensor parallelism inside the NVLink domain, pipeline stages across servers in one rack or pod, and data parallelism across the rest so that the large but infrequent gradient all-reduce crosses the thinnest links. All-to-all in mixture-of-experts models has no locality to exploit and stresses bisection bandwidth. **Rail-optimised** topologies attach the i-th NIC of every server to the i-th leaf switch so that collectives among GPUs with the same local index never cross spines; the price is that traffic between different rails does cross spines or relies on intra-server forwarding.

## Advanced: congestion control and load balancing for training fabrics
Training generates few long synchronised flows: ECMP hashing has too little entropy (see the second lab where splitting flows into sub-flows drives the busiest-link overload toward 1), and a single slow link delays the whole collective (stragglers). Solutions combine: more queue pairs per connection and path-aware flowlet or per-packet spraying (InfiniBand adaptive routing, Ultra Ethernet Consortium's packet spraying with out-of-order delivery support in the NIC), receiver-driven or credit-based transports, congestion control driven by ECN (DCQCN), RTT/delay (Swift-like, TIMELY) or in-band telemetry (HPCC), and sometimes **no congestion control** within carefully scheduled collectives. Lossless Ethernet needs priority flow control (PFC) with deadlock avoidance; PFC storms and head-of-line blocking motivate designs that avoid PFC or confine it to a single hop. Scale-out designs also address failure: with tens of thousands of links, flaps are routine, so fast rerouting, link health monitoring and job restart with checkpoints become part of network design.

## Advanced: optical circuit switching and alternative topologies
Torus and mesh topologies (3-D torus in TPU pods) offer excellent nearest-neighbour bandwidth at low cost; optical circuit switches can reconfigure which racks connect, letting the same hardware form different slice shapes and routing around failures (reported for TPU v4 superpods). The cost is reconfiguration time (milliseconds), so circuits are changed between jobs or phases rather than per packet. Research directions include photonics inside packages, co-designed collective algorithms and topologies, and rethinking transports for collectives rather than flows.

## Advanced: reasoning about scale
Scaling efficiency η = T_compute / (T_compute + T_exposed_comm). Overlapping communication with the backward pass (bucketed gradient all-reduce while earlier layers are still computing) reduces exposed communication; compression, gradient accumulation, and larger batch sizes reduce its frequency. Latency matters when messages are small (many short collectives per step); bandwidth matters for large gradients. The model T = 2(N−1)/N·S/B + 2(N−1)·α captures both, which is why the ring is best for large S and trees for small S.
""")

# ---------------- Week 15 ----------------
LAB(15, "Constraint-based shortest path first (CSPF)", "A five-node WAN. Plain shortest-path routing sends every demand over the cheapest path and overloads it; CSPF (used by MPLS-TE) prunes links without enough residual capacity before running Dijkstra.", """
import heapq
edges = {("A", "B"): (1, 10), ("B", "D"): (1, 10), ("A", "C"): (2, 10), ("C", "D"): (2, 10), ("D", "E"): (1, 20)}
cost, cap0 = {}, {}
for (u, v), (c, k) in edges.items(): cost[(u, v)] = cost[(v, u)] = c; cap0[(u, v)] = cap0[(v, u)] = k
def cspf(src, dst, bw, cap):
    pq = [(0, src, [src])]; seen = set()
    while pq:
        d, u, p = heapq.heappop(pq)
        if u == dst: return p
        if u in seen: continue
        seen.add(u)
        for (a, b), c in cost.items():
            if a == u and cap[(a, b)] >= bw and b not in seen: heapq.heappush(pq, (d + c, b, p + [b]))
    return None
demands = [6, 6, 6]                                   # three A->E demands of 6 units
cap = dict(cap0); load = {k: 0 for k in cap0}
print("CSPF:")
for d in demands:
    p = cspf("A", "E", d, cap)
    print("  demand", d, "->", "-".join(p) if p else "BLOCKED")
    if p:
        for a, b in zip(p, p[1:]): cap[(a, b)] -= d; cap[(b, a)] -= d
for d in demands:
    p = cspf("A", "E", 0, cap0)
    for a, b in zip(p, p[1:]): load[(a, b)] += d
print("plain shortest path: all demands on", "-".join(p), "-> utilisation of link A-B:", f"{load[('A','B')]/cap0[('A','B')]:.0%}")
""")
LAB(15, "Chord lookups", "Build a Chord ring of N random identifiers in a 16-bit space, give every node finger tables and measure the number of hops for 500 random lookups; compare with ½·log₂N (our count includes the final hop to the successor, so expect about ½·log₂N + 1).", """
import random, bisect, math
def build(N, m=16, seed=1):
    random.seed(seed); return sorted(random.sample(range(2 ** m), N))
def succ(ids, x, M): return ids[bisect.bisect_left(ids, x % M) % len(ids)]
def lookup(ids, m, start, key):
    M = 2 ** m; n = start; hops = 0
    while True:
        s = succ(ids, n + 1, M)
        if n == s or 0 < (key - n) % M <= (s - n) % M: return hops + 1      # key lies in (n, successor]
        nxt = n
        for i in range(m - 1, -1, -1):                                       # closest preceding finger
            f = succ(ids, n + 2 ** i, M)
            if f != n and 0 < (f - n) % M < (key - n) % M: nxt = f; break
        if nxt == n: return hops + 1
        n = nxt; hops += 1
print("nodes    mean hops   max hops   0.5*log2(N)")
for N in (2 ** 6, 2 ** 8, 2 ** 10, 2 ** 12):
    ids = build(N); rnd = random.Random(2)
    h = [lookup(ids, 16, rnd.choice(ids), rnd.randrange(2 ** 16)) for _ in range(500)]
    print(f"{N:6d} {sum(h)/len(h):10.2f} {max(h):10d} {0.5 * math.log2(N):12.2f}")
""")
LAB(15, "DNS caching: TTL, popularity and latency", "2,000 names with Zipf(1.0) popularity are queried at 1,000 queries/s. A resolver caches each answer for its TTL. Hit ratio and mean latency (1 ms hit, 60 ms miss) for several TTLs.", """
import random
def dns_hit(ttl, names=2000, alpha=1.0, T=200000, rate=1000.0, seed=1):
    rnd = random.Random(seed); w = [1 / (i + 1) ** alpha for i in range(names)]
    expiry = [-1.0] * names; hits = 0; t = 0.0
    for q in rnd.choices(range(names), w, k=T):
        t += rnd.expovariate(rate)
        if expiry[q] > t: hits += 1
        else: expiry[q] = t + ttl
    return hits / T
print("TTL(s)  hit ratio  mean latency")
for ttl in (1, 10, 60, 300, 3600):
    h = dns_hit(ttl); print(f"{ttl:6d} {h:9.1%} {h * 1 + (1 - h) * 60:9.2f} ms")
""")
deepen(15, r"""
## Basics: the wide-area network and who runs it
A **wide-area network (WAN)** connects sites across cities and continents. Inside a company it is a private network of leased lines or fibre; across the world it is the Internet, a federation of thousands of **autonomous systems**. Two kinds of commercial relationship exist: **transit** (a customer pays a provider to reach the whole Internet) and **peering** (two networks exchange traffic between their own customers, often without payment). Traffic is usually billed on the 95th percentile of five-minute usage samples.

### Why MPLS exists
IP routers forward by looking up the destination in a large table, and IP picks one shortest path regardless of load. **Multiprotocol label switching** adds a short label in front of each packet; routers then forward with a simple exact-match on the label and *swap* it for the next hop's label, like baggage tags at connecting airports. Paths (label-switched paths) can be set up explicitly, which allows traffic engineering, fast backup paths and virtual private networks.

### Quality of service in brief
Not all packets need the same treatment. **DiffServ** marks packets with a code point (DSCP) and routers give each class its own queue and weight: voice gets strict priority and a small queue; bulk transfers get what is left. Without capacity management, QoS only decides *who* suffers in congestion, so ISPs also over-provision links to keep utilisation moderate.

### The traffic engineering problem
Shortest-path routing can leave one path overloaded while a longer path sits idle. TE spreads demand over several paths to lower the maximum link utilisation. It is a **multi-commodity flow** problem: each source-destination pair is a commodity with a demand, flows share link capacities, and we optimise an objective such as minimising the maximum utilisation or maximising the served fraction.

### Max-min fairness by water-filling
When flows compete for a link, a fair rule is: give everyone an equal share, but a flow that needs less than its share only takes what it needs, and the surplus is redistributed to the others. For capacity 20 and demands 2, 4, 8, 8: the equal share is 5, flow 1 needs 2, the remaining 18 is shared 6 each, flow 2 needs 4, and the remaining 14 gives 7 to each of the last two.

### Overlays and names in two paragraphs
An **overlay network** is a network built on top of another: peers form their own topology and routing over IP. In a **distributed hash table (DHT)**, keys and nodes are hashed to the same identifier space and each key is stored at the node responsible for it, so any key can be found without a central index. **DNS** is the Internet's name system: a hierarchy of servers (root, top-level domains, authoritative servers) with caching at every level controlled by each record's time-to-live.

### Self-check
Why can a longer path be better for the network overall? What does a DNS TTL of 30 seconds trade off? What does a 95th-percentile bill ignore? (The top 5% of 5-minute intervals, i.e. short bursts.)
""", r"""
## Advanced: MPLS-TE, segment routing and PCE
**RSVP-TE** signals explicit label-switched paths with bandwidth reservations; each router advertises unreserved bandwidth by IGP extensions, and the head-end computes a constrained path (CSPF, as in the first lab) and signals it hop by hop. Make-before-break re-optimisation moves traffic to a new path before tearing down the old one. **Fast reroute** pre-signals backup paths (facility backup with a bypass tunnel shared by many LSPs, or one-to-one detour) for sub-50 ms repair. **Segment routing** (RFC 8402) encodes the path as an ordered list of segment identifiers in the packet header (MPLS labels or an IPv6 routing header), removing per-flow state from the core; SR-TE computes the segment list at the head-end or a **path computation element (PCE)** that has a global view via BGP-LS. Trade-offs: header overhead and hardware limits on label stack depth versus network state.

## Advanced: software-defined WANs
Google's B4 splits the WAN into sites, uses a centralised traffic-engineering service over a logically centralised controller, groups flows into flow groups and tunnel groups, and computes allocations with bandwidth functions that express each application's priority and fairness; it runs links near full utilisation because the controller can shift low-priority bulk traffic and because traffic is classed by priority with graceful degradation on failure. SWAN (Microsoft) allocates approximately max-min fair rates among service classes using a linear programme with geometric bins for tractability, and performs **congestion-free updates**: with a fraction s of capacity reserved as scratch, a sequence of at most ⌈1/s⌉ − 1 intermediate configurations moves the network from one allocation to another without overloading any link at any intermediate step. Both rely on host-side rate limiting (brokers and enforcers) rather than only router queues. Lessons: global optimisation raises utilisation, but needs accurate demand estimates, fast failure reaction (local fast reroute, then global recomputation) and careful update orchestration; failures of the controller must degrade gracefully to the local protocols.

## Advanced: structured overlays in depth
**Chord** guarantees O(log N) hops with high probability and keeps O(log N) state per node; nodes join by finding their successor and running periodic **stabilisation** to repair pointers, and a **successor list** of r nodes tolerates failures (the ring survives unless all r successors fail simultaneously). Churn handling dominates real systems: lookups under high churn need parallelism, timeouts and proximity-aware neighbour choice. **Kademlia** (used by the BitTorrent mainline DHT and in other systems) defines distance as XOR, keeps k-buckets of up to k contacts per distance range, and performs parallel iterative lookups with concurrency α (typically 3); XOR distance is symmetric, so nodes learn useful contacts from incoming queries. Security issues: Sybil attacks (one party creating many identifiers; mitigated by identity constraints), eclipse attacks (surrounding a victim's routing table) and index poisoning. Overlay ideas live on in distributed storage, blockchains' peer-to-peer layers, and consistent hashing in data-centre services.

## Advanced: DNS in depth
A recursive resolver walks the hierarchy using referrals, caches NS and address records (glue records break the circularity when a name server lives inside the zone it serves), and caches negative answers (NXDOMAIN, with TTL from the SOA minimum). The root zone is served by 13 named server identities, each implemented as an anycast service with many instances worldwide. **EDNS Client Subnet** lets a resolver tell an authoritative server (e.g. a CDN's) which part of the client's network is asking, improving mapping at the cost of privacy. TTL choices trade agility (fast failover, load balancing) against cache effectiveness and query load: the third lab shows that hit ratio rises steeply as TTL grows to the minutes range, and that short TTLs multiply authoritative load and mean latency. Failures and attacks (the 2016 attack on a managed DNS provider that made many popular sites unreachable) justify using multiple authoritative providers, anycast and DNSSEC. DNS also underlies email authentication (SPF, DKIM records), service discovery and certificate issuance checks.

## Advanced: interdomain economics and the shape of the Internet
The tiered hierarchy of the early commercial Internet has flattened: large content and cloud providers peer directly with access networks at IXPs and build private backbones, so many paths are only one or two AS hops long. Settlement-free peering requires mutual benefit, typically balanced traffic ratios and presence at common locations; transit pricing has fallen steadily with competition and volume. These economic decisions shape routing more than latency does, which is why BGP policy, not shortest path, governs where packets go, and why measurement studies of the Internet's topology need both BGP data and traceroutes.
""")

# ---------------- Midterm and final extras ----------------
mid["body"] += r"""

## Study plan for the midterm
| Topic | Weight | Skills tested | Where to practise |
|---|---|---|---|
| Delay model, BDP, pipelining | 15% | store-and-forward time, BDP, bits vs bytes | Week 1 labs and exercises |
| Queueing | 20% | Little, M/M/1, M/M/1/K, buffer sizing | Week 2 labs, demo |
| Routing and BGP | 20% | Dijkstra, DV, valley-free, decision process | Week 3 labs |
| Congestion control | 25% | AIMD, Reno sawtooth, CUBIC, fairness, Mathis | Weeks 4 and 5 labs and demos |
| QUIC and transport | 10% | handshake RTTs, HOL blocking | Week 6 |
| Data centers | 10% | fat-tree sizing, ECMP, incast, oversubscription | Week 7 labs |

## How to prepare
Re-derive from memory: the packetised transfer time, M/M/1 mean delay, the Reno throughput formula, the fat-tree counts and the BGP decision order. Redo every exercise without looking at the solution. Re-run each lab and predict its output before reading it."""
mid["ex"] = mid["ex"] + [
    ("A 4 MB file crosses 4 store-and-forward links at 100 Mb/s using 1000 B packets (ignore propagation). Transfer time?", "P = 4000 packets; T = (4 + 4000 − 1)·8000/10⁸ = 0.320 s."),
    ("M/M/1, λ = 800, μ = 1000 pkt/s. Mean delay, mean number in system, and P(more than 10 packets in the system)?", "W = 1/200 = 5 ms; L = 4; P(>10) = ρ¹¹ = 0.8¹¹ = 8.6%."),
    ("x–y costs 3, y–z costs 4, x–z costs 9. What does distance-vector give for x's distance to z?", "min(9, 3 + 4) = 7, via y."),
    ("A Reno flow halves its window from 200 to 100 at an RTT of 200 ms. Time to regain 200?", "100 RTTs × 0.2 s = 20 s."),
    ("RTT 120 ms. Time to first byte for TCP+TLS 1.3, QUIC 1-RTT and QUIC 0-RTT?", "3 × 120 = 360 ms; 2 × 120 = 240 ms; 1 × 120 = 120 ms.")]
fin["body"] += r"""

## Project timeline
| Week | Milestone | Deliverable |
|---|---|---|
| 3 | proposal | one page: question, method, baselines, data/tools |
| 6 | design review | experiment plan, expected figures, risks |
| 10 | checkpoint | preliminary results with error bars |
| 13 | draft | 6-page report in conference format |
| 16 | final | report, code and data, 10-minute talk |

## Final review checklist
For each of Weeks 9 to 15 you should be able to: state the problem, give the key formula or algorithm, work a numeric example by hand, explain one design trade-off, and name two papers. Then revisit the midterm topics: the final is cumulative."""
fin["ex"] = fin["ex"] + [
    ("Heavy hitters: a count-min sketch with w = 1024 and d = 4 processes N = 10⁶ packets. By how much can a flow's estimate exceed its true count (with probability ≥ 1 − e⁻⁴)?", "ε = e/w ≈ 0.00266, so at most εN ≈ 2,656 packets."),
    ("A 20 MHz Wi-Fi link at 30 dB SNR: Shannon capacity?", "20·log₂(1001) ≈ 199 Mb/s."),
    ("A CDN cache hits 95% of the time (hit 5 ms, miss 100 ms). Mean latency and origin offload?", "0.95·5 + 0.05·100 = 9.75 ms; origin sees 5% of requests (20× offload)."),
    ("Water-filling: capacity 30, demands 5, 10, 20, 20.", "(5, 8.33, 8.33, 8.33)."),
    ("Chord with 2²⁰ nodes: mean hops, and why not N/2?", "About 10 hops; fingers at distances 2ⁱ halve the remaining distance each hop, whereas successor pointers move one node at a time.")]

GL_EXTRA = {
    "All-reduce": "Collective in which every participant ends up with the element-wise sum of all participants' data.",
    "Anycast": "Announcing one IP address from many locations so routing delivers each user to a nearby instance.",
    "ARQ": "Automatic repeat request: retransmitting data until it is acknowledged.",
    "Autonomous system (AS)": "A network under one administrative control that exchanges routes with others using BGP.",
    "Chord": "A distributed hash table that finds a key in O(log N) hops using finger tables.",
    "CIDR": "Classless inter-domain routing: IP prefixes of any length written as address/length.",
    "Clos network": "Multi-stage switching fabric with many equal-cost paths between ports; basis of fat-trees and leaf-spine.",
    "CoDel": "Queue-management algorithm that drops packets when minimum queueing delay stays above a target.",
    "Congestion collapse": "State in which load is high but useful throughput is very low because of retransmissions and drops.",
    "Consistent hashing": "Mapping keys to servers so that adding or removing a server moves only about 1/n of the keys.",
    "CSMA/CA": "Carrier-sense multiple access with collision avoidance, the Wi-Fi medium-access method.",
    "DCTCP": "Data-centre TCP: reduces the window in proportion to the fraction of ECN-marked packets.",
    "DiffServ": "IP quality-of-service architecture based on per-hop treatment of packet classes marked in the DSCP field.",
    "DNSSEC": "Signatures on DNS data so resolvers can verify authenticity and integrity.",
    "Fat-tree": "Clos-style data-centre topology built from identical k-port switches: k³/4 hosts, 5k²/4 switches.",
    "FIB / RIB": "Forwarding information base (used per packet) and routing information base (all learned routes).",
    "Flowlet": "A burst of packets of a flow separated from the next by an idle gap, used for order-safe load balancing.",
    "Goodput": "Application-level useful throughput, excluding headers and retransmissions.",
    "HOL blocking": "Head-of-line blocking: later data waits behind an earlier missing item in the same ordered stream or queue.",
    "INT": "In-band network telemetry: switches append measurements to packets as they pass.",
    "Jain's index": "Fairness measure (Σx)²/(nΣx²), equal to 1 when all shares are equal.",
    "Kendall notation": "A/S/c/K description of a queue: arrival process, service process, servers, buffer.",
    "LEO": "Low Earth orbit, 500 to 2,000 km altitude; satellites move quickly and have short propagation delay.",
    "LPM": "Longest-prefix match: the rule of selecting the most specific matching route.",
    "MIMO": "Multiple-input multiple-output: using several antennas to multiplex streams or steer beams.",
    "MPLS": "Multiprotocol label switching: forwarding by short labels along pre-established paths.",
    "MSS": "Maximum segment size: the largest TCP payload in one segment, typically 1460 bytes.",
    "NAT": "Network address translation: rewriting addresses and ports so private hosts share public addresses.",
    "NFV": "Network functions virtualisation: running firewalls, load balancers and similar functions as software.",
    "OFDM": "Orthogonal frequency-division multiplexing: many narrow subcarriers carrying symbols in parallel.",
    "PFC": "Priority flow control: Ethernet pause frames that make a fabric lossless per traffic class.",
    "PTO": "Probe timeout: QUIC timer that triggers probe packets when no acknowledgment arrives.",
    "QoE": "Quality of experience: user-perceived quality, e.g. bitrate, stalls and start-up delay of video.",
    "RDMA": "Remote direct memory access: NIC-to-NIC memory transfers that bypass the host CPU and kernel.",
    "Reflection attack": "DDoS in which attackers spoof the victim's address so third-party servers send replies to the victim.",
    "Segment routing": "Source routing in which the path is encoded as a list of segment identifiers in the packet.",
    "SYN cookie": "Stateless handshake defence encoding connection state in the server's initial sequence number.",
    "TCAM": "Ternary content-addressable memory: hardware that matches rules with wildcard bits in one cycle.",
    "Traffic engineering": "Choosing routes and splits to balance load and meet performance goals.",
    "TLS": "Transport Layer Security: authenticated, encrypted channel protocol used by HTTPS.",
    "Water-filling": "Algorithm for max-min fair allocation: raise all rates equally until each is satisfied or capacity is exhausted.",
    "Zipf's law": "Popularity distribution in which the i-th most popular item has frequency proportional to i^(−α).",
}
