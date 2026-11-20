# executed inside build.py (shares its globals)
rr_ = [0.6 + 0.02 * i for i in range(41)]
def pb(r, K): return 1 / (K + 1) if abs(r - 1) < 1e-9 else (1 - r) * r ** K / (1 - r ** (K + 1))
plot("mm1k", "Blocking probability of an M/M/1/K queue (K = total buffer slots) versus offered load. Even at ρ < 1 a small buffer drops packets; at ρ = 1 loss is exactly 1/(K+1).",
     [(f"K = {K}", rr_, [pb(r, K) for r in rr_]) for K in (5, 10, 20)], "offered load ρ", "blocking probability", False, True)
nn_ = list(range(1, 201))
plot("hol", "Probability that a burst of n packets contains at least one loss, for three random loss rates. With HTTP/2 over TCP one such loss stalls every multiplexed stream.",
     [(f"p = {p*100:g}%", nn_, [100 * (1 - (1 - p) ** n) for n in nn_]) for p in (0.001, 0.01, 0.02)], "packets in flight n", "P(at least one loss) (%)")
dm = list(range(5, 101, 5))
plot("fspl", "Free-space path loss versus distance. Each doubling of distance costs 6 dB, and each doubling of frequency also costs 6 dB, which is why 5 and 6 GHz Wi-Fi reach less far than 2.4 GHz.",
     [(f"{f/1000:g} GHz", dm, [20 * math.log10(d / 1000) + 20 * math.log10(f) + 32.44 for d in dm]) for f in (2400, 5000, 6000)], "distance (m)", "path loss (dB)")
def abr(fixed, n=20, thr=3.0, chunk=4.0, b=8.0):
    out = []
    for _ in range(n):
        bit = fixed if fixed else max(x for x in (1.0, 2.5, 5.0) if x <= 0.9 * thr)
        b = max(0, b - bit * chunk / thr) + chunk; out.append(min(b, 30))
    return out
plot("abr", "Playback buffer after each 4 s chunk when throughput is 3 Mb/s: a fixed 5 Mb/s rendition drains the buffer into repeated stalls; an adaptive player settles on 2.5 Mb/s and builds a cushion.",
     [("fixed 5 Mb/s", list(range(1, 21)), abr(5.0)), ("adaptive", list(range(1, 21)), abr(None))], "chunk number", "buffer (s)")

def add(n, body, ex=(), code=""):
    w = next(x for x in ALL if x["n"] == n); w["body"] += "\n\n" + body; w["ex"] = w["ex"] + list(ex)
    if code: w["code"] += "\n\n" + code

add(1, r"""## Encapsulation overhead and goodput
Every layer adds a header, so useful throughput is below link rate. On Ethernet each frame carries 38 bytes of overhead on the wire (8 preamble, 14 header, 4 FCS, 12 inter-frame gap). A full 1500-byte IP packet holds 20 B IP + 20 B TCP + 1460 B payload.

$ efficiency = payload / (payload + headers + 38)

!! Worked example: IPv4/TCP: 1460/1538 = 94.9%. IPv6/TCP (40 B IP header): 1440/1538 = 93.6%. A 1-byte telnet keystroke is padded to the 46-byte minimum, so 1/84 = 1.2% of the wire carries data.

## Where the architecture bends
NAT (and carrier-grade NAT) breaks the end-to-end model: hosts behind a NAT are not addressable, so peer-to-peer applications need STUN/ICE hole-punching or relays. IPv6 restores global addressing; its adoption is now a large fraction of users (check Google's IPv6 statistics for the current figure) but dual-stack operation will last for years. Middleboxes (firewalls, load balancers, DPI) violate fate-sharing and ossify protocols, a theme that returns in Week 6 (QUIC) and Week 9 (NFV).

## Common pitfalls
Confusing bits and bytes (link rates are bits/s, buffers are bytes), forgetting that propagation delay does not depend on bandwidth, and assuming a 'fast' link has low latency: a 10 Gb/s satellite link still has a 480 ms floor.""",
    [("What fraction of a 10 Gb/s Ethernet link carries TCP payload with 9000 B jumbo frames (IPv4)?", "Payload 8960 B over 9000+38 = 9038 B on the wire: 99.1%."),
     ("Why does doubling link bandwidth not halve the latency of a 1 KB web request?", "Transmission time is only part of delay; propagation, handshakes and queueing do not scale with bandwidth.")],
    """def goodput(mtu=1500, ip=20, l4=20, wire=38): return (mtu - ip - l4) / (mtu + wire)
print(f"IPv4/TCP {goodput():.1%}   IPv6/TCP {goodput(ip=40):.1%}   jumbo {goodput(9000):.1%}")
print("1-byte payload:", f"{1 / (46 + 38):.1%}")""")

add(2, r"""## Deriving the M/M/1 distribution
Let πₙ be the stationary probability of n packets. In steady state the flow across each cut between n and n+1 balances: λπₙ = μπₙ₊₁, so πₙ₊₁ = ρπₙ and πₙ = (1−ρ)ρⁿ after normalising. Then

$ L = Σ n·πₙ = ρ / (1 − ρ),    P(queue > k) = ρᵏ⁺¹

## Finite buffers: M/M/1/K
Real routers have K slots. Loss (blocking) probability is

$ P_block = (1−ρ)·ρᴷ / (1 − ρᴷ⁺¹)    (ρ = 1: 1/(K+1))

!! Worked example: ρ = 0.9, K = 10 gives 0.1 × 0.349 / 0.686 = 5.1% loss even though the link is not overloaded. Doubling K to 20 reduces it to about 1.4%.

[[fig:mm1k]]

## How big should buffers be?
The folklore rule is one bandwidth-delay product. Appenzeller et al. (2004) showed that with n long-lived, desynchronised flows the needed buffer is BDP/√n.

!! Worked example: 10 Gb/s, RTT 250 ms, BDP = 312 MB. With n = 10,000 flows, 312/100 = 3.1 MB suffices. Too little costs utilisation; too much costs latency (bufferbloat, Week 5).

## Common pitfalls
Applying M/M/1 to bursty traffic (underestimates queues), forgetting packet-size variability (use M/G/1: W = 1/μ + λE[S²]/(2(1−ρ))), and treating utilisation averages as if they say anything about bursts.""",
    [("Using P(queue > k) = ρᵏ⁺¹, how many buffer slots keep overflow below 1% at ρ = 0.8 (infinite-queue approximation)?", "0.8^(k+1) < 0.01 → k+1 > ln0.01/ln0.8 = 20.6 → k = 20 slots."),
     ("A router has 10 Gb/s ports, 100 ms average RTT and 400 flows. What buffer does the BDP/√n rule give?", "BDP = 125 MB; /√400 = 20 → 6.25 MB.")],
    """def pblock(rho, K): return 1 / (K + 1) if rho == 1 else (1 - rho) * rho ** K / (1 - rho ** (K + 1))
for K in (5, 10, 20): print(f"rho=0.9 K={K:2d}: loss = {pblock(0.9, K):.2%}")
print("rho=1.0 K=10:", f"{pblock(1.0, 10):.2%}")
print("BDP/sqrt(n) buffer:", 10e9 * 0.25 / 8 / 1e6 / 100, "MB")""")

add(3, r"""## The Bellman-Ford equation
Distance-vector routing is the distributed solution of

$ dₓ(y) = min over neighbours v of { c(x,v) + d_v(y) }

!! Worked example: x–y cost 2, y–z cost 3, x–z cost 7. x's distance to z is min(7, 2+3) = 5, via y. Each router recomputes whenever a neighbour's vector changes and re-advertises if its own changes.

## Costs of each approach
Link-state floods each link-state advertisement once over every link (at most 2E transmissions per event), then every router runs Dijkstra in O(E log V). Distance-vector sends O(neighbours) small vectors but needs up to O(diameter) rounds, plus count-to-infinity on failures. Large networks add OSPF areas (summarise at area borders) and IS-IS levels to bound flooding.

## BGP convergence
Labovitz et al. (2000) found that after a withdrawal BGP needs about three minutes on average and sometimes much longer, because routers explore successively longer alternative paths (path exploration) and rate-limit updates with the MRAI timer (30 s default for eBGP). Mitigations: route flap damping (controversial), BGP-RR with add-paths, and fast reroute in the data plane (IP FRR, MPLS).

## Valley-free paths
A path is valley-free if it climbs customer→provider links, crosses at most one peer link, then descends provider→customer links. Because customers pay providers and peers exchange traffic for free, an AS exports peer and provider routes only to customers. A path that goes provider → customer → provider (a valley) means a customer is giving free transit and would be rejected by export policy.

## IPv4 table growth
The global IPv4 routing table has been near or above one million prefixes in recent years, forcing TCAM upgrades and motivating aggregation. Deaggregation for traffic engineering is a common cause of growth.""",
    [("A network has 100 links. At most how many LSA transmissions does one link-cost change trigger?", "Each LSA crosses each link at most once per direction: ≤ 2E = 200."),
     ("Why does the MRAI timer slow convergence but protect routers?", "It batches updates per neighbour (30 s), reducing churn and CPU load at the cost of delaying each propagation step, so path exploration takes longer in wall-clock time.")],
    """def bellman_ford(nodes, edges, src):
    d = {n: float("inf") for n in nodes}; d[src] = 0
    for _ in range(len(nodes) - 1):
        for u, v, w in edges:
            if d[u] + w < d[v]: d[v] = d[u] + w
            if d[v] + w < d[u]: d[u] = d[v] + w
    return d
print(bellman_ford("xyz", [("x", "y", 2), ("y", "z", 3), ("x", "z", 7)], "x"))""")

add(4, r"""## Deriving Reno's throughput
In a sawtooth between W/2 and W, one cycle lasts W/2 RTTs and sends the area under the line: (W/2)·(3W/4) = 3W²/8 packets. If one packet in 1/p is lost, 3W²/8 = 1/p, so W = √(8/(3p)). Average throughput is (¾W)·MSS/RTT:

$ Thr = (MSS/RTT) · √(3/2) / √p = 1.22 · MSS / (RTT·√p)

This is the Mathis formula of Week 5, now derived: throughput scales as 1/RTT and 1/√p.

## Slow start and short flows
Most flows are short, so slow start, not congestion avoidance, dominates their completion time. With initial window IW = 10 segments (RFC 6928) the window doubles every RTT: 10, 20, 40, 80...

!! Worked example: a 100 KB response is 69 segments of 1460 B. Windows 10 + 20 + 40 = 70 ≥ 69, so after the handshake it needs 3 RTTs. At 100 ms RTT that is 300 ms no matter how fast the link is: latency, not bandwidth, limits short transfers.

## Loss recovery
Fast retransmit resends after 3 duplicate ACKs (without waiting for the timeout); SACK tells the sender exactly which segments arrived, avoiding go-back-N waste; the retransmission timeout uses RTO = SRTT + 4·RTTVAR (Jacobson). Timeouts reset cwnd to 1 and are expensive, so tail loss probes (TLP/RACK) try to convert them into fast recovery.

## Common pitfalls
Comparing algorithms with a single flow and one RTT, measuring throughput before the flow leaves slow start, and ignoring ACK compression or delayed ACKs when reading cwnd traces.""",
    [("How many RTTs does slow start with IW = 10 need to reach a window of 640?", "10·2ⁿ ≥ 640 → n = 6 RTTs."),
     ("A Reno flow sees p = 10⁻⁴. What is W and average cwnd?", "W = √(8/(3·10⁻⁴)) ≈ 163 packets; average ¾W ≈ 122 packets.")],
    """import math
def slow_start_rtts(segments, iw=10):
    sent, w, rtt = 0, iw, 0
    while sent < segments: sent += w; w *= 2; rtt += 1
    return rtt
print("100 KB (69 segs):", slow_start_rtts(69), "RTTs;  1 MB (685 segs):", slow_start_rtts(685), "RTTs")
p = 1e-4; W = math.sqrt(8 / (3 * p)); print(f"Reno W={W:.0f}  avg cwnd={0.75 * W:.0f} packets")""")

add(5, r"""## Active queue management
RED drops or marks with probability rising linearly between two queue thresholds; it is hard to tune. CoDel (RFC 8289) instead tracks the minimum sojourn time of packets over an interval (100 ms) and starts dropping when it stays above a target (5 ms), so it needs no tuning across link speeds. FQ-CoDel adds per-flow queues so a bulk flow cannot delay a sparse one. ECN lets routers mark instead of drop; L4S (RFC 9330-9332) uses a dedicated scalable-marking queue for ultra-low latency.

## BBR in detail
BBR cycles through four states: Startup (pacing gain 2/ln 2 ≈ 2.89 to find BtlBw quickly), Drain (empty the queue Startup built), ProbeBW (gain cycle 1.25, 0.75, then six rounds at 1.0) and ProbeRTT (every 10 s, cut inflight to 4 packets for 200 ms to re-measure RTprop). The in-flight cap is cwnd_gain × BtlBw × RTprop with cwnd_gain = 2.

!! Worked example: BtlBw = 100 Mb/s, RTprop = 40 ms: BDP = 500 KB, so BBR caps inflight at 1 MB. With a deep buffer it can leave up to one BDP of standing queue (40 ms of extra delay) in the worst case.

## Fairness issues
Hock et al. (2017) and others measured BBR v1 against CUBIC: with deep buffers BBR can take a share set by its 2×BDP cap, nearly independent of the number of CUBIC flows; with shallow buffers it ignores loss and can cause high retransmission rates. BBRv2/v3 react to loss and ECN to coexist better. The lesson: a congestion-control comparison must report buffer size, RTT mix and flow count.

## Common pitfalls
Declaring a winner from one buffer size, forgetting that pacing needs fine-grained timers (fq qdisc on Linux), and assuming delay-based control is 'safe' when sharing with loss-based flows.""",
    [("BtlBw = 50 Mb/s, RTprop = 80 ms. What is BBR's maximum inflight?", "BDP = 500 KB; × cwnd_gain 2 = 1 MB (≈ 685 packets of 1460 B)."),
     ("Why does CoDel use minimum sojourn time rather than average queue length?", "A good queue (absorbing a burst) drains within an interval, so the minimum is low; a bad standing queue keeps even the minimum high. The average would confuse the two.")],
    """bw, rt = 50e6, 0.08
bdp = bw * rt / 8
print(f"BDP = {bdp/1e3:.0f} KB, BBR inflight cap = {2*bdp/1e6:.1f} MB = {2*bdp/1460:.0f} packets")
import math; print("Startup gain 2/ln2 =", round(2 / math.log(2), 3))""")

add(6, r"""## Loss recovery in QUIC
Packet numbers in QUIC never repeat, so there is no retransmission ambiguity (a classic TCP RTT-sampling problem); lost data is resent in new packets. ACK frames carry ranges, loss detection uses packet and time thresholds, and a probe timeout (PTO) replaces the RTO (RFC 9002). Flow control operates per stream and per connection.

## Quantifying head-of-line blocking
If each packet is lost independently with probability p, the chance that a burst of n packets contains at least one loss is

$ 1 − (1 − p)ⁿ

!! Worked example: p = 1% and n = 100 in flight: 1 − 0.99¹⁰⁰ = 63%. With HTTP/2 over TCP, in most such windows every multiplexed stream pauses until the lost segment is retransmitted (about one RTT); with QUIC only the affected stream waits.

[[fig:hol]]

## TLS 1.3 and HTTP/3
TLS 1.3 needs one round trip: the client sends its key share in ClientHello, the server replies with its share, certificate and Finished, and application data follows. Forward secrecy is mandatory. HTTP/3 (RFC 9114) maps HTTP semantics onto QUIC streams and replaces HPACK with QPACK to avoid header-compression blocking.

## Common pitfalls
Assuming QUIC is always faster (on clean low-RTT links the gain is small and user-space CPU cost is higher), blocking UDP 443 so browsers fall back silently, and forgetting that 0-RTT is replayable.""",
    [("p = 0.5%, 40 packets in flight. P(at least one loss)?", "1 − 0.995⁴⁰ = 1 − 0.818 = 18.2%."),
     ("Why does QUIC encrypt packet headers' transport fields?", "To prevent middleboxes from depending on, or modifying, them: this keeps the protocol evolvable (anti-ossification) and hides metadata.")],
    """def p_loss(p, n): return 1 - (1 - p) ** n
for p, n in ((0.01, 100), (0.005, 40), (0.001, 100)): print(f"p={p:.3f} n={n:3d}: P(>=1 loss) = {p_loss(p, n):.1%}")""")

add(7, r"""## Leaf-spine and oversubscription
Production fabrics are often two-tier leaf-spine (a folded Clos). Oversubscription is the ratio of server-facing to uplink capacity at a leaf.

$ oversubscription = (downlinks × rate) / (uplinks × rate)

!! Worked example: a leaf with 48 × 10 Gb/s server ports and 4 × 40 Gb/s uplinks: 480/160 = 3:1. If every server sends at line rate across racks each gets only a third of its rate; in practice utilisation is lower, so 2:1 to 4:1 is common for general racks and 1:1 for storage or ML clusters.

## Incast, quantified
!! Worked example: 40 servers each return a 32 KB response to one client: 1.28 MB arrives simultaneously, but the shallow switch port buffer is 128 KB, so ~90% overflows. TCP then waits for its 200 ms minimum RTO while the RTT is about 100 µs: a 2000x mismatch that idles the link. Vasudevan et al. (2009) showed that microsecond-granularity timers (RTO_min ≈ 1 ms) restore throughput; DCTCP and receiver-driven transports avoid the overflow in the first place.

## Load balancing beyond ECMP
VL2 uses Valiant load balancing (random intermediate switch) to make any traffic matrix look uniform. Flowlet switching (CONGA) re-hashes a flow only after an idle gap longer than the path-delay difference, so packets stay in order. Packet spraying (NDP, Ultra Ethernet) balances perfectly at the cost of reordering. RDMA over Converged Ethernet needs lossless fabrics (PFC) whose head-of-line blocking and deadlock risks drive new congestion control (DCQCN, HPCC).

## Common pitfalls
Quoting full bisection bandwidth without looking at hashing, forgetting that tail latency (99.9th percentile) decides partition-aggregate performance, and enabling PFC everywhere without deadlock analysis.""",
    [("A leaf has 32 × 25 Gb/s down and 8 × 100 Gb/s up. Oversubscription?", "800/800 = 1:1 (non-blocking)."),
     ("How many hosts and switches does a k = 8 fat-tree have?", "Hosts k³/4 = 128; switches 5k²/4 = 80.")],
    """print("oversubscription 48x10G / 4x40G =", (48 * 10) / (4 * 40), ":1")
resp, n, buf = 32e3, 40, 128e3
print(f"incast burst {n*resp/1e6:.2f} MB vs buffer {buf/1e3:.0f} KB -> {1 - buf/(n*resp):.0%} overflow")
print("RTO/RTT mismatch:", 0.2 / 100e-6)""")

add(9, r"""## Consistent network updates
Changing many switches' rules one by one can create transient loops or black holes. Reitblatt et al. (2012) proposed per-packet consistent updates by two-phase commit: install the new rules tagged with a new version on the internal switches first, then flip the ingress switches to stamp packets with the new version, and finally remove old rules. Every packet is processed entirely by the old or the new configuration, never a mix.

## Network verification
Because configurations are code, they can be checked. Header Space Analysis (Kazemian et al. 2012) treats packet headers as bit vectors and rules as transformations to answer reachability and loop questions; Batfish (Fogel et al. 2015) analyses router configurations offline. Verification finds bugs like unintended reachability or missing route filters before deployment.

## Virtualised network functions
NFV moves firewalls, NATs and load balancers from appliances to software on commodity servers (Sherry et al. 2012 argued for outsourcing middleboxes). Challenges: per-packet cost at 100 Gb/s (DPDK, kernel bypass, SmartNICs), state migration during scaling, and service chaining. eBPF/XDP now processes packets inside the Linux kernel at tens of millions of packets per second per core group.

## The programmable pipeline, in numbers
A switch ASIC such as a 12.8 Tb/s chip handles billions of packets per second in a fixed number of match-action stages; each stage has limited SRAM/TCAM, so telemetry must be compressed (sketches) and rules aggregated. In-band network telemetry (INT) lets each hop append queue depth and timestamps to a packet, giving per-hop latency visibility.

## Common pitfalls
Treating the controller as always available, forgetting TCAM limits (a ternary entry costs about twice the bits of an exact entry), and updating rules without ordering guarantees.""",
    [("Why are count-min sketches mergeable across switches?", "With identical hash functions the counter arrays are linear: adding two sketches element-wise gives the sketch of the combined stream, so a controller can merge per-switch sketches."),
     ("In a two-phase update, why must internal switches be updated before the ingress?", "If ingress stamped the new version first, packets would reach internal switches lacking rules for it and be dropped.")],
    """import random
random.seed(3); w, d = 256, 3
ab = [(random.randrange(1, 10**9), random.randrange(10**9)) for _ in range(d)]
h = lambda j, x: (ab[j][0] * x + ab[j][1]) % 1000003 % w
def sketch(stream):
    t = [[0] * w for _ in range(d)]
    for x in stream:
        for j in range(d): t[j][h(j, x)] += 1
    return t
A, B = [1, 2, 2, 3] * 50, [2, 4, 4, 4] * 50
SA, SB = sketch(A), sketch(B); M = [[a + b for a, b in zip(r1, r2)] for r1, r2 in zip(SA, SB)]
est = lambda S, x: min(S[j][h(j, x)] for j in range(d))
print("merged estimate of flow 2:", est(M, 2), "  true:", (A + B).count(2))
print("merged equals sketch of concatenation:", M == sketch(A + B))""")

add(10, r"""## Link budget
Free-space path loss (d in km, f in MHz) is

$ FSPL(dB) = 20·log₁₀(d) + 20·log₁₀(f) + 32.44

[[fig:fspl]]

!! Worked example: 2.4 GHz at 100 m: −20 + 67.6 + 32.4 = 80.0 dB. Transmit 20 dBm → receive −60 dBm. Thermal noise over 20 MHz is −174 + 73 = −101 dBm; with a 5 dB receiver noise figure the floor is −96 dBm, so SNR = 36 dB (≈ 3981x). Shannon capacity is 20 × log₂(3982) ≈ 239 Mb/s: an upper bound, since real MCS tables need extra margin. At 5 GHz the loss is 86.4 dB (6.4 dB more), giving SNR 29.6 dB and about 197 Mb/s.

## Walls, fading and MIMO
Indoors, walls add 3 to 15 dB each and multipath causes fading: signals add and cancel over a wavelength. OFDM splits a channel into many narrow subcarriers (e.g. 64 to 2048), so frequency-selective fading hits only some of them and each has a long symbol that tolerates multipath delay. MIMO beamforming and spatial multiplexing exploit multipath; MU-MIMO serves several users at once.

## Cellular overview
LTE/5G use scheduled access: the base station assigns resource blocks per millisecond-scale slot, with HARQ retransmissions at the link layer. 5G NR numerology scales subcarrier spacing (15 to 120 kHz), and millimetre-wave bands offer wide channels but short range and blockage, needing dense small cells and beam tracking. Handover keeps a connection alive when the user moves; TCP sees it as a delay or burst loss.

## Common pitfalls
Quoting PHY rates as throughput (MAC overhead and contention often halve them), forgetting that capacity is per-cell, shared by all clients, and testing Wi-Fi from one location only.""",
    [("Compute FSPL at 5 GHz at 50 m.", "20log₁₀(0.05) + 20log₁₀(5000) + 32.44 = −26.0 + 74.0 + 32.4 = 80.4 dB."),
     ("Why does doubling transmit power (+3 dB) give much less than 2x throughput at high SNR?", "Capacity is logarithmic in SNR: +3 dB adds about one bit/s/Hz, so at 6.7 b/s/Hz that is a ~15% increase.")],
    """import math
def fspl(d_m, f_mhz): return 20 * math.log10(d_m / 1000) + 20 * math.log10(f_mhz) + 32.44
def cap(B_mhz, snr_db): return B_mhz * math.log2(1 + 10 ** (snr_db / 10))
for f in (2400, 5000):
    loss = fspl(100, f); rx = 20 - loss; snr = rx - (-96)
    print(f"{f/1000:g} GHz @100 m: loss {loss:.1f} dB, rx {rx:.1f} dBm, SNR {snr:.1f} dB, Shannon {cap(20, snr):.0f} Mb/s")""")

add(11, r"""## ABR dynamics
!! Worked example: chunks are 4 s long, renditions are 1, 2.5 and 5 Mb/s and measured throughput is 3 Mb/s. A 5 Mb/s chunk is 20 Mb and takes 6.67 s to download, draining 2.67 s of buffer per chunk; a 2.5 Mb/s chunk takes 3.33 s and adds 0.67 s. Starting with an 8 s buffer, the first 5 Mb/s chunk leaves 1.33 s, the 4 s of video it delivered brings the buffer to 5.33 s, and the second chunk (6.67 s to download) already stalls; the player then stays at the edge of stalling.

[[fig:abr]]

## QoE and control
A common QoE model: QoE = Σ bitrate − μ · rebuffer time − λ · Σ|bitrate change|. Throughput-rule players use a safety factor (e.g. pick the top rendition at most 90% of the harmonic-mean estimate); buffer-based players map buffer level to bitrate with a reservoir (e.g. 5 to 10 s) and a cushion; MPC chooses the next several chunks by solving a short-horizon optimisation; Pensieve learns the policy with reinforcement learning. Low-latency live streaming (LL-HLS, CMAF chunked transfer) shrinks chunks to under 1 s, shrinking buffers and making estimation harder.

## CDN internals
Consistent hashing assigns each object to a server in a ring so that adding or removing a server remaps only about 1/n of objects. Hierarchical caching (edge, mid-tier, origin shield) multiplies effective hit ratio and protects the origin. Cache replacement (LRU, LFU, TinyLFU, GDSF) matters because one-hit wonders can pollute caches: admission filters help.

## Common pitfalls
Assuming popularity is static (viral content breaks Zipf fits), using arithmetic means of throughput, and ignoring startup delay in QoE.""",
    [("With an 8 s buffer, 3 Mb/s throughput and fixed 5 Mb/s chunks of 4 s, during which chunk download does the first stall occur?", "Download takes 6.67 s. Chunk 1: buffer 8 → 1.33, +4 = 5.33 s. Chunk 2 needs 6.67 s > 5.33 s, so it stalls (1.33 s) during the second chunk."),
     ("With 20 servers on a consistent-hash ring, what fraction of keys moves when one server is added?", "About 1/21 ≈ 4.8%.")],
    """def sim(fixed=None, n=8, thr=3.0, chunk=4.0, b=8.0):
    stalls = 0
    for _ in range(n):
        bit = fixed or max(x for x in (1.0, 2.5, 5.0) if x <= 0.9 * thr)
        dl = bit * chunk / thr
        if dl > b: stalls += 1
        b = max(0, b - dl) + chunk
    return stalls, round(b, 1)
print("fixed 5 Mb/s (stalls, final buffer):", sim(5.0))
print("adaptive     (stalls, final buffer):", sim())""")

add(12, r"""## Why SYN cookies matter
A server keeps a half-open entry for each SYN until the handshake completes or times out. Linux retries the SYN-ACK five times (1+2+4+8+16+32 = 63 s).

!! Worked example: with a backlog of 1024 entries and 63 s lifetime, an attacker needs only 1024/63 ≈ 16 spoofed SYNs per second to keep the queue full. With SYN cookies the server stores nothing until a valid ACK arrives, so the table cannot be exhausted.

## DNSSEC chain of trust
The root zone's key is the trust anchor. Each parent publishes a DS record (hash of the child's key); the child's DNSKEY signs its records as RRSIGs. A validating resolver follows root → TLD → domain, so a forged answer fails validation. DNSSEC does not encrypt queries and amplifies responses (a cost for DDoS); DoT/DoH protect privacy.

## RPKI in detail
A ROA says 'AS X may originate prefix P up to maximum length m'. A route is valid if a matching ROA exists, invalid if one covers it but the origin or length mismatches, and unknown if none covers it. For ROA 10.0.0.0/16 with maxLength 16, a hijacker announcing 10.0.1.0/24 is invalid. Over-generous maxLength values reopen subprefix hijacks, so best practice is exact lengths.

## Defence in depth for DDoS
Anycast spreads attack traffic across many sites, each absorbing its share; scrubbing centres filter at volumetric scale; rate limits, response-rate limiting and disabling open resolvers shrink reflector pools; BCP 38/84 stop spoofing near the source; QUIC's address-validation tokens and retry packets limit amplification by requiring clients to prove their address.

## Common pitfalls
Equating encryption with authentication (an encrypted channel to the wrong server is still wrong), forgetting that anycast does not stop application-layer floods, and writing RPKI ROAs with maxLength larger than needed.""",
    [("A server has a 4096-entry SYN backlog and 63 s half-open lifetime. SYN rate needed to fill it?", "4096/63 ≈ 65 SYN/s."),
     ("A ROA authorises AS 64500 for 192.0.2.0/24, maxLength 24. What is the status of 192.0.2.0/25 from AS 64500?", "Invalid: it is more specific than the maxLength allows.")],
    """backlog, life = 1024, 1 + 2 + 4 + 8 + 16 + 32
print("half-open lifetime:", life, "s;  SYN/s to fill backlog:", round(backlog / life, 1))
def roa(prefix_len, maxlen, origin, roa_as): return "valid" if origin == roa_as and prefix_len <= maxlen else "invalid"
print("/16 from owner:", roa(16, 16, 64500, 64500), "  /24 hijack from owner AS:", roa(24, 16, 64500, 64500), "  /16 from attacker:", roa(16, 16, 666, 64500))""")

add(13, r"""## Statistics for measurement
Network measurements are heavy-tailed, so report medians and percentiles (p95, p99), not just means, and give uncertainty. For n independent samples with standard deviation s, a 95% confidence interval for the mean is x̄ ± 1.96·s/√n.

!! Worked example: n = 100 RTT samples with s = 20 ms: ±1.96 × 20/10 = ±3.9 ms. To halve that, you need four times as many samples. RTT samples are correlated in time, so effective n is smaller than it looks.

## Orbital mechanics for LEO
A satellite at altitude h orbits with period T = 2π√(a³/μ), a = R + h, μ = 398,600 km³/s². For h = 550 km, a = 6921 km and T ≈ 5730 s ≈ 95.5 min. A given satellite is visible to a ground terminal for only a few minutes, so connections hand over between satellites constantly, causing RTT steps and sometimes reordering that confuse congestion control.

## Machine learning for networking
Remy (Winstein and Balakrishnan 2013) synthesises congestion-control rules offline from a network model; Pensieve (Week 11) learns video bitrate selection; Aurora trains deep-RL congestion control. Open questions are generalisation to unseen networks, safety under adversarial conditions, and explainability. A good rule: treat a learned controller as correct only inside the training distribution, and add guard rails.

## IoT and LPWAN
Low-power wide-area networks (LoRaWAN, NB-IoT) trade data rate (hundreds of bit/s to tens of kb/s) for kilometres of range and years of battery life using duty-cycled radios and long symbols. Constraints: tiny payloads, regulatory duty cycles (often 1%), and security on constrained devices.

## Common pitfalls
Using a single vantage point, ignoring time-of-day effects, and reporting 'average speed' from tests that only measure the home access link.""",
    [("A Starlink-like shell at 1200 km altitude: orbital period?", "a = 7571 km; T = 2π√(7571³/398600) ≈ 6,560 s ≈ 109 min."),
     ("100 RTT samples have s = 15 ms. 95% CI half-width for the mean?", "1.96 × 15/10 = 2.9 ms.")],
    """import math
def period_min(h_km, R=6371, mu=398600): a = R + h_km; return 2 * math.pi * math.sqrt(a ** 3 / mu) / 60
for h in (550, 1200, 35786): print(f"altitude {h:5d} km: period {period_min(h):7.1f} min")
print("CI half-width (n=100, s=20 ms):", round(1.96 * 20 / math.sqrt(100), 1), "ms")""")

add(8, r"""## Extra practice problems
Work these under exam conditions, then check the solutions in the exercise list below. Together with the formula sheet they cover the main calculation types from Weeks 1 to 7: store-and-forward delay, AIMD recovery time, fat-tree sizing, Mathis throughput, M/M/1 queues and handshake round trips.""",
    [("A 1000 B packet crosses 5 hops at 10 Mb/s (store-and-forward, ignore propagation). End-to-end transmission delay?", "5 × (8000/10⁷) = 4 ms."),
     ("A Reno flow halves cwnd from 120 to 60 after a loss. How many RTTs to recover?", "Additive increase of 1 per RTT: 60 RTTs."),
     ("A fat-tree uses 8-port switches. Hosts and switches?", "k³/4 = 128 hosts; 5k²/4 = 80 switches."),
     ("Which of TCP+TLS 1.3 and QUIC 1-RTT saves how much at RTT 80 ms?", "3 RTT vs 2 RTT: saves 80 ms.")])
add(16, r"""## Reproducibility checklist
Before submitting: state the topology, link rates, delays, buffer sizes and workload; fix and report random seeds; run at least 5 seeds and plot error bars; include the baselines the community expects (Reno or CUBIC, BBR, DCTCP, ECMP as appropriate); release code and configuration; and report negative results and failure cases.

## How to read a networking paper in 30 minutes
Read the abstract and conclusion, then the figures; decide the claim; read the evaluation setup and ask what is missing; only then read the design. Write down the baseline, the metric, one threat to validity and one follow-up experiment. This is also the template for your weekly paper critiques.

## Project menu
Choose one scope: (1) reproduce a figure from a SIGCOMM/NSDI paper in Mininet or ns-3; (2) compare Reno, CUBIC and BBR under varying buffer size and RTT; (3) measure QUIC versus TCP page-load time on emulated lossy links; (4) implement a count-min sketch heavy-hitter detector in P4 or Python on a packet trace; (5) analyse BGP table dynamics from RouteViews/RIPE RIS data. Each project needs a hypothesis, an experimental plan and a failure analysis.""",
    [("Why is reporting only the mean of 3 runs insufficient?", "Three samples give almost no estimate of variance; report ≥5 seeds with confidence intervals or percentile bands.")])
