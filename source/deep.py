# executed inside build.py after extra.py (shares globals)
PH[5] = "Modern Frontiers"
ASSIGN = {}
Ns_ = [2 ** i for i in range(1, 11)]
def _ring(N, S, B=50e9, a=5e-6): return 2 * (N - 1) / N * S / B + 2 * (N - 1) * a
def _rhd(N, S, B=50e9, a=5e-6): return 2 * (N - 1) / N * S / B + 2 * math.log2(N) * a
plot("ar", "All-reduce time versus number of GPUs (50 GB/s per GPU, 5 µs per step). For 1 MB messages latency dominates and ring is up to ~70x slower; for 1 GB messages both approach the bandwidth bound 2S/B.",
     [("ring 1 MB", Ns_, [_ring(n, 1e6) * 1e3 for n in Ns_]), ("halving-doubling 1 MB", Ns_, [_rhd(n, 1e6) * 1e3 for n in Ns_]),
      ("ring 1 GB", Ns_, [_ring(n, 1e9) * 1e3 for n in Ns_]), ("halving-doubling 1 GB", Ns_, [_rhd(n, 1e9) * 1e3 for n in Ns_])], "GPUs N", "time (ms)", True, True)
Nc_ = [10 ** (i / 4) for i in range(4, 29)]
plot("chord", "Expected lookup hops in a ring overlay: successor-pointer walking needs N/2 hops, Chord's finger tables need about ½·log₂N. At a million nodes that is 10 hops instead of 500,000.",
     [("successor ring (N/2)", Nc_, [n / 2 for n in Nc_]), ("Chord (½ log₂ N)", Nc_, [0.5 * math.log2(n) for n in Nc_])], "nodes N", "expected hops", True, True)

def newwk(n, title, src, summary, obj, key, body, code, ex, rd):
    d = dict(n=n, ph=5, title=title, src=src, summary=summary, obj=obj, key=key, body=body, code=code, ex=ex, rd=rd)
    W_.append(d); ALL.append(d); BYN[n] = d
newwk(14, "AI Cluster Networking: RDMA, Collectives and Rail Design", "Stanford CS244, CMU 15-744, recent SIGCOMM/NSDI papers",
      "Why distributed training reshaped data-center networks: synchronous collectives, ring versus tree all-reduce, RoCE and its congestion control, and rail-optimised topologies.",
      ["Derive the cost of ring and recursive halving-doubling all-reduce.", "Explain why ECMP fails for a few huge synchronised flows.", "Describe RDMA, PFC, DCQCN and their failure modes.", "Reason about rail-optimised and oversubscribed AI fabrics."],
      "T_ring = 2(N−1)/N·S/B + 2(N−1)·α",
      r"""## Why AI traffic is different
Training is synchronous: after each step every GPU must combine its gradients with all others (an all-reduce) before the next step can start. So (1) the slowest flow sets the step time, making tail latency the metric that matters; (2) traffic consists of few, huge, long-lived flows rather than millions of short ones, so ECMP hashing has very low entropy; (3) all GPUs communicate at the same instant, which creates synchronised bursts and incast-like patterns.

## Cost model of all-reduce
Let N GPUs each hold S bytes, with per-GPU bandwidth B and per-step latency α. Ring all-reduce has two phases. Reduce-scatter takes N−1 steps, each moving S/N bytes per GPU; all-gather takes another N−1 steps of the same size. Therefore

$ T_ring = 2(N−1)/N · S/B + 2(N−1)·α

The bandwidth term approaches 2S/B and is optimal (Patarasuk and Yuan 2009): no algorithm can move less data per GPU. Recursive halving-doubling keeps the same bandwidth term but needs only 2·log₂N steps:

$ T_rhd = 2(N−1)/N · S/B + 2·log₂(N)·α

!! Worked example: a 5-billion-parameter model has 10 GB of fp16 gradients. With N = 64 and B = 50 GB/s (400 Gb/s per GPU), T_ring = 2·(63/64)·10/50 s = 0.394 s plus 0.63 ms of latency. For a tiny 1 MB message with N = 1024, ring needs 10.2 ms of latency while halving-doubling needs 0.1 ms.

[[fig:ar]]

[[demo:ring]]

## RDMA and RoCEv2
Remote direct memory access moves data NIC-to-NIC without involving the CPU, giving microsecond latency. RoCEv2 carries it over UDP/IP on Ethernet. Original RoCE NICs used go-back-N retransmission, so a single loss re-sends a whole window; a first-order model gives goodput efficiency ≈ 1/(1 + p·W) for loss rate p and window W packets. They therefore rely on a lossless fabric: priority flow control (PFC) pauses the upstream hop before the buffer overflows. PFC brings its own problems: head-of-line blocking, pause storms, and deadlocks when a cyclic buffer dependency forms (Guo et al. 2016).

## Congestion control for RDMA
DCQCN (Zhu et al. 2015) combines ECN marking at switches with rate-based reaction at senders: on receiving congestion notification packets the sender cuts its rate multiplicatively and then recovers in stages. HPCC uses in-band telemetry to read queue lengths and link utilisation directly. Receiver-driven schemes (Homa, NDP) and Ultra Ethernet's packet spraying aim for the same goals without PFC.

## Topology
GPU clusters use full-bisection fat-trees or Clos fabrics, often rail-optimised: the i-th NIC of every server connects to the i-th leaf switch ("rail i"), so collectives among corresponding GPUs stay within one leaf. Within a server, NVLink/NVSwitch provides several hundred GB/s between GPUs, so hierarchical collectives first reduce within the server, then across the network. Dragonfly and torus topologies are used in other systems (supercomputers, TPU pods) trading cost for locality.

!! Worked example: hashing 8 equal elephant flows onto 8 equal-cost links gives P(no two collide) = 8!/8⁸ = 0.24%, so a collision is almost certain and a collided link runs at half rate, halving the whole collective. Remedies: flowlet or per-packet load balancing, many more queue pairs per connection, or explicit path control.

## Common pitfalls
Using the average link utilisation to judge a fabric (collectives care about the worst link), enabling PFC without deadlock analysis, ignoring the host side (PCIe, NIC buffers) and assuming network bandwidth is the only bottleneck when compute and communication can overlap.""",
      """import math
def ring(N, S, B=50e9, a=5e-6): return 2 * (N - 1) / N * S / B + 2 * (N - 1) * a
def rhd(N, S, B=50e9, a=5e-6): return 2 * (N - 1) / N * S / B + 2 * math.log2(N) * a
print(f"10 GB, N=64 : ring {ring(64, 10e9)*1e3:.1f} ms")
print(f"1 MB, N=1024: ring {ring(1024, 1e6)*1e3:.2f} ms, halving-doubling {rhd(1024, 1e6)*1e3:.2f} ms")
print(f"P(no ECMP collision, 8 flows / 8 links) = {math.factorial(8) / 8**8:.2%}")
W = 400e9 / 8 * 10e-6 / 1024
for p in (1e-5, 1e-4, 1e-3): print(f"go-back-N efficiency, window {W:.0f} pkts, p={p:g}: {1/(1+p*W):.1%}")""",
      [("Ring all-reduce, N = 8 GPUs, S = 1 GB, B = 100 GB/s, ignore latency. Time?", "2·(7/8)·1/100 s = 17.5 ms."),
       ("Why is halving-doubling better than ring for small messages but not for large ones?", "Both have the same bandwidth term; halving-doubling has 2·log₂N latency steps instead of 2(N−1), which only matters when latency dominates."),
       ("A job's 16 GPUs use 4 equal-cost paths with 4 elephant flows. P(no collision)?", "4!/4⁴ = 24/256 = 9.4%.")],
      ["Patarasuk & Yuan (2009) Bandwidth optimal all-reduce algorithms for clusters of workstations. JPDC.", "Thakur, Rabenseifner, Gropp (2005) Optimization of collective communication operations in MPICH.", "Zhu et al. (2015) Congestion control for large-scale RDMA deployments (DCQCN). SIGCOMM.", "Guo et al. (2016) RDMA over commodity Ethernet at scale. SIGCOMM.", "Gangidi et al. (2024) RDMA over Ethernet for distributed AI training at Meta scale. SIGCOMM."])
newwk(15, "WAN Traffic Engineering, MPLS, Overlays and Naming", "Princeton COS 561, MIT 6.829, Stanford CS244",
      "Label switching, traffic engineering as a flow optimisation problem, max-min fairness, structured overlays (Chord) and the DNS hierarchy.",
      ["Formulate WAN traffic engineering as a multicommodity-flow problem.", "Compute max-min fair allocations by water-filling.", "Analyse lookup cost in a DHT and latency in the DNS."],
      "Chord hops ≈ ½·log₂N ;  max-min by water-filling",
      r"""## MPLS and label switching
MPLS (RFC 3031) forwards on short labels instead of IP prefixes: an ingress router classifies a packet into a forwarding equivalence class, pushes a label, and each label-switching router swaps the label by exact-match lookup until the egress pops it. Label-switched paths can follow explicit routes (RSVP-TE), enabling traffic engineering, fast reroute (pre-computed backup paths switch in tens of milliseconds) and VPNs. Segment routing (RFC 8402) encodes the path as a stack of segment identifiers in the packet and removes per-path state from the core.

## Traffic engineering as optimisation
Shortest-path routing ignores load. Given a topology with capacities cₑ and demands d_k, TE chooses how to split each demand over paths. The maximum-concurrent-flow LP is

$ maximise α  s.t.  every demand k delivers α·d_k,  and Σ flows on each link e ≤ cₑ

!! Worked example: demand A→D is 12 Gb/s and two disjoint paths of 10 Gb/s exist. Putting all traffic on the shortest path overloads it to 120% and drops 2 Gb/s (17%). Splitting 6 + 6 gives 60% utilisation on both. Google's B4 and Microsoft's SWAN centralise this computation (using SDN) and report running links much closer to full utilisation than the 30 to 40% typical of conventional WANs; SWAN reports carrying substantially more traffic than MPLS TE on the same network. Priority classes (interactive, elastic, background) let background bulk transfers fill leftover capacity.

## Max-min fairness
An allocation is max-min fair if no flow's rate can be raised without lowering a flow with an equal or smaller rate. Water-filling computes it: raise all unsatisfied flows' rates equally until one reaches its demand or the link is full.

!! Worked example: capacity 20 shared by demands 2, 4, 8, 8. Equal share 5 > 2, so flow 1 gets 2. The remaining 18 gives 6 each; flow 2 needs 4, so it gets 4. The remaining 14 gives 7 each to flows 3 and 4. Result: (2, 4, 7, 7).

## Overlays and structured DHTs
An overlay builds its own routing on top of IP. In Chord (Stoica et al. 2001) nodes and keys get m-bit identifiers on a ring; a key is stored at its successor node. Each node keeps m fingers: finger i points to the successor of n + 2ⁱ. Each hop at least halves the remaining identifier distance, so a lookup needs O(log N) hops, about ½·log₂N on average.

[[fig:chord]]

!! Worked example: N = 2²⁰ ≈ 10⁶ nodes: about 10 hops on average and at most 20, versus about 500,000 hops for walking successors. Kademlia (used in BitTorrent) uses XOR distance and parallel lookups for the same O(log N) bound with better churn tolerance.

## DNS as a global distributed database
Names are resolved down a hierarchy (root, TLD, authoritative) and cached with a time-to-live set by the owner. A resolver with cache hit rate h has mean latency h·t_cache + (1−h)·t_full.

!! Worked example: t_cache = 1 ms, t_full = 60 ms. At h = 90% the mean is 6.9 ms; at h = 99% it is 1.6 ms. Short TTLs (used for load balancing and fail-over) lower h and so cost latency. Negative caching stores NXDOMAIN answers too. Attacks and failures (the 2016 Dyn outage) show that DNS is a critical dependency, motivating anycast, multi-provider authoritative DNS and DNSSEC.

## Common pitfalls
Assuming TE gains without accounting for demand-estimation error, forgetting that DHT lookup cost excludes the real network latency of each hop, and setting very low DNS TTLs without measuring the resolver load they cause.""",
      """import math
def waterfill(cap, demands):
    alloc, left = {}, sorted(range(len(demands)), key=lambda i: demands[i])
    for k, i in enumerate(left):
        share = cap / (len(left) - k)
        alloc[i] = min(demands[i], share); cap -= alloc[i]
    return [alloc[i] for i in range(len(demands))]
print("max-min allocation:", waterfill(20, [2, 4, 8, 8]))
print("split 6+6 on 10G paths: utilisation", 6 / 10, "; unsplit: drop", 2 / 12)
for N in (2**10, 2**16, 2**20): print(f"Chord N=2^{int(math.log2(N))}: avg {0.5*math.log2(N):.0f} hops, max {math.log2(N):.0f}")
for h in (0.9, 0.95, 0.99): print(f"DNS hit rate {h:.0%}: mean latency {h*1 + (1-h)*60:.2f} ms")""",
      [("Capacity 30, demands 5, 10, 20, 20. Max-min allocation?", "Share 7.5 > 5 → flow 1 = 5; remaining 25/3 = 8.33 < 10 → flows 2,3,4 get 8.33 each: (5, 8.33, 8.33, 8.33)."),
       ("Chord with 2¹⁶ nodes: average and maximum lookup hops?", "About ½·16 = 8 and 16."),
       ("Why does a short TTL raise latency but improve failover?", "The cache expires sooner, so more queries go to authoritative servers (higher mean latency), but clients stop using a dead address after at most one TTL.")],
      ["Rosen, Viswanathan, Callon (2001) RFC 3031: Multiprotocol label switching architecture.", "Jain et al. (2013) B4: experience with a globally-deployed software defined WAN. SIGCOMM.", "Hong et al. (2013) Achieving high utilization with software-driven WAN (SWAN). SIGCOMM.", "Stoica et al. (2001) Chord: a scalable peer-to-peer lookup service. SIGCOMM.", "Maymounkov & Mazières (2002) Kademlia: a peer-to-peer information system based on the XOR metric.", "Filsfils et al. (2018) RFC 8402: Segment routing architecture."])
ALL.sort(key=lambda w: w["n"]); fin["ph"] = 5
fin["obj"] = [o for k in range(9, 16) for o in BYN[k]["obj"][:1]]
fin["body"] = fin["body"].replace("Weeks 9 to 13", "Weeks 9 to 15").replace("sketch sizing, Shannon capacity", "sketch sizing, all-reduce cost, max-min fairness, Shannon capacity")
sheet = srows(sorted(W_, key=lambda w: w["n"]))

def add2(n, assign, paper, ex):
    w = BYN[n]; w["body"] += "\n\n## Programming assignment\n" + assign + "\n\n## Paper reading guide\n" + paper; w["ex"] = w["ex"] + list(ex); ASSIGN[n] = assign
add2(1, "Build a small discrete-event simulator for store-and-forward links in Python and reproduce Figure 1 (transfer time versus hops). Then add propagation delay and per-hop processing and show for which link rates (1 Mb/s, 1 Gb/s, 100 Gb/s) transmission, propagation or processing dominates. Deliver code, a figure and a one-page explanation.",
     "Clark (1988): list the seven goals in order and name one design decision that follows from each of the first three. Saltzer et al. (1984): find three modern systems (TLS, CDN, storage checksums) and say where the 'end' is in each.",
     [("Minimum fibre RTT New York to London (5,570 km, route stretch 1.4, 2×10⁸ m/s)?", "2 × 1.4 × 5570 / 200,000 = 78 ms."), ("A 100 Mb/s link with 10 ms one-way delay: BDP?", "100×10⁶ × 0.02 / 8 = 250 KB.")])
add2(2, "Write a discrete-event simulator of an M/M/1 and an M/M/1/K queue. Compare mean delay and loss with the formulas at ρ = 0.5, 0.8, 0.9, 0.95, with confidence intervals from at least 10 runs. Then replace Poisson arrivals by ON/OFF sources with Pareto ON periods (shape 1.5) at the same mean load and show how the delay changes.",
     "Paxson & Floyd (1995): what evidence rejects Poisson models for packet arrivals, and which things (e.g. session arrivals) still look Poisson? Appenzeller et al. (2004): state the assumptions behind BDP/√n and when they fail.",
     [("Show that the Pollaczek-Khinchine formula W = 1/μ + λE[S²]/(2(1−ρ)) reduces to M/M/1 for exponential service.", "For exponential service E[S²] = 2/μ², so W = 1/μ + ρ/(μ(1−ρ)) = 1/(μ(1−ρ)) = 1/(μ−λ). For deterministic service E[S²] = 1/μ² halves the queueing term."), ("A server has 50 requests in the system on average and receives 200 requests/s. Mean response time?", "Little: W = L/λ = 50/200 = 0.25 s.")])
add2(3, "Implement (a) a link-state simulator (flooding + Dijkstra) and (b) a distance-vector simulator with and without split horizon and poisoned reverse. On a 10-node topology fail a link and plot messages sent and convergence time. Then, using a RouteViews or RIPE RIS RIB snapshot (or the toy file provided), compute the distribution of AS-path lengths.",
     "Gao & Rexford (2001): state the stability conditions in your own words and why they depend on business relationships. Labovitz et al. (2000): what was injected, what was measured, and why does path exploration happen?",
     [("Path 100→200→300→400 where 100 is a customer of 200, 200 and 300 are peers, 400 is a customer of 300. Valley-free?", "Yes: up (customer→provider), one peer link, then down (provider→customer)."), ("Why do split horizon and poisoned reverse not stop count-to-infinity in a loop of three routers?", "They only prevent two-node loops; longer loops still circulate stale distances, so hold-down timers or path-vector routing are needed.")])
add2(4, "Write a per-RTT simulator for N flows sharing a bottleneck with Reno and CUBIC. Reproduce Chiu-Jain convergence using Jain's fairness index, measure RTT unfairness (20 ms vs 80 ms flows), and plot average utilisation versus buffer size of 0.25, 0.5, 1 and 2 × BDP.",
     "Jacobson (1988): list each mechanism the paper introduces and the problem it solves. Ha, Rhee, Xu (2008): why is window growth a function of real time, and what does the TCP-friendly region do?",
     [("Jain's index J = (Σx)²/(n·Σx²) for rates (80, 10) and (45, 45)?", "(90)²/(2·6500) = 0.62; and 1.0."), ("Why does Reno need a buffer of at least one BDP to keep a link busy?", "After halving, the window is (BDP+B)/2, which must still be ≥ BDP, so B ≥ BDP.")])
add2(5, "In Mininet use tc/netem and iperf3 to run CUBIC and BBR across buffer sizes (0.1 to 8 × BDP) and RTTs (20 and 100 ms). Record goodput, retransmissions and RTT inflation, plot, and explain each regime. Repeat with fq_codel at the bottleneck.",
     "Cardwell et al. (2016): why windowed max/min filters, and what does ProbeRTT trade away? Hock et al. (2017): under which buffer sizes does BBR dominate CUBIC and why?",
     [("A 10 Mb/s uplink with a full 256 KB buffer: added queueing delay?", "256,000 × 8 / 10⁷ = 0.205 s."), ("How many bytes correspond to CoDel's 5 ms target on a 10 Mb/s link?", "10⁷/8 × 0.005 = 6,250 bytes.")])
add2(6, "Write a toy reliable transport over UDP with sequence numbers, ACK ranges, an RTT-based retransmission timer and independent streams. Fetch 20 objects over one ordered stream and over independent streams under 0 to 3% loss (netem) and plot page-load time.",
     "Langley et al. (2017): which results are medians and which are tails, and what did not improve? RFC 9000: read the sections on connection IDs and address validation and note the amplification limit.",
     [("SRTT = ⅞·SRTT + ⅛·R with SRTT = 100 ms and sample R = 180 ms. New SRTT?", "87.5 + 22.5 = 110 ms."), ("QUIC's server may send at most 3× the bytes it received before validating the client. A client Initial is padded to 1200 B. Server limit?", "3600 bytes.")])
add2(7, "Build a k = 4 fat-tree (Mininet or a flow-level simulator). On a permutation traffic matrix compare ECMP, per-packet spraying and flowlet switching and plot maximum link utilisation and the completion-time CDF. Add an incast generator (8 to 64 senders) and sweep the ECN threshold K with DCTCP-style reaction.",
     "Alizadeh et al. (2010): derive or restate the steady-state queue-size result and why a small K works. Al-Fares et al. (2008): what does the paper assume about routing and how does it differ from ECMP?",
     [("4 flows, 4 equal paths, ECMP: P(no collision)?", "4!/4⁴ = 9.4%."), ("DCTCP with α = 0.5: window cut?", "α/2 = 25%.")])
add2(9, "Write a behavioural model (P4_16 or Python) that does longest-prefix forwarding and a count-min heavy-hitter detector. Run it on a Zipf trace and report precision and recall for the top 50 flows versus sketch width. Then build a two-phase consistent update in a simulator and show a transient loop under a naive update.",
     "McKeown et al. (2008): which limitations does the paper itself acknowledge? Bosshart et al. (2014): the three goals of P4. Reitblatt et al. (2012): what per-packet consistency guarantees.",
     [("Heavy hitters: flows > 1% of N = 10⁶ packets. A sketch with ε = 0.001 overestimates by at most how much?", "εN = 1000 packets (w.h.p.), so a 10,000-packet threshold is reliable."), ("A ternary 5-tuple rule (104 bits) needs how many TCAM bits?", "About 2 × 104 = 208 (two bits per ternary bit).")])
add2(10, "Implement the link-budget calculator and then an 802.11 CSMA/CA simulator (CWmin 15, CWmax 1023, binary exponential backoff). Plot saturation throughput and collision probability versus number of stations and compare with Bianchi's model.",
     "Heusse et al. (2003): derive the equal-throughput result behind the 802.11 anomaly. Bianchi (2000): what Markov chain is used and what assumption (saturation) limits it?",
     [("One station at 1 Mb/s and one at 11 Mb/s each send 1500 B frames in turn (ignore overhead). Per-station throughput?", "12 ms + 1.09 ms per round of two frames: 12,000 bits / 13.09 ms ≈ 0.92 Mb/s each."), ("Why do 5 and 6 GHz networks need more access points than 2.4 GHz for equal coverage?", "Free-space loss grows 6 dB per frequency doubling, and walls attenuate higher frequencies more.")])
add2(11, "Build a trace-driven cache simulator (LRU, LFU and a TinyLFU-style admission filter) on a synthetic Zipf trace and plot object and byte hit ratios versus cache size. Then implement buffer-based and throughput-based ABR over recorded throughput traces and compare QoE.",
     "Breslau et al. (1999): where does the Zipf fit hold and where does it fail? Huang et al. (2014): explain the reservoir and cushion regions of the buffer-based algorithm.",
     [("Harmonic versus arithmetic mean of 4, 4, 4 and 1 Mb/s?", "Harmonic 4/1.75 = 2.29; arithmetic 3.25: the harmonic mean is the safer estimate."), ("A CDN has a 90% hit ratio and the origin can serve 10 Gb/s. Maximum total delivery rate?", "10/(1−0.9) = 100 Gb/s.")])
add2(12, "In an isolated Mininet lab (never against real hosts), build a server with a finite backlog, show how a SYN flood exhausts it and implement SYN cookies. Measure the amplification factor of a toy UDP service you write yourself. Then classify prefixes in a published RPKI validator dump as valid, invalid or unknown.",
     "Rossow (2014): which protocols and amplification factors, and how were they measured? Lychev et al. (2013): why does partial deployment of BGP security give weaker benefits than expected?",
     [("A ROA covers 10.0.0.0/20 with maxLength 22 for AS 64500. Announcement 10.0.0.0/21 from AS 64500?", "Valid: length 21 ≤ 22 and origin matches."), ("A 1 Tb/s attack is spread evenly over 10 anycast sites. Per-site load?", "100 Gb/s (in the idealised case).")])
add2(13, "Write a traceroute-style probe with scapy (or use RIPE Atlas) to 10 destinations. Compute RTT percentiles and compare with the fibre propagation lower bound; plot time-of-day variation. Then reproduce the LEO-versus-fibre crossover for your own stretch assumptions.",
     "Handley (2018): what routing and geometry assumptions underlie the latency claims? Bajpai & Schönwälder (2015): choose one platform and list its biases.",
     [("With fibre stretch 1.2, at what distance does the LEO model beat fibre?", "0.012d = 0.00733d + 7.33 → d ≈ 1,570 km."), ("Why are medians and percentiles preferred to means for RTT?", "RTT distributions are heavy-tailed; a few huge values distort the mean while percentiles describe typical and worst-case behaviour.")])
ASSIGN[14] = "Using the all-reduce model and the demo, size a fabric: for a 1,024-GPU job with 10 GB gradients, compare ring and halving-doubling at 200, 400 and 800 Gb/s per GPU. Then write a flow-level simulator of ECMP with 8 elephant flows and measure the distribution of the maximum link load over 10,000 random hash assignments."
ASSIGN[15] = "Implement water-filling max-min fairness and a path-splitting TE solver (use scipy.optimize.linprog if available, otherwise a greedy heuristic) on the Abilene topology or a toy 6-node graph. Then implement Chord finger tables in simulation and measure lookup hops for N = 2⁸ to 2¹⁴ against ½·log₂N."
fin["body"] += r"""

## Practice final exam (selected questions)
Solve these before looking at the solutions in the exercise list: pipeline latency, M/M/1, the Mathis formula, Chord hop count and all-reduce bandwidth term."""
fin["ex"] = fin["ex"] + [("Derive T for a message of P packets through N store-and-forward links.", "The first packet needs N·L/R; each of the other P−1 packets follows one transmission time later: T = (N + P − 1)·L/R."),
    ("M/M/1 with μ = 500 pkt/s, ρ = 0.8: W and L?", "λ = 400; W = 1/(500−400) = 10 ms; L = 4."),
    ("Mathis: RTT 50 ms, MSS 1460 B, p = 10⁻³. Throughput?", "1.22 × 11,680 / 0.05 / 0.0316 ≈ 9.0 Mb/s."),
    ("Chord with 2²⁰ nodes: average lookup hops?", "½·20 = 10."),
    ("Ring all-reduce, N = 16, S = 4 GB, B = 25 GB/s: bandwidth term?", "2·(15/16)·4/25 = 0.30 s.")]

DEMOS_JS = r"""(function(){var D={};function f(x,d){return(+x).toFixed(d==null?2:d)}
function tb(r){return'<table>'+r.map(function(x){return'<tr><td>'+x[0]+'</td><td><b>'+x[1]+'</b></td></tr>'}).join('')+'</table>'}
function mk(el,sp,rn){var h='<div class="dh">Interactive demo</div><div class="dc">';sp.forEach(function(s){h+='<label>'+s[1]+': <b class="v'+s[0]+'"></b><input type="range" data-k="'+s[0]+'" min="'+s[2]+'" max="'+s[3]+'" step="'+s[4]+'" value="'+s[5]+'"></label>'});el.innerHTML=h+'</div><div class="do"></div>';
function up(){var v={};el.querySelectorAll('input').forEach(function(i){v[i.dataset.k]=parseFloat(i.value);el.querySelector('.v'+i.dataset.k).textContent=i.value});el.querySelector('.do').innerHTML=rn(v)}
el.querySelectorAll('input').forEach(function(i){i.oninput=up});up()}
function svg(ss,mx){var w=600,h=200,o='<svg viewBox="0 0 '+w+' '+h+'"><rect width="'+w+'" height="'+h+'" fill="#fbf9f4"/>';ss.forEach(function(s){o+='<polyline fill="none" stroke="'+s.c+'" stroke-width="2" points="'+s.y.map(function(y,i){return(i/(s.y.length-1)*(w-10)+5).toFixed(1)+','+(h-5-Math.min(y,mx)/mx*(h-10)).toFixed(1)}).join(' ')+'"/>'});return o+'</svg>'}
D.queue=function(e){mk(e,[['rho','utilisation rho',0.05,0.99,0.01,0.8],['mu','service rate mu (pkt/s)',100,10000,100,1000],['K','buffer K (packets)',2,60,1,10]],function(v){var r=v.rho,pb=(1-r)*Math.pow(r,v.K)/(1-Math.pow(r,v.K+1));return tb([['mean delay W',f(1000/(v.mu*(1-r)))+' ms'],['mean packets in system L',f(r/(1-r))],['P(queue > K), infinite buffer',f(100*Math.pow(r,v.K+1))+' %'],['loss with K slots (M/M/1/K)',f(100*pb)+' %']])})};
D.mathis=function(e){mk(e,[['rtt','RTT (ms)',5,300,5,100],['lp','log10 of loss rate p',-7,-1,0.1,-4]],function(v){var p=Math.pow(10,v.lp),t=1.22*1460*8/(v.rtt/1000)/Math.sqrt(p)/1e6;return tb([['loss rate p',p.toExponential(1)],['TCP Reno throughput',f(t)+' Mb/s'],['average window',f(1.22/Math.sqrt(p),0)+' packets']])})};
D.link=function(e){mk(e,[['f','frequency (MHz)',900,7000,100,5000],['d','distance (m)',1,200,1,20],['tx','transmit power (dBm)',0,30,1,20],['b','bandwidth (MHz)',20,160,20,80]],function(v){var l=20*Math.log10(v.d/1000)+20*Math.log10(v.f)+32.44,n=-174+10*Math.log10(v.b*1e6)+5,s=v.tx-l-n;return tb([['path loss',f(l,1)+' dB'],['received power',f(v.tx-l,1)+' dBm'],['noise floor (NF 5 dB)',f(n,1)+' dBm'],['SNR',f(s,1)+' dB'],['Shannon capacity',f(v.b*Math.log2(1+Math.pow(10,s/10)),0)+' Mb/s']])})};
D.zipf=function(e){mk(e,[['a','Zipf exponent alpha',0.5,1.5,0.05,1],['n','log10 catalogue size',3,6,0.5,5],['c','cache size (% of catalogue)',0.1,20,0.1,1]],function(v){var N=Math.round(Math.pow(10,v.n)),C=Math.floor(v.c/100*N),s=0,t=0;for(var i=1;i<=N;i++){var x=Math.pow(i,-v.a);t+=x;if(i<=C)s+=x}return tb([['catalogue',N.toLocaleString()],['objects cached',C.toLocaleString()],['hit ratio',f(100*s/t,1)+' %']])})};
D.fat=function(e){mk(e,[['k','ports per switch k',4,128,2,48]],function(v){var k=v.k;return tb([['pods',k],['hosts k^3/4',(k*k*k/4).toLocaleString()],['switches 5k^2/4',(5*k*k/4).toLocaleString()],['core switches (k/2)^2',(k*k/4).toLocaleString()],['equal-cost paths between pods',(k*k/4).toLocaleString()]])})};
D.ring=function(e){mk(e,[['s','log10 message size (GB)',-3,1,0.1,0],['n','log2 of GPUs',1,11,1,6],['b','GB/s per GPU',10,100,10,50],['a','step latency (us)',1,20,1,5]],function(v){var S=Math.pow(10,v.s)*1e9,N=Math.pow(2,v.n),B=v.b*1e9,a=v.a*1e-6,bw=2*(N-1)/N*S/B,r=bw+2*(N-1)*a,h=bw+2*Math.log2(N)*a;return tb([['GPUs',N],['message',f(S/1e6,1)+' MB'],['bandwidth term 2(N-1)/N*S/B',f(bw*1e3,3)+' ms'],['ring all-reduce',f(r*1e3,3)+' ms'],['halving-doubling',f(h*1e3,3)+' ms'],['ring / halving-doubling',f(r/h,1)+'x']])})};
D.cc=function(e){mk(e,[['cap','path capacity (packets)',50,800,10,400],['rtt','RTT (ms)',10,300,10,100]],function(v){var c=v.cap,R=[],C=[],w=c/2,t=0,K=Math.cbrt(c*0.3/0.4),u=0.7*c,sr=0,sc=0,n=400;for(var i=0;i<n;i++){w+=1;if(w>c)w/=2;R.push(w);sr+=w;t+=v.rtt/1000;u=0.4*Math.pow(t-K,3)+c;if(u>c){u=0.7*c;t=0}C.push(u);sc+=u}return svg([{c:'#1f6f78',y:R},{c:'#c0562b',y:C}],c)+'<p><b style="color:#1f6f78">Reno</b> avg window '+f(sr/n,0)+' ('+f(100*sr/n/c,0)+'% of capacity) &nbsp; <b style="color:#c0562b">CUBIC</b> avg window '+f(sc/n,0)+' ('+f(100*sc/n/c,0)+'%)</p>'})};
document.querySelectorAll('.demo').forEach(function(e){var d=D[e.dataset.demo];if(d)d(e)})})();"""
open(OUT + "/assets/demos.js", "w", encoding="utf-8").write(DEMOS_JS)
CSS_EXTRA = ".demo{background:#fff;border:1px solid #1f6f78;border-radius:8px;margin:1.4em 0;overflow:hidden}.dh{background:#1f6f78;color:#fff;font:600 12px system-ui;padding:5px 12px;letter-spacing:.05em;text-transform:uppercase}.dc{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;padding:12px;font:13px system-ui}.dc input{width:100%}.do{padding:0 12px 12px;font:14px system-ui}.do svg{width:100%;height:auto;border-radius:6px}.do table{margin:0}"
for n_, d_ in (("cc", 4), ("queue", 2), ("mathis", 5), ("link", 10), ("zipf", 11), ("fat", 7)):
    w_ = BYN[d_]; marker = "\n\n## " + {4: "Common pitfalls", 2: "Common pitfalls", 5: "Common pitfalls", 10: "Common pitfalls", 11: "Common pitfalls", 7: "Common pitfalls"}[d_]
    w_["body"] = w_["body"].replace(marker, f"\n\n[[demo:{n_}]]" + marker, 1) if marker in w_["body"] else w_["body"] + f"\n\n[[demo:{n_}]]"

def post():
    rd = "<h1>Reading list</h1><p class='lead'>Every reading in the course, by week. Items marked in the first position of each week are the essential ones.</p>" + "".join(f"<h2>Week {w['n']}: {html.escape(w['title'])}</h2><ul>" + "".join(f"<li>{html.escape(r)}</li>" for r in w["rd"]) + "</ul>" for w in ALL)
    page("reading.html", "Reading list", "rd", rd)
    a = "<h1>Assignments</h1><p class='lead'>One programming assignment per content week. Each is designed to take 4 to 8 hours and to reproduce a figure or result from the notes.</p>" + "".join(f"<h2>Week {n}: {html.escape(BYN[n]['title'])}</h2><p>{html.escape(t)}</p>" for n, t in sorted(ASSIGN.items()))
    page("assignments.html", "Assignments", "as", a)
    if "post_book" in globals(): post_book()
