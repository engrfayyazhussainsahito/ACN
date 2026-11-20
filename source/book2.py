# ---------------- Week 5 ----------------
LAB(5, "Buffer size versus utilisation and delay", "One Reno flow fills a bottleneck of 400-packet BDP. Sweep the buffer size B and measure link utilisation and the average queueing delay (queue ÷ capacity, capacity = 4000 packets/s).", """
def reno_buffer(bdp, B, steps=30000):
    W = bdp / 2; util = qsum = 0.0
    for _ in range(steps):
        q = min(B, max(0.0, W - bdp))            # standing queue when window exceeds the pipe
        util += min(1.0, W / bdp); qsum += q
        W += 1                                   # additive increase, once per RTT
        if W - bdp > B: W /= 2                   # buffer overflow -> loss -> halve
    return util / steps, qsum / steps
bdp, C = 400, 4000
print("buffer(xBDP)  utilisation  mean queue delay")
for f in (0.1, 0.25, 0.5, 1, 2, 4, 8):
    u, q = reno_buffer(bdp, f * bdp)
    print(f"{f:10.2f}  {u:11.1%}  {q / C * 1000:10.1f} ms")
""")
LAB(5, "Checking the Mathis model by simulation", "Simulate Reno with independent per-packet loss probability p (one window of W packets suffers a loss with probability 1−(1−p)^W) and compare the mean window with 1.22/√p.", """
import random, math
def mathis_sim(p, rounds=300000, seed=7):
    random.seed(seed); W = 10.0; tot = 0.0
    for _ in range(rounds):
        tot += W
        if random.random() < 1 - (1 - p) ** W: W = max(2.0, W / 2)
        else: W += 1
    return tot / rounds
print("p        simulated mean window   1.22/sqrt(p)")
for p in (1e-2, 1e-3, 1e-4): print(f"{p:6.0e}  {mathis_sim(p):12.1f} {1.22 / math.sqrt(p):18.1f}")
""")
deepen(5, r"""
## Basics: buffers, queues and the signal of congestion
A router buffer exists to absorb short bursts so that packets are not dropped when two arrive together. A buffer that is too small wastes capacity (the link idles after a drop). A buffer that is too large looks harmless but is not: if the sender keeps the buffer full, every packet waits in line behind a full buffer, so latency soars even though throughput is fine. This is **bufferbloat**.

### What does a full buffer cost?
Queueing delay = bytes queued ÷ link rate. A 256 KB buffer on a 10 Mb/s uplink holds 256,000 × 8 / 10⁷ ≈ 0.2 s of data: an interactive call or game sharing that uplink with a big upload sees 200 ms of extra delay. At a 1 Gb/s link the same buffer is only 2 ms, which is why the problem shows up on slow home links.

### Two kinds of congestion signal
- **Loss-based** (Reno, CUBIC): the only evidence of congestion is a dropped packet, which arrives only *after* the buffer is full, so these senders deliberately fill the buffer.
- **Delay-based / model-based** (Vegas, BBR): the sender watches RTT. If the RTT rises above its minimum, a queue is forming, so the sender can slow down before any loss occurs.
- **Explicit** (ECN): the router sets a mark in the IP header instead of dropping; the receiver echoes it and the sender reduces its rate. ECN gives early, loss-free feedback.

### The ideal operating point
Kleinrock (1979) showed that the best operating point maximises throughput divided by delay: keep exactly one BDP in flight. Below it the pipe is not full; above it the extra data only adds queueing delay. Loss-based TCP operates at the *right* edge (full buffer); good congestion control tries to operate at the knee.

### Active queue management in one paragraph
AQM drops or marks packets *before* the buffer is full, based on a measure of queue health, so the sender gets the signal early and queues stay short. Examples: RED (probability grows with average queue length), CoDel (drops when the minimum waiting time stays above 5 ms for 100 ms), and PIE.

### Self-check
Why does a single long upload ruin a video call on the same home link, even though the call uses little bandwidth? (The upload fills the queue; the call's packets wait in it.)
""", r"""
## Advanced: how BBR works
BBR (Cardwell et al. 2016) builds an explicit model of the path: **BtlBw**, the maximum delivery rate over the last ~10 round trips, and **RTprop**, the minimum RTT over the last 10 seconds. It paces packets at gain × BtlBw and caps inflight at cwnd_gain × BtlBw × RTprop. Delivery rate is measured per ACK as delivered bytes over the interval, with a rate-sample correction for application-limited periods. The gain cycle probes: 1.25× for one RTT (find extra bandwidth), 0.75× (drain the queue it created), then 1.0× for six RTTs. If RTprop has not been refreshed for 10 s, ProbeRTT drops inflight to 4 packets for 200 ms.

Properties: BBR's rate does not collapse on random loss, so it excels on lossy long-haul paths; it keeps queues short on deep buffers when it is the only flow. Weaknesses reported in measurements: v1 can take a disproportionate share against CUBIC in shallow buffers (it ignores loss) and cause persistently high retransmissions; flows with different RTprop estimates can be unfair because the larger inflight cap belongs to the longer-RTT flow; and a BBR flow can overestimate bandwidth on paths with ACK aggregation. BBRv2/v3 add loss and ECN response, a bound on inflight_hi and refined probing.

## Advanced: delay-based control and its theory
Vegas estimates the number of its own packets queued as diff = W·(1 − baseRTT/RTT) and keeps it between α and β (typically 1 to 3) by adjusting W by ±1 per RTT. Its equilibrium has each flow holding a fixed number of packets in the queue, so its share is not biased by RTT, but it loses to loss-based flows that fill the buffer. FAST TCP uses a smoother update and targets high BDP paths. Copa targets a rate of 1/(δ·d_queue) with an adaptive δ to coexist with buffer-fillers; PCC and PCC Vivace choose rates by online experiments on a utility function; Remy and later learning-based schemes (Aurora, Orca) search for control laws offline, and their open problem is robustness outside the training distribution.

## Advanced: AQM and ECN in detail
**RED** computes an exponentially weighted average queue and drops with probability rising linearly between min and max thresholds; it is notoriously hard to tune. **CoDel** (RFC 8289) tracks the minimum sojourn time over an interval (default 100 ms); if it stays above target (5 ms), CoDel drops a packet and shortens the next interval by 1/√count, so the drop rate rises until the standing queue vanishes. It is stateless with respect to link speed. **FQ-CoDel** (RFC 8290) hashes flows into queues served by deficit round robin with CoDel on each, giving sparse flows (DNS, VoIP) priority and isolating bulk flows; it is the default qdisc in many Linux distributions and a key part of fixing home-router bufferbloat. **PIE** (used in DOCSIS) computes the drop probability from the queue delay estimate.

ECN uses two IP bits: ECT(0)/ECT(1) mean 'ECN-capable', CE means 'congestion experienced'. Classic ECN reacts to a mark like a loss (halve). **L4S** (RFC 9330 to 9332) adds a second queue for 'scalable' congestion controls (DCTCP-like, TCP Prague, BBRv3) that mark early with a shallow ramp and react proportionally, delivering sub-millisecond queuing delay; a coupled AQM shares capacity fairly with classic traffic.

## Advanced: the Mathis model and its limits
The Mathis formula assumes a single loss per cycle, random independent loss and a long-lived Reno flow. It fails for: short flows (dominated by slow start), bursty or correlated loss, flows limited by the receiver window or the application, flows with timeouts (Padhye et al. model adds RTO terms: B ≈ MSS / (RTT√(2bp/3) + T₀·min(1, 3√(3bp/8))·p(1+32p²))), and paths where RTT varies with queue length. Use the formula for intuition about scaling (1/RTT, 1/√p), not for prediction to better than a factor of two.
""")

# ---------------- Week 6 ----------------
LAB(6, "Measuring head-of-line blocking", "10 streams of 30 packets are interleaved on one connection (window 20 packets per RTT, random loss p). A packet is *usable* by the application only when every earlier packet in its ordering domain has arrived: the whole connection for TCP/HTTP/2, only its own stream for QUIC. The head-of-line (HOL) delay is usable time minus arrival time, in RTTs.", """
import random
def hol_delays(p, mode, streams=10, size=30, W=20, seed=0):
    rnd = random.Random(seed)
    order = [(s, i) for i in range(size) for s in range(streams)]      # round-robin interleaving
    n = len(order); recv = [None] * n; pending = list(range(n)); r = 0
    while pending:
        r += 1
        send, pending = pending[:W], pending[W:]
        lost = [k for k in send if rnd.random() < p]
        for k in send:
            if k not in lost: recv[k] = r
        pending = lost + pending                                       # retransmit lost packets first
    run, out = {}, []
    for k, (s, i) in enumerate(order):
        dom = None if mode == "tcp" else s                             # ordering domain
        run[dom] = max(run.get(dom, 0), recv[k]); out.append(run[dom] - recv[k])
    return out
print("loss  mode   mean HOL delay   share of packets delayed   p95 delay (RTTs)")
for p in (0.01, 0.03, 0.05):
    for mode in ("tcp", "quic"):
        d = sum((hol_delays(p, mode, seed=s) for s in range(120)), []); d.sort()
        print(f"{p:4.0%}  {mode:5s} {sum(d)/len(d):12.3f} {sum(x > 0 for x in d)/len(d):18.1%} {d[int(0.95*len(d))]:20d}")
""")
LAB(6, "ACK ranges and the probe timeout", "QUIC acknowledges ranges of packet numbers, and its probe timeout (RFC 9002) is PTO = SRTT + max(4·RTTVAR, 1 ms) + max_ack_delay, doubling on each consecutive PTO.", """
def ack_ranges(pns):
    pns = sorted(set(pns)); out = []; s = prev = pns[0]
    for x in pns[1:]:
        if x != prev + 1: out.append((s, prev)); s = x
        prev = x
    out.append((s, prev)); return out[::-1]                  # largest range first, as in an ACK frame
print("received 1,2,3,5,6,9 ->", ack_ranges([1, 2, 3, 5, 6, 9]))
srtt, rttvar, mad = 0.100, 0.020, 0.025
pto = srtt + max(4 * rttvar, 0.001) + mad
print("PTO =", round(pto * 1000), "ms; after 3 consecutive PTOs:", [round(pto * 2**k * 1000) for k in range(3)], "ms")
print("amplification limit: server may send", 3 * 1200, "bytes in reply to a 1200-byte Initial")
""")
deepen(6, r"""
## Basics: connections, encryption and why transport changed
A **connection** is shared state at both ends (sequence numbers, windows, keys). Setting it up costs round trips; each round trip costs one RTT of waiting. On a 100 ms path, every extra handshake round trip is a visible delay.

### What TLS adds, in plain words
TLS makes a connection private and authenticated. The client and server agree on a shared secret key using public-key cryptography (a key exchange), the server proves its identity with a certificate signed by an authority the client trusts, and then both encrypt traffic with the shared key using fast symmetric ciphers. TLS 1.3 needs one round trip for all of this; TLS 1.2 needed two.

### The web protocol stack, version by version
| Protocol | Transport | Multiplexing | Main problem it fixed or left |
|---|---|---|---|
| HTTP/1.1 | TCP (+TLS) | none: browsers open ~6 connections per host | head-of-line blocking per connection |
| HTTP/2 | one TCP connection | streams in one connection | a lost TCP segment stalls all streams |
| HTTP/3 | QUIC over UDP | independent streams | per-stream recovery; faster setup |

### What is head-of-line blocking?
TCP presents one ordered byte stream. If segment 7 is lost, segments 8, 9 and 10 may have arrived, but the application cannot see them until 7 is retransmitted (at least one extra RTT). When 10 web objects share one TCP connection, the loss of one packet stalls all 10. The first lab quantifies this.

### Why QUIC runs over UDP
New transports cannot run directly over IP because firewalls and NATs drop unknown protocols. UDP passes everywhere, and QUIC implements reliability, congestion control and encryption in the application, so browsers and servers can update the transport as software. Cost: more CPU (no kernel offload, though this is improving) and some networks rate-limit UDP.

### Self-check
How many round trips before the first byte of an HTTPS request with TCP + TLS 1.3? (TCP handshake 1, TLS 1, request/response 1: 3.) Why is a stream the right unit for ordering?
""", r"""
## Advanced: the TLS 1.3 handshake and key schedule
ClientHello carries the supported cipher suites and one or more key shares (e.g., X25519). ServerHello selects a suite and returns its key share; from the resulting shared secret both sides derive handshake keys with HKDF. The rest of the server flight (EncryptedExtensions, Certificate, CertificateVerify, Finished) is already encrypted, hiding the certificate from passive observers. The client verifies the chain and signature, sends Finished, and both derive application traffic keys. Properties: forward secrecy for every connection (ephemeral Diffie-Hellman), removal of weak or legacy primitives, and one RTT cost. **Session resumption** uses a pre-shared key from a ticket; with **0-RTT**, the client sends early data in its first flight, encrypted under the resumption key. Early data is replayable (no fresh server randomness), so servers must restrict it to idempotent requests and may use single-use tickets or time windows.

## Advanced: QUIC in depth
**Packets and frames.** Long headers (Initial, Handshake, 0-RTT, Retry) carry version and connection IDs during setup; short headers carry only the destination connection ID. Payload is a sequence of frames (STREAM, ACK, CRYPTO, MAX_DATA, MAX_STREAM_DATA, NEW_CONNECTION_ID, PATH_CHALLENGE ...). Nearly all of it is authenticated and encrypted; packet numbers are protected by header protection.

**Streams and flow control.** Each stream is an independent ordered byte stream with its own credit (MAX_STREAM_DATA) plus a connection-level credit (MAX_DATA), so a slow stream cannot exhaust the connection's buffer. Unidirectional and bidirectional streams are created implicitly by use.

**Loss detection and congestion control (RFC 9002).** Packet numbers never repeat, which removes retransmission ambiguity and allows precise RTT samples including the peer's reported ack delay. A packet is declared lost if a later packet was acknowledged and it is more than 3 packet numbers older or older than 9/8 × max(SRTT, latest RTT). The PTO timer sends probe packets when no ACK arrives. The specification defines a NewReno-style controller; implementations commonly use CUBIC or BBR, pacing and HyStart++. Because congestion control is user-space code, deployments can run different algorithms per connection or per CDN and iterate quickly.

**Addresses, migration and amplification.** A connection is identified by connection IDs rather than the 4-tuple, so a client moving from Wi-Fi to LTE can continue after path validation (PATH_CHALLENGE/RESPONSE). Until the client's address is validated the server may send at most 3× the bytes received, defeating reflection abuse; Retry packets and address-validation tokens add stateless validation. Key update lets endpoints rotate keys without a new handshake. DPLPMTUD probes path MTU, and the spin bit allows passive RTT measurement by on-path observers who opt in.

**HTTP/3 and the ecosystem.** HTTP/3 maps requests to QUIC streams and uses QPACK, a header compression scheme designed to avoid head-of-line blocking between header blocks. Extensions include WebTransport, MASQUE (proxying UDP and IP over HTTP/3) and DATAGRAM frames for unreliable data. Operationally, QUIC hides transport signals from middleboxes, so operators lose some visibility and must rely on endpoint telemetry, qlog traces and the spin bit.

**Measured effects.** Reported deployments show the largest gains in tail latency, on lossy or high-RTT networks and for repeat visits via 0-RTT, and smaller gains at the median on good networks; user-space CPU cost is higher than kernel TCP, which is an active area of optimisation (UDP GSO, sendmmsg, kernel-bypass).

## Advanced: multipath transport
MPTCP (RFC 8684) lets one connection use several subflows (e.g., Wi-Fi and cellular), with a data-sequence mapping above the subflow sequence spaces. Coupled congestion control (LIA, OLIA, BALIA) ensures that a multipath flow is no more aggressive than a single TCP flow at any shared bottleneck, while shifting traffic towards less congested paths. Schedulers choose which subflow carries each segment; the min-RTT default can suffer from head-of-line blocking when RTTs differ greatly, motivating redundant and blocking-estimation schedulers. Multipath QUIC applies the same ideas with per-path packet number spaces. Open problems: energy cost of keeping radios active, middlebox interference with options, and fairness at shared bottlenecks.
""")

# ---------------- Week 7 ----------------
LAB(7, "ECMP hash collisions", "Hash n equal-rate flows uniformly onto 8 equal-cost links 2,000 times. The busiest link determines completion time, so compare the mean maximum load with the perfectly balanced load n/8.", """
import random, collections
def ecmp_max(flows, links, trials=2000, seed=1):
    random.seed(seed); tot = 0
    for _ in range(trials):
        c = collections.Counter(random.randrange(links) for _ in range(flows))
        tot += max(c.values())
    return tot / trials
print("flows  ideal  mean max load  overload factor")
for f in (8, 32, 128, 1024, 8192):
    m = ecmp_max(f, 8); print(f"{f:5d} {f/8:6.1f} {m:11.1f} {m/(f/8):12.2f}x")
""")
LAB(7, "TCP incast collapse", "N servers each return a 32 KB block through one 10 Gb/s port with a 128 KB buffer (about 85 packets). If the synchronised burst exceeds buffer + BDP, a loss occurs and the stalled flows wait for the minimum retransmission timeout.", """
def incast(N, rto, block=32_000, mss=1460, buf=85, rtt=100e-6, rate=10e9):
    pk = -(-block // mss) * N
    bdp_pk = rate * rtt / 8 / mss
    t = rtt + pk * mss * 8 / rate
    if pk > buf + bdp_pk: t += rto                      # overflow -> loss -> RTO stall
    return N * block * 8 / t / 1e9                      # goodput in Gb/s
print("servers  RTO=200ms  RTO=1ms")
for N in (2, 4, 6, 8, 16, 32, 64): print(f"{N:7d} {incast(N, 0.2):9.3f} {incast(N, 0.001):9.3f}  Gb/s")
print("tail at scale: P(at least one of 100 backends slow) with p99/p99.9 =", f"{1 - 0.99**100:.1%} / {1 - 0.999**100:.1%}")
""")
deepen(7, r"""
## Basics: what is special about a data center
A data center is thousands of servers in racks, connected by a network that is owned and designed by one organisation. Unlike the Internet, the operator controls both endpoints and switches, distances are short (RTTs of tens of microseconds), bandwidth is cheap relative to latency, and the dominant traffic is **east-west**, between servers, rather than north-south to the outside. Typical workloads: a web request that fans out to hundreds of back-end services, storage replication, MapReduce-style shuffles and machine-learning training.

### The tree and why it failed
Early designs were trees: servers connect to a top-of-rack (ToR) switch, ToRs to aggregation switches, those to a core. Each level is **oversubscribed**: if a ToR has 40 servers at 10 Gb/s (400 Gb/s down) but 40 Gb/s up, the oversubscription is 10:1, meaning inter-rack traffic gets one tenth of the rate rack-local traffic can have. The core links become the bottleneck and the core switches must be the biggest and most expensive.

### The Clos idea
In 1953 Charles Clos designed telephone switches from small crossbars arranged in stages so that many equal paths exist between any two ports. A **fat-tree** (this chapter's core topology) applies this to Ethernet: many small identical switches, every layer has the same total bandwidth, and a packet between two racks has many equal-cost paths. Capacity grows by adding switches rather than buying bigger ones. **Equal-cost multipath (ECMP)** hashes each flow onto one of the paths so packets of one flow stay in order.

### The tail at scale
When a request fans out to 100 back-ends, it finishes only when the slowest answers. If each back-end is slow 1% of the time, the chance that at least one is slow is 1 − 0.99¹⁰⁰ ≈ 63%. So rare per-server delays become common user-visible delays: data-center networks are judged by tail latency, not averages (Dean and Barroso, 2013). The second lab prints this number.

### Self-check
A leaf switch has 24 ports of 25 Gb/s down and 6 of 100 Gb/s up. Oversubscription? (600/600 = 1:1.) Why does a larger shuffle exercise the core more than a small RPC?
""", r"""
## Advanced: topology design space
Production fabrics evolved from three-tier trees to folded Clos (leaf-spine, pods of spines, super-spines). Radix limits drive layers: with k-port switches, a 2-tier leaf-spine supports k²/2 ports, 3-tier k³/4, and the cost in optics and cabling dominates. Alternatives for locality-heavy workloads or high radix: Dragonfly (all-to-all groups; adaptive routing needed), Jellyfish (random regular graphs with near-optimal capacity but harder cabling and routing via k-shortest paths), Xpander, and HyperX. Some operators have moved to optical circuit switches in the spine layer to reconfigure the topology to the demand, trading flexibility against reconfiguration latency; traffic engineering over such 'direct-connect' fabrics uses multi-path routing with non-shortest paths.

## Advanced: load balancing
ECMP's static hashing collides large flows (see the first lab: relative imbalance falls as flows increase, but the absolute busiest-link overload remains; few large flows make it severe). Approaches: **centralised placement** of elephant flows (Hedera); **per-flowlet** switching (CONGA, LetFlow) which re-hashes after an idle gap larger than the path delay difference, preserving order while spreading load, with congestion feedback in CONGA; **per-packet spraying** with end-host reorder tolerance (Presto uses fixed-size flowcells; NDP and Ultra Ethernet spray packets); **programmable data-plane** load balancing (HULA tracks best next hop per destination in switch registers); and **weighted ECMP** to handle asymmetry after failures. Failures matter: rehashing on a link failure can scramble all flows (consistent hashing in the data plane reduces disruption), and gray failures (partial loss) are hard to detect.

## Advanced: transport for the data center
Datacenter RTTs make the standard TCP minimum RTO (200 ms) 2000x too long, causing incast collapse; fine-grained timers (RTO_min ≈ 1 ms) fix part of it. **DCTCP** marks packets above a shallow threshold K (roughly BDP/7 in the original analysis) and reduces cwnd by α/2 with α the EWMA fraction of marked packets, giving near-zero loss and queues of a few packets. **pFabric** uses switches that schedule by remaining flow size; **PIAS** approximates shortest-job-first with a few priority queues without knowing sizes; **Homa** gives receivers control, using priorities and grants to run near-SRPT for short messages; **NDP** trims payloads at congested switches and has receivers pull packets at line rate; **HPCC** uses in-band telemetry for precise rate control; **Swift** and **TIMELY** use delay measurements. Reported benefits are order-of-magnitude reductions in tail latency for short messages in specific workloads. Choosing among them depends on whether hosts or switches can be modified.

## Advanced: buffer management and measurement
Merchant silicon has tens of megabytes of shared buffer for all ports; dynamic thresholds (Choudhury and Hahne) cap each queue at a multiple of the free buffer, balancing burst absorption and fairness. Microburst detection requires microsecond telemetry (INT, mirror-on-drop, sampled queue depth). Operators track **flow completion time** by size class, tail latency, loss and link utilisation at fine granularity, because 5-minute averages hide microbursts that cause incast.
""")

# ---------------- Week 9 ----------------
LAB(9, "A match-action switch", "A tiny interpreter for prioritised wildcard rules, the abstraction behind OpenFlow and P4 tables. Fields not mentioned in a rule are wildcards.", """
rules = [  # (priority, match dict, action)
    (300, {"proto": "tcp", "dport": 22}, "drop"),
    (200, {"dst": "10.1.2.0/24"}, "port3"),
    (100, {"dst": "10.0.0.0/8"}, "port1"),
    (0,   {}, "send_to_controller"),
]
def ip(a): x = [int(v) for v in a.split(".")]; return (x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3]
def in_prefix(addr, pre):
    base, l = pre.split("/"); l = int(l); m = (0xFFFFFFFF << (32 - l)) & 0xFFFFFFFF
    return ip(addr) & m == ip(base) & m
def matches(pkt, m):
    for k, v in m.items():
        if k == "dst":
            if not in_prefix(pkt["dst"], v): return False
        elif pkt.get(k) != v: return False
    return True
def forward(pkt):
    return next(a for pr, m, a in sorted(rules, key=lambda r: -r[0]) if matches(pkt, m))
for pkt in ({"dst": "10.1.2.7", "proto": "udp", "dport": 53}, {"dst": "10.9.9.9", "proto": "tcp", "dport": 80},
            {"dst": "10.1.2.7", "proto": "tcp", "dport": 22}, {"dst": "8.8.8.8", "proto": "udp", "dport": 53}):
    print(pkt, "->", forward(pkt))
""")
LAB(9, "Consistent updates: naive versus two-phase", "Four switches A, B, C, D. The old routes are A→B→C→D; the new ones are A→C→B→D. Updating the switches one at a time in every possible order exposes transient loops; version-tagging (two-phase) never does.", """
from itertools import permutations
old = {"A": "B", "B": "C", "C": "D"}
new = {"A": "C", "B": "D", "C": "B"}
def reaches(table, src, dst="D"):
    seen, n = set(), src
    while n != dst:
        if n in seen or n not in table: return False
        seen.add(n); n = table[n]
    return True
bad = 0
for order in permutations("ABC"):
    t = dict(old); ok = True
    for sw in order:
        t[sw] = new[sw]
        ok = ok and all(reaches(t, s) for s in "ABC")
    bad += not ok
    print("update order", "".join(order), "-> transient loop/blackhole:", not ok)
print(f"{bad} of 6 orders break connectivity; two-phase update: every packet follows a complete old or new path:",
      reaches(old, "A"), reaches(new, "A"))
""")
LAB(9, "Heavy-hitter detection with a count-min sketch", "Detect flows carrying at least 0.5% of 200,000 packets with a 4-row sketch of increasing width; report precision and recall against ground truth.", """
import random
from collections import Counter
random.seed(5); n_flows, N = 5000, 200000
stream = random.choices(range(n_flows), [1 / (i + 1) for i in range(n_flows)], k=N)
true = Counter(stream); thr = 0.005 * N
hh = {f for f, c in true.items() if c >= thr}
def detect(w, d=4):
    ab = [(random.randrange(1, 10**9), random.randrange(10**9)) for _ in range(d)]
    t = [[0] * w for _ in range(d)]
    for x in stream:
        for j, (a, b) in enumerate(ab): t[j][(a * x + b) % 1000003 % w] += 1
    est = lambda f: min(t[j][(a * f + b) % 1000003 % w] for j, (a, b) in enumerate(ab))
    found = {f for f in true if est(f) >= thr}
    tp = len(found & hh); return tp / max(1, len(found)), tp / len(hh)
print("true heavy hitters:", len(hh))
for w in (64, 256, 1024, 4096):
    pr, rc = detect(w); print(f"width {w:5d}: precision {pr:5.1%}  recall {rc:5.1%}")
""")
deepen(9, r"""
## Basics: three planes of a network
Every network device does three different jobs. The **data plane** moves packets: parse the header, look up a table, forward, at nanosecond timescales in hardware. The **control plane** computes the tables: routing protocols, spanning tree, ARP. The **management plane** configures devices and monitors them (CLI, SNMP, NETCONF). In traditional routers all three live in one closed box, and a new feature means waiting for the vendor.

### What 'software-defined' means
Software-defined networking (SDN) separates the control plane from the data plane: switches become simple, fast forwarders and a (logically) centralised **controller** computes global policy and installs rules via a southbound API (OpenFlow, P4Runtime, gNMI). Applications such as traffic engineering, access control and virtual networks sit on top via a northbound API. Benefits: a global view makes optimisation and verification feasible; network behaviour becomes software that can be tested and versioned.

### Match-action: one abstraction for everything
A switch table is a list of rules; each rule has a **match** (header fields, possibly with wildcards or prefixes), an **action** (forward to port, drop, rewrite a field, set a queue, send to the controller) and a priority. Routers, firewalls, NATs and load balancers all reduce to match-action tables. The first lab implements a tiny interpreter of this idea.

### Reactive versus proactive control
In **reactive** mode the first packet of a flow goes to the controller, which installs a rule: flexible but adds latency to flow setup and load to the controller. In **proactive** mode rules are pre-installed from policy, which scales and survives controller failure. Production systems are mostly proactive with centralised optimisation on a slower timescale.

### What P4 adds
OpenFlow fixed the set of header fields a switch could match. **P4** is a language to define the parser, the match-action tables and the deparser themselves, so a switch can support new protocols, tunnels or telemetry without new silicon. A P4 program has three parts: a **parser** (a state machine extracting headers from bytes), **match-action control blocks** (tables and actions), and a **deparser** (reassembling the packet).

```
// Sketch of a P4_16 ingress block (illustrative, not a complete program)
table ipv4_lpm {
    key = { hdr.ipv4.dstAddr : lpm; }
    actions = { forward(); drop(); }
    default_action = drop();
}
apply { if (hdr.ipv4.isValid()) ipv4_lpm.apply(); }
```

### Self-check
Which plane runs OSPF? Why is a proactive design more robust to controller failure? What would a firewall rule look like as a match-action entry?
""", r"""
## Advanced: switch architecture and its limits
A programmable pipeline (e.g. PISA: Protocol-Independent Switch Architecture) consists of a programmable parser, a fixed number of match-action stages (tens), each with limited SRAM and TCAM and a few ALUs, then a deparser, with a traffic manager (queues, schedulers) in the middle. Because every packet passes each stage in one clock, there are no loops: a program must fit in the stage count, and state is limited to **registers**, **counters** and **meters** with restricted read-modify-write per packet. This is why measurement uses compact data structures. An exact-match table in SRAM costs the key width, a ternary (TCAM) rule costs about twice the key width in bits plus higher power, and longest-prefix match uses algorithmic tries or TCAM; table capacity is typically hundreds of thousands to a few million entries.

## Advanced: telemetry and sketching
In-band network telemetry (INT) lets each hop append metadata (switch ID, queue depth, timestamps) to a probe or data packet, enabling per-hop latency decomposition; sinks aggregate and export. Sketches summarise streams in sublinear memory: count-min for frequency (never underestimates; additive error ≤ εN with probability 1−δ for w = ⌈e/ε⌉, d = ⌈ln 1/δ⌉), count sketch for unbiased estimates, Bloom filters for membership, HyperLogLog for distinct counts, and universal sketches for many metrics at once. Sketches are mergeable across switches (element-wise addition when hash functions match) and across time. The third lab shows a precision-recall trade-off: narrow sketches over-estimate many mice and produce false heavy hitters; wide ones recover both.

## Advanced: network update and verification
Consistent updates (Reitblatt et al. 2012) give per-packet consistency by version-tagging; later work makes updates faster using ordering (dependency graphs), incremental updates, and time-based updates with synchronised clocks. **Verification** checks properties of the network: Header Space Analysis represents sets of packets as wildcard bit vectors and rules as transfer functions; VeriFlow and NetPlumber check each update incrementally in microseconds to milliseconds; Batfish builds a model of router configurations to answer reachability and policy questions before deployment; Minesweeper and later tools encode control-plane behaviour in SMT. P4 verification (p4v, Vera) checks the programs themselves. Practical lesson: most outages come from configuration, so test and verify the network the way software is tested.

## Advanced: network functions and in-network computing
NFV runs firewalls, NATs, load balancers (Maglev, Katran), DPI and proxies as software on commodity hardware. High-performance packet I/O uses DPDK (user-space polling), eBPF/XDP (programs in the kernel receive path, handling tens of millions of packets per second per few cores) and SmartNICs/DPUs (offload flow tables). Programmable switches have been used for in-network key-value caching (NetCache, SOSP 2017), aggregation for ML training (SwitchML, NSDI 2021), consensus acceleration and load balancing, trading severe memory limits for line-rate speed. Operating SDN at scale also needs management interfaces: model-driven configuration (YANG with NETCONF/gNMI), streaming telemetry, intent-based abstractions, and controllers such as ONOS or OpenDaylight with replicated state for fault tolerance.
""")
