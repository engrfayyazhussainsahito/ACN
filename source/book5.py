# Expansion layer: deepens Weeks 6, 9 and 14 further. Executed inside build.py after book4.py.
import random as _r

def extend(n, prime, adv, ex=(), obj=(), rd=()):
    w = BYN[n]; tok = "\n\n[[lab:%d]]" % n
    w["body"] = prime.strip() + "\n\n" + w["body"]                      # new basics come first
    w["body"] = w["body"].replace(tok, "", 1)
    mk = "\n\n## Programming assignment"
    if mk in w["body"]: w["body"] = w["body"].replace(mk, "\n\n" + adv.strip() + tok + mk, 1)   # advanced material, then labs
    else: w["body"] = w["body"] + "\n\n" + adv.strip() + tok
    w["ex"] = w["ex"] + list(ex); w["obj"] = w["obj"] + list(obj); w["rd"] = w["rd"] + list(rd)

# ---------- extra figures ----------
def _hol_mean(p, mode, seeds=40, streams=10, size=30, W=20):
    tot = cnt = 0
    for sd in range(seeds):
        rnd = _r.Random(sd); order = [(s, i) for i in range(size) for s in range(streams)]; n_ = len(order)
        recv = [None] * n_; pending = list(range(n_)); r_ = 0
        while pending:
            r_ += 1; send, pending = pending[:W], pending[W:]
            lost = [k for k in send if rnd.random() < p]
            for k in send:
                if k not in lost: recv[k] = r_
            pending = lost + pending
        run = {}
        for k, (s, i) in enumerate(order):
            dom = None if mode == "tcp" else s; run[dom] = max(run.get(dom, 0), recv[k]); tot += run[dom] - recv[k]; cnt += 1
    return tot / cnt
_ps = [0, 0.5, 1, 2, 3, 4, 5]
plot("hol2", "Mean head-of-line delay (in RTTs) of a packet when 10 streams share one connection, versus random loss rate. One ordered byte stream (TCP/HTTP/2) delays far more packets than independent QUIC streams.",
     [("TCP / HTTP/2", _ps, [_hol_mean(p / 100, "tcp") for p in _ps]), ("QUIC streams", _ps, [_hol_mean(p / 100, "quic") for p in _ps])], "random loss rate (%)", "mean HOL delay (RTTs)")
_bs = list(range(4, 25))
plot("bloomfp", "Bloom-filter false-positive rate versus bits per item: optimal k = (m/n)·ln 2 against a fixed k = 3. Each extra bit per item cuts the optimal rate by about 38%, so ~10 bits per item gives about 1%.",
     [("optimal k", _bs, [0.5 ** (b * math.log(2)) for b in _bs]), ("k = 3", _bs, [(1 - math.exp(-3 / b)) ** 3 for b in _bs])], "bits per item (m/n)", "false-positive rate", False, True)
def _ring(N, S, B, a): return 2 * (N - 1) / N * S / B + 2 * (N - 1) * a
_Ms = [2 ** i for i in range(1, 10)]
plot("hier", "10 GB all-reduce: one flat ring over the network versus a hierarchical algorithm (8 GPUs per server, 300 GB/s inside, 50 GB/s per GPU across servers). The hierarchical version moves 1/8 of the data over the slow links.",
     [("flat ring", [8 * m for m in _Ms], [_ring(8 * m, 10e9, 50e9, 5e-6) * 1e3 for m in _Ms]),
      ("hierarchical", [8 * m for m in _Ms], [(2 * 7 / 8 * 10e9 / 300e9 + _ring(m, 10e9 / 8, 50e9, 5e-6)) * 1e3 for m in _Ms])], "GPUs", "time (ms)", True, False)

# ---------- extra demos (patched into demos.js) ----------
_dj = OUT + "/assets/demos.js"; _js = open(_dj, encoding="utf-8").read()
_new = r"""D.bloom=function(e){mk(e,[['n','items n (thousands)',1,10000,1,1000],['b','bits per item m/n',4,32,1,10],['k','hash functions k',1,16,1,7]],function(v){var n=v.n*1000,m=n*v.b,p=Math.pow(1-Math.exp(-v.k/v.b),v.k),ko=v.b*Math.LN2;return tb([['memory',f(m/8/1e6,2)+' MB'],['false-positive rate',f(100*p,3)+' %'],['optimal k = (m/n)ln2',f(ko,1)],['FPR at optimal k',f(100*Math.pow(0.5,ko),3)+' %']])})};
D.quic=function(e){mk(e,[['rtt','RTT (ms)',10,300,10,80],['lp','random loss (%)',0,5,0.1,1],['n','packets in flight',10,200,10,100]],function(v){var p=v.lp/100;return tb([['TCP + TLS 1.2: first byte',4*v.rtt+' ms'],['TCP + TLS 1.3',3*v.rtt+' ms'],['QUIC 1-RTT',2*v.rtt+' ms'],['QUIC 0-RTT (resumption)',v.rtt+' ms'],['P(at least one loss in flight)',f(100*(1-Math.pow(1-p,v.n)),1)+' %'],['streams stalled by one loss (10 streams)','TCP: 10, QUIC: 1']])})};
D.train=function(e){mk(e,[['P','parameters (billions)',1,1000,1,70],['by','bytes per gradient',2,4,2,2],['d','log2 of data-parallel GPUs',1,10,1,6],['bw','network GB/s per GPU',10,100,10,50],['c','compute per step (s)',0.5,30,0.5,10]],function(v){var d=Math.pow(2,v.d),comm=2*(d-1)/d*v.P*1e9*v.by/(v.bw*1e9);return tb([['data-parallel GPUs',d],['gradient size',f(v.P*v.by,0)+' GB'],['ring all-reduce time',f(comm,2)+' s'],['efficiency, no overlap',f(100*v.c/(v.c+comm),1)+' %'],['efficiency, perfect overlap',f(100*Math.min(1,v.c/comm),1)+' %']])})};
"""
_js = _js.replace("document.querySelectorAll('.demo')", _new + "document.querySelectorAll('.demo')", 1)
open(_dj, "w", encoding="utf-8").write(_js)

# =====================================================================
# WEEK 6
# =====================================================================
LAB(6, "QUIC variable-length integers and stream IDs", "QUIC encodes integers in 1, 2, 4 or 8 bytes; the two top bits of the first byte give the length. The sample values are the examples in RFC 9000 Appendix A. Stream IDs carry the initiator and direction in their two low bits.", """
def enc_varint(v):
    for n, tag in ((1, 0), (2, 1), (4, 2), (8, 3)):
        if v < (1 << (8 * n - 2)): return ((tag << (8 * n - 2)) | v).to_bytes(n, "big")
    raise ValueError("too large")
def dec_varint(b):
    n = 1 << (b[0] >> 6); return int.from_bytes(b[:n], "big") & ((1 << (8 * n - 2)) - 1), n
tests = [("c2197c5eff14e88c", 151288809941952652), ("9d7f3e7d", 494878333), ("7bbd", 15293), ("25", 37)]
for hx, expect in tests:
    raw = bytes.fromhex(hx); v, n = dec_varint(raw)
    print(f"{hx:>18s} -> {v:>20d} ({n} bytes)", "OK" if v == expect and enc_varint(v) == raw else "MISMATCH")
kinds = {0: "client-initiated bidirectional", 1: "server-initiated bidirectional", 2: "client-initiated unidirectional", 3: "server-initiated unidirectional"}
for sid in (0, 1, 2, 3, 4, 6, 7, 100): print("stream", sid, "->", kinds[sid & 3], "| index", sid >> 2)
""")
LAB(6, "The QUIC RTT estimator, probe timeout and loss threshold", "RFC 9002: the first sample sets smoothed_rtt = sample and rttvar = sample/2; later samples subtract the peer's ack delay when that keeps the result above the minimum RTT. PTO = smoothed_rtt + max(4·rttvar, 1 ms) + max_ack_delay and doubles on each consecutive PTO. A packet is declared lost when older than 9/8·max(smoothed, latest) RTT.", """
class Rtt:
    def __init__(self): self.srtt = None; self.var = None; self.min = float("inf")
    def sample(self, latest, ack_delay=0.0):
        self.min = min(self.min, latest)
        adj = latest - ack_delay if latest >= self.min + ack_delay else latest
        if self.srtt is None: self.srtt, self.var = latest, latest / 2
        else:
            self.var = 0.75 * self.var + 0.25 * abs(self.srtt - adj)
            self.srtt = 0.875 * self.srtt + 0.125 * adj
    def pto(self, mad=25.0, backoff=0): return (self.srtt + max(4 * self.var, 1.0) + mad) * 2 ** backoff
r = Rtt()
print("sample(ms) ack_delay  srtt    rttvar   PTO   loss-time threshold")
for latest, ad in ((120, 0), (100, 10), (110, 5), (300, 0), (105, 5)):
    r.sample(latest, ad)
    print(f"{latest:9d} {ad:9d} {r.srtt:7.1f} {r.var:8.1f} {r.pto():7.1f} {9/8*max(r.srtt, latest):10.1f}")
print("PTO backoff after 3 timeouts:", [round(r.pto(backoff=k)) for k in range(4)], "ms")
""")
LAB(6, "HKDF (RFC 5869) and a toy Diffie-Hellman exchange", "TLS 1.3 and QUIC derive every key with HKDF-Extract and HKDF-Expand. This lab checks our implementation against RFC 5869 test case 1, derives labelled keys the way the TLS 1.3 key schedule does (with simplified labels), and runs Diffie-Hellman with tiny numbers.", """
import hmac, hashlib
def extract(salt, ikm): return hmac.new(salt, ikm, hashlib.sha256).digest()
def expand(prk, info, L):
    out, t, i = b"", b"", 1
    while len(out) < L:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest(); out += t; i += 1
    return out[:L]
prk = extract(bytes(range(13)), bytes([0x0b]) * 22)
okm = expand(prk, bytes(range(0xf0, 0xfa)), 42)
print("RFC 5869 test case 1, PRK matches:", prk.hex() == "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5")
print("RFC 5869 test case 1, OKM matches:", okm.hex() == "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865")
p, g, a, b = 23, 5, 6, 15
A, B = pow(g, a, p), pow(g, b, p)
print(f"toy DH p={p} g={g}: A={A} B={B}; both sides compute", pow(B, a, p), "and", pow(A, b, p))
secret = pow(B, a, p).to_bytes(1, "big")
hs = extract(b"\\x00" * 32, secret)                          # handshake secret
ck, sk = expand(hs, b"tls13 c hs traffic", 16), expand(hs, b"tls13 s hs traffic", 16)
print("client key:", ck.hex(), "\\nserver key:", sk.hex(), "\\ndifferent labels give independent keys:", ck != sk)
""")
LAB(6, "Window-limited throughput and the BDP", "A sender may have at most one window per round trip in flight, so throughput = window / RTT (until the link rate). Tabulate Mb/s for typical receive windows and paths.", """
print("RTT      64 KB window   1 MB window   16 MB window   BDP of 1 Gb/s path")
for rtt in (0.005, 0.020, 0.100, 0.300):
    row = [min(1000.0, w * 8 / rtt / 1e6) for w in (64e3, 1e6, 16e6)]
    print(f"{rtt*1000:4.0f} ms " + "".join(f"{x:13.1f} Mb/s" for x in row) + f"   {1e9*rtt/8/1e6:8.2f} MB")
""")
extend(6, r"""
## Basics: the transport mechanisms underneath, from first principles
This section builds the vocabulary needed for the rest of the chapter, assuming only that you know what a packet is.

### Reliability from scratch
Suppose a sender wants to deliver ten packets over a network that may lose, duplicate or reorder them. The sender numbers each packet; the receiver replies with acknowledgments (ACKs) saying what has arrived; the sender keeps a copy of anything unacknowledged and **retransmits** it after a timeout. *Stop-and-wait* sends one packet per round trip: on a 100 ms path that is ten packets per second, no matter how fast the link. To use the pipe, the sender needs a **window**: many packets in flight at once. TCP uses a *cumulative* ACK ('I have everything up to byte N'), plus optional *selective* ACKs (SACK) naming extra ranges. QUIC uses ranges from the start.

### Timers: what to wait for
Wait too short and you retransmit packets that were merely slow (wasting capacity and shrinking the window); wait too long and a loss stalls the connection. So the timeout must track the path's round-trip time **and its variation**. Both TCP and QUIC keep a smoothed RTT (a moving average with weight 1/8 on each new sample) and an RTT variance (weight 1/4) and set the timeout to roughly smoothed RTT plus four times the variance. Lab 6.4 implements QUIC's version.

### Window-limited throughput
The sender may have at most one window of data outstanding, so throughput ≤ window / RTT. A default 64 KB window over a 100 ms path caps throughput near 5 Mb/s; filling a 1 Gb/s, 100 ms path needs a window of 12.5 MB, the **bandwidth-delay product**. This is why receive buffers must be tuned (Lab 6.6 prints the table) and why a lost window-sized burst is expensive.

### Cryptography without the mathematics
You need three facts. (1) A **symmetric cipher** encrypts bulk data quickly with a shared secret key. (2) A **key exchange** such as Diffie-Hellman lets two parties who have never met create a shared secret by exchanging public values that an eavesdropper cannot turn into the secret; Lab 6.5 runs it with tiny numbers (p = 23, g = 5 gives shared secret 2). (3) A **signature** lets the server prove it owns a public key that a certificate authority has vouched for. **HKDF** is the standard tool that stretches a shared secret into many independent keys (one per direction and purpose), distinguished by textual labels.

### A packet on the wire
A QUIC packet is a UDP datagram. The first byte's top bit says long header (handshake) or short header (data). A short header carries just the flags, the destination **connection ID** (so the receiver can find the connection even if the sender's IP address or port changed) and a packet number; the rest is encrypted payload made of **frames**. QUIC's integers use a variable-length encoding in which the two top bits of the first byte select a 1, 2, 4 or 8 byte representation, so small values cost one byte; Lab 6.3 decodes the examples from the specification and shows how a stream ID's two low bits encode who started the stream and whether it is one-way.

### Self-check
How long does stop-and-wait take to send 100 packets over a 50 ms RTT path? (100 × 50 ms = 5 s.) Why must the timeout depend on RTT variance as well as the mean? Why can QUIC survive a change of the client's IP address when TCP cannot?
""", r"""
## Advanced: reading a QUIC connection end to end
A typical first connection proceeds as follows. The client sends an **Initial** packet (padded to at least 1,200 bytes to limit amplification) carrying a CRYPTO frame with the TLS ClientHello; Initial packets are protected with keys derived from the destination connection ID and a version-specific salt, so anyone on the path can read them (this is intentional: it lets load balancers route by SNI/connection ID). The server replies with an Initial (ServerHello) and Handshake packets (the encrypted remainder of its flight). The client completes the handshake and may now send 1-RTT data. The server confirms the handshake and sends HANDSHAKE_DONE; both discard Initial and Handshake keys. Application data then flows in short-header packets. Debugging uses a TLS key log (`SSLKEYLOGFILE`) so Wireshark can decrypt, or **qlog** files from the endpoints visualised with qvis, which show packets sent, lost, acknowledged and congestion-window evolution.

## Advanced: scheduling streams and priorities
Streams share one congestion window, so an endpoint must decide which stream's data to send next. Simple round-robin gives every stream an equal share (good fairness, but delays a small critical resource, e.g. a stylesheet, behind large images). Browsers therefore declare priorities: HTTP/2's dependency tree proved complex and inconsistently implemented; HTTP/3 uses **Extensible Priorities** (RFC 9218), a urgency level from 0 to 7 plus an *incremental* flag that says whether partial data is useful (progressive images) or the object is only useful when whole (scripts). Servers should send higher urgency first and share bandwidth among equal urgency flows; implementation quality varies, which is a major source of page-load differences between servers.

## Advanced: flow control and receiver tuning
Per-stream and per-connection credit limit how much a sender may transmit. A receiver that advertises too little throttles the sender to window/RTT (see the BDP lab); one that advertises too much risks memory exhaustion (a denial-of-service lever). Implementations auto-tune: they grow the advertised window when the sender repeatedly fills it, typically by doubling each time the application drains the buffer within about two RTTs. Because limits are per stream, a stalled consumer on one stream cannot starve others unless the connection limit is exhausted, so servers cap per-stream and total buffered data.

## Advanced: congestion control and pacing inside QUIC
QUIC implementations pace packets: sending a whole window back to back creates microbursts that overflow shallow buffers. A typical pacer spreads the congestion window over the smoothed RTT, with rate = N · cwnd / smoothed_rtt (N ≈ 1.25 allows the window to grow during slow start). Because the transport lives in user space, operators run CUBIC, BBR or custom controllers per connection and deploy updates in days. Hybrid slow start (HyStart++) leaves slow start when RTT begins to rise, avoiding massive overshoot. Loss detection is precise because packet numbers are never reused; the loss-time threshold (9/8 of the larger of smoothed and latest RTT, printed in Lab 6.4) lets QUIC recover from reordering without spurious retransmission, and **persistent congestion** (a long run of lost packets spanning multiple PTOs) collapses the window to its minimum.

## Advanced: CPU cost and engineering
Kernel TCP benefits from decades of offloads: segmentation offload, checksum offload and zero-copy sends. User-space QUIC starts at a disadvantage: per-packet system calls and encryption in software. Mitigations: **UDP generic segmentation offload** (send one large buffer split by the NIC or kernel into many datagrams), `sendmmsg`/`recvmmsg` batching, GRO on receive, hardware AES offload, io_uring, and in extreme cases kernel-bypass stacks. Server operators report significantly higher CPU for QUIC than for TCP in early deployments, narrowing as these optimisations land, so HTTP/3 rollouts need capacity planning.

## Advanced: deployment, discovery and failure modes
Clients usually do not know a server speaks HTTP/3. Discovery uses an **Alt-Svc** HTTP header (the server announces that h3 is available) or the DNS HTTPS/SVCB record (which also carries ALPN and IP hints, allowing first-visit QUIC). Because some networks block or throttle UDP, clients race QUIC against TCP ('happy eyeballs') and fall back when QUIC fails, so measured benefits depend on the mix of networks. Middlebox behaviour matters: NAT bindings for UDP expire quickly (often 30 s), so endpoints send keep-alives; some enterprise firewalls drop unknown UDP; and carrier-grade NATs may rebind ports, which connection IDs and path validation handle. Measurement studies (Kakhki et al. 2017; Yu et al. 2021) found that gains vary with implementation quality, network conditions and workload, and that mis-tuned QUIC stacks can underperform TCP, so evaluate with the same congestion controller on both.

## Advanced: relationship to other transports
| Feature | TCP + TLS | QUIC | SCTP | MPTCP |
|---|---|---|---|---|
| Streams | one byte stream | many | many (message-oriented) | one per connection |
| Encryption | separate layer | built in | optional (DTLS) | separate layer |
| Handshake RTTs (with TLS 1.3) | 2 + request | 1 (0 on resume) | 2 | like TCP |
| Migration across addresses | no | yes (connection IDs) | multi-homing | yes (subflows) |
| Evolvability | ossified | user space | rare | limited by middleboxes |
| Header visible to middleboxes | yes | mostly no | yes | yes |

## Advanced: what to measure
Compare protocols on **page load time**, time to first byte, speed index, rebuffering for video, and especially the 95th and 99th percentiles; control for the congestion controller, initial window, server location and TLS resumption; run repeated paired trials in time; and always report the number of requests and the network emulation parameters. The head-of-line figure shows what to expect in the idealised case: the penalty of one ordered stream grows with loss, while independent streams pay only for the stream that lost a packet.

[[fig:hol2]]

[[demo:quic]]
""", ex=[
    ("Decode the QUIC variable-length integer 0x7bbd and encode 37.", "0x7bbd: top bits 01 → 2 bytes; clear them: 0x3bbd = 15,293. 37 < 64 → one byte 0x25."),
    ("Stream ID 6, 5 and 4: who initiated them and are they bidirectional?", "6 = ...10 → client-initiated unidirectional; 5 = ...01 → server-initiated bidirectional; 4 = ...00 → client-initiated bidirectional."),
    ("QUIC RTT estimator: first sample 120 ms, second sample 100 ms with ack delay 10 ms. smoothed RTT, rttvar and PTO (max_ack_delay 25 ms)?", "First: srtt 120, var 60. Second: min = 100, 100 < 100 + 10 so no ack-delay adjustment; var = ¾·60 + ¼·|120−100| = 50; srtt = ⅞·120 + ⅛·100 = 117.5. PTO = 117.5 + 4·50 + 25 = 342.5 ms."),
    ("Why does the receive window cap a 100 ms path at about 5 Mb/s when it is 64 KB?", "Throughput ≤ window/RTT = 65,536 × 8 / 0.1 s ≈ 5.2 Mb/s."),
    ("At RTT 80 ms how much faster is the first byte with QUIC 1-RTT than with TCP+TLS 1.2?", "TCP+TLS 1.2 needs 4 RTT = 320 ms; QUIC 1-RTT needs 2 RTT = 160 ms; it saves 160 ms."),
    ("Why must the 'Initial' packet be padded to 1,200 bytes?", "To bound amplification: the server may answer with at most 3× the bytes received before validating the client, so a larger client packet allows a useful server flight and a spoofed small request cannot cause large reflection.")],
    obj=["Implement QUIC's variable-length integers, RTT estimator and probe timeout from the specification.", "Explain the HKDF-based key derivation and the discovery, fallback and engineering issues of deploying HTTP/3."],
    rd=["RFC 9001: Using TLS to secure QUIC.", "RFC 9002: QUIC loss detection and congestion control.", "RFC 9114 (HTTP/3), RFC 9204 (QPACK) and RFC 9218 (Extensible priorities).", "Kakhki et al. (2017) Taking a long look at QUIC. IMC.", "Yu et al. (2021) Dissecting performance of production QUIC. The Web Conference."])

# =====================================================================
# WEEK 9
# =====================================================================
LAB(9, "From bytes to headers: parsing IPv4 and updating the checksum", "A programmable parser extracts headers from raw bytes; a data-plane step decrements the TTL and fixes the checksum. The sample header is the standard Wikipedia example (checksum 0xb861). The incremental update is RFC 1624: HC' = ~(~HC + ~m + m').", """
import struct
def csum(data):
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while s >> 16: s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF
hdr = bytes.fromhex("450000730000400040110000c0a80001c0a800c7")      # checksum field zeroed
c = csum(hdr); print("computed header checksum:", hex(c), "(known answer 0xb861)")
pkt = bytearray(hdr); pkt[10:12] = c.to_bytes(2, "big")
print("checksum over the finished header (must be 0):", csum(bytes(pkt)))
def parse_ipv4(b):
    v_ihl, tos, tot, ident, ff, ttl, proto, ck, src, dst = struct.unpack("!BBHHHBBH4s4s", b[:20])
    return dict(version=v_ihl >> 4, ihl=v_ihl & 15, total_len=tot, ttl=ttl, proto=proto, src=".".join(map(str, src)), dst=".".join(map(str, dst)))
print(parse_ipv4(bytes(pkt)))
old = (pkt[8] << 8) | pkt[9]; pkt[8] -= 1; new = (pkt[8] << 8) | pkt[9]       # forward: TTL - 1
hc = int.from_bytes(pkt[10:12], "big")
s = (~hc & 0xFFFF) + (~old & 0xFFFF) + new
while s >> 16: s = (s & 0xFFFF) + (s >> 16)
inc = (~s) & 0xFFFF
z = bytearray(pkt); z[10:12] = b"\\x00\\x00"
print("incremental checksum:", hex(inc), "| full recomputation:", hex(csum(bytes(z))), "| equal:", inc == csum(bytes(z)))
""")
LAB(9, "Bloom filters: measured versus theoretical false-positive rate", "A Bloom filter of m bits and k hash functions holds n items with false-positive rate (1 − e^(−kn/m))^k. Insert 20,000 items, then query 50,000 items that were never inserted.", """
import hashlib, math
class Bloom:
    def __init__(self, m, k): self.m, self.k, self.bits = m, k, bytearray(m)
    def _idx(self, x):
        h = hashlib.sha256(str(x).encode()).digest()
        a, b = int.from_bytes(h[:8], "big"), int.from_bytes(h[8:16], "big") | 1
        return [(a + i * b) % self.m for i in range(self.k)]            # double hashing
    def add(self, x):
        for i in self._idx(x): self.bits[i] = 1
    def __contains__(self, x): return all(self.bits[i] for i in self._idx(x))
n = 20000
print("bits/item  k   measured FPR   theory")
for b in (4, 8, 12, 16):
    m = n * b; k = max(1, round(b * math.log(2))); f = Bloom(m, k)
    for i in range(n): f.add(i)
    fp = sum((n + j) in f for j in range(50000)) / 50000
    print(f"{b:9d} {k:3d} {fp:12.4%} {(1 - math.exp(-k * n / m)) ** k:10.4%}")
""")
LAB(9, "A miniature header-space analysis: finding a forwarding loop", "Packet headers are 8-bit strings over {0,1,x}. Each switch has ordered match rules. We propagate the set of headers that match each rule along the network and flag paths that revisit a switch. This is the core idea of Header Space Analysis.", """
def inter(a, b):
    out = []
    for x, y in zip(a, b):
        if x == "x": out.append(y)
        elif y == "x" or x == y: out.append(x)
        else: return None
    return "".join(out)
net = {"A": [("1xxxxxxx", "B"), ("0xxxxxxx", "C")],
       "B": [("11xxxxxx", "D"), ("10xxxxxx", "A")],        # bug: headers 10xxxxxx bounce back to A
       "C": [("xxxxxxxx", "D")],
       "D": [("xxxxxxxx", "deliver")]}
def explore(node, hs, path, found):
    if node == "deliver": found.append(("delivered", path, hs)); return
    for match, nxt in net[node]:
        h = inter(hs, match)
        if h is None: continue
        if nxt in path: found.append(("LOOP", path + [nxt], h)); continue
        explore(nxt, h, path + [nxt], found)
found = []; explore("A", "xxxxxxxx", ["A"], found)
for kind, path, hs in found: print(f"{kind:9s} {'->'.join(path):16s} headers {hs}")
""")
LAB(9, "Reactive versus proactive rule installation", "200 hosts generate 20,000 random flows. A reactive controller installs an exact-match (source, destination) rule for each new pair via Packet-In and Flow-Mod; a proactive controller pre-installs one rule per destination.", """
import random
random.seed(11); H, F = 200, 20000
seen = set(); packet_in = 0
for _ in range(F):
    s, d = random.randrange(H), random.randrange(H)
    if s != d and (s, d) not in seen: seen.add((s, d)); packet_in += 1
print(f"reactive exact-match: {packet_in} Packet-In/Flow-Mod pairs, {len(seen)} table entries")
print(f"proactive per-destination: 0 Packet-Ins, {H} entries ({len(seen) / H:.0f}x smaller table)")
print("all-pairs exact entries for 2,000 hosts:", 2000 * 1999)
print("control-channel load at 10,000 new flows/s with 128-byte Packet-Ins:", 10000 * 128 * 8 / 1e6, "Mb/s")
""")
extend(9, r"""
## Basics: OpenFlow, concretely
Before P4, OpenFlow defined a standard way for a controller to program a switch. Knowing its objects makes every later idea (P4 tables, verification, telemetry) easier.

### The cast of messages
| Message | Direction | Meaning |
|---|---|---|
| Hello / Features | both | negotiate version; the switch reports ports and tables |
| Packet-In | switch → controller | 'I have no rule for this packet' (or a rule says send to controller) |
| Flow-Mod | controller → switch | add, modify or delete a rule |
| Packet-Out | controller → switch | send this specific packet out of a port |
| Port-Status | switch → controller | a link went up or down |
| Barrier | controller → switch | 'tell me when everything before this is installed' |
| Stats request/reply | both | read counters per flow, port or table |

### Anatomy of a flow entry
A rule has a **match** (ingress port, Ethernet and IP fields, ports, VLAN, ...), a **priority** (the highest matching rule wins), **counters** (packets and bytes), **instructions or actions** (output, drop, rewrite, push a tag, go to the next table, apply a group or meter), **timeouts** (idle and hard: soft state again) and a **cookie** the controller uses to identify its rules. Since OpenFlow 1.1 a packet passes through a **pipeline of tables**; each table's instructions may send it to a later table, which avoids the cross-product of rules that a single table would need (e.g. VLAN × ACL × routing). **Group tables** implement multipath ('select' buckets, the hardware form of ECMP) and fast failover (a group tries its first live bucket). **Meters** rate-limit.

### A learning switch as an SDN application
The classic first application: when a Packet-In arrives, record that the source MAC lives on the ingress port; if the destination MAC is known, install a rule and forward, otherwise flood. The controller's program is ten lines; the cost is the control-channel round trip for the first packet of every flow and a table entry for every active pair. Lab 9.7 counts both, and shows why production designs install rules proactively and aggregate them (per destination or per prefix).

### Why sketches and filters appear everywhere in data planes
A switch has tens of megabytes of fast memory and a nanosecond-scale budget per packet, so it cannot keep an exact record for millions of flows or addresses. A **Bloom filter** answers 'have I seen this item?' using a few bits per item at the price of occasional false positives and no false negatives. It is the simplest example of the trade that sketches make: *exchange exactness for small, fixed memory*. Lab 9.5 verifies the false-positive formula; the demo below lets you size one.

### Self-check
What is the difference between Packet-In and Packet-Out? Why does a pipeline of tables need fewer rules than one big table? Can a Bloom filter produce a false negative? (No.)

[[demo:bloom]]
""", r"""
## Advanced: a complete P4 program, line by line
The listing below follows the structure of the standard P4_16 tutorial programs for the v1model architecture (BMv2). It is shown for study and was not compiled in this build.

```
#include <core.p4>
#include <v1model.p4>
const bit<16> TYPE_IPV4 = 0x800;
typedef bit<9>  egressSpec_t;  typedef bit<48> macAddr_t;  typedef bit<32> ip4Addr_t;
header ethernet_t { macAddr_t dstAddr; macAddr_t srcAddr; bit<16> etherType; }
header ipv4_t {
    bit<4> version; bit<4> ihl; bit<8> diffserv; bit<16> totalLen; bit<16> identification;
    bit<3> flags; bit<13> fragOffset; bit<8> ttl; bit<8> protocol; bit<16> hdrChecksum;
    ip4Addr_t srcAddr; ip4Addr_t dstAddr; }
struct metadata { }
struct headers { ethernet_t ethernet; ipv4_t ipv4; }

parser MyParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t sm) {
    state start { transition parse_ethernet; }
    state parse_ethernet { packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) { TYPE_IPV4: parse_ipv4; default: accept; } }
    state parse_ipv4 { packet.extract(hdr.ipv4); transition accept; }
}
control MyVerifyChecksum(inout headers hdr, inout metadata meta) { apply { } }
control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t sm) {
    action drop() { mark_to_drop(sm); }
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        sm.egress_spec = port; hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr; hdr.ipv4.ttl = hdr.ipv4.ttl - 1; }
    table ipv4_lpm { key = { hdr.ipv4.dstAddr: lpm; } actions = { ipv4_forward; drop; NoAction; }
                     size = 1024; default_action = drop(); }
    apply { if (hdr.ipv4.isValid()) { ipv4_lpm.apply(); } }
}
control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t sm) { apply { } }
control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply { update_checksum(hdr.ipv4.isValid(),
        { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv, hdr.ipv4.totalLen, hdr.ipv4.identification,
          hdr.ipv4.flags, hdr.ipv4.fragOffset, hdr.ipv4.ttl, hdr.ipv4.protocol, hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
        hdr.ipv4.hdrChecksum, HashAlgorithm.csum16); } }
control MyDeparser(packet_out packet, in headers hdr) { apply { packet.emit(hdr.ethernet); packet.emit(hdr.ipv4); } }
V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(), MyComputeChecksum(), MyDeparser()) main;
```
**Reading it.** The `header` types define byte layouts exactly as Lab 9.4's `struct.unpack` does. The parser is a state machine: it extracts the Ethernet header, branches on `etherType`, and extracts IPv4. `MyIngress` holds the match-action logic: a table keyed on the destination address with *longest-prefix* matching whose actions rewrite the MAC addresses, set the output port and decrement the TTL; the controller fills the table at run time through P4Runtime. `MyComputeChecksum` recomputes the header checksum after the TTL change (hardware often uses the incremental update shown in Lab 9.4). The deparser re-serialises the valid headers. A header never extracted stays invalid and is not emitted, which is how tunnels are added or removed: extract the outer header and do not emit it.

## Advanced: stateful processing and what fits in a pipeline
A **register** array stores per-index state that a packet can read, modify and write back within one stage, enabling per-flow counters, sketches (a count-min row is one register array indexed by a hash), meters and simple state machines such as TCP flag tracking. Constraints decide what is feasible: a packet touches each register at most once in the pipeline; the arithmetic is integer, with limited ops; recirculation (sending the packet through the pipeline again) buys extra passes at the cost of throughput; and the stage count (a dozen to a few tens) bounds dependent steps. This is why algorithms must be redesigned for the data plane: HULA keeps the best next hop per destination ToR using probes rather than flow state; heavy-hitter detectors keep a small 'candidate' table next to a sketch; and in-network aggregation (SwitchML) streams fixed-size vectors through a pool of accumulators.

## Advanced: the cost of telemetry
In-band telemetry adds metadata to packets: with k hops and h bytes of metadata per hop the added bytes are about a header plus k·h (e.g. 5 hops × 16 B = 80 B, 5.3% of a 1,500-byte packet and 55% of a 150-byte one). Operators therefore *sample* (mark one packet in N), use postcards (each switch exports its own report rather than stacking it in the packet) or export only on events such as a queue exceeding a threshold or a packet drop (mirror-on-drop). The collector must handle millions of reports per second, so filtering and aggregation in the data plane (Bloom filters and sketches again) are part of the design.

[[fig:bloomfp]]

## Advanced: header-space analysis and what verification costs
Lab 9.6 treats each rule as a transfer function on sets of headers. Real tools represent these sets as unions of wildcard expressions (HSA), binary decision diagrams or SMT formulas, and answer reachability, loop, black-hole and isolation questions. Complexity comes from rewrites (NAT, tunnels) and from the number of rules; tools reach millions of rules by computing *equivalence classes* of packets that are treated identically (VeriFlow, APV) and by processing updates incrementally. Control-plane verification (Batfish-like) goes one level up: it models the routing protocols to predict the forwarding tables from the configuration, catching errors before deployment. Limits: models of vendor behaviour may be incomplete, dynamic behaviour (failures, timing, convergence) is harder than static snapshots, and verification proves only the properties you state.

## Advanced: controller architecture and scale
A production controller is a distributed system: a replicated, consistent store for network state (ONOS and OpenDaylight use clustering with consensus or eventually consistent stores for different data), southbound drivers for many device types, northbound APIs, and application logic. Typical goals: tens of thousands of devices, sub-second reaction to failures, no single point of failure. Design principles drawn from operations: keep the data plane able to forward without the controller (fail-static); reconcile *intended* versus *actual* state continuously rather than trusting every message; version and roll out network changes like software with staged rollout and automatic rollback; and monitor the controller's own latency. Management protocols have converged on **gNMI/gRPC** with **YANG** models and streaming telemetry instead of polling SNMP.

## Advanced: SDN and the limits of centralisation
Centralisation gives a global view but adds a control-loop latency of milliseconds to seconds, so reflexes (fast reroute, link-failure detection with BFD, load balancing per flowlet) stay in the data plane or on the device, while slow optimisation (traffic engineering, capacity planning, policy) lives in the controller. This hybrid, a **logically centralised, physically distributed** control plane, is the pattern in Google's Jupiter and B4, in cloud virtual networks (the controller pushes encapsulation and filtering rules to host virtual switches such as Open vSwitch or custom smart NICs) and in enterprise intent-based systems.

""", ex=[
    ("A Bloom filter holds n = 1,000,000 items in 10 bits per item with k = 7 hash functions. Memory and false-positive rate?", "m = 10⁷ bits = 1.25 MB; FPR ≈ (1 − e^(−0.7))⁷ = 0.5034⁷ ≈ 0.82%."),
    ("A reactive controller handles 10,000 new flows/s with 128-byte Packet-Ins. Control-channel bandwidth?", "10,000 × 128 × 8 = 10.24 Mb/s (plus the Flow-Mods back), and every flow's first packet pays a controller round trip."),
    ("2,000 hosts, exact-match all-pairs rules. Entries needed versus per-destination rules?", "2,000 × 1,999 ≈ 4.0 million versus 2,000."),
    ("A ternary 5-tuple rule uses 104 key bits. How much TCAM do 1 million such rules need?", "About 2 × 104 = 208 bits each → 208 Mbit ≈ 26 MB, far beyond typical TCAM capacities, so rules must be aggregated or kept in SRAM-based tables."),
    ("Why must an incremental checksum update use the old *and* new 16-bit word?", "The checksum is a one's-complement sum, so replacing a word m by m' changes it by (m' − m): HC' = ~(~HC + ~m + m')."),
    ("Why do the 10xxxxxx headers loop in the header-space lab?", "Switch B sends them back to A, and A forwards all headers starting with 1 to B again.")],
    obj=["Write and run a P4-style parser and checksum update.", "Size Bloom filters and sketches for a measurement task and explain the verification, update and controller-scale issues of SDN."],
    rd=["Bloom (1970) Space/time trade-offs in hash coding with allowable errors. CACM.", "Broder & Mitzenmacher (2004) Network applications of Bloom filters: a survey.", "Kazemian, Varghese, McKeown (2012) Header space analysis. NSDI.", "Fogel et al. (2015) A general approach to network configuration analysis (Batfish). NSDI.", "Katta et al. (2016) HULA: scalable load balancing using programmable data planes. SOSR.", "Jin et al. (2017) NetCache: balancing key-value stores with fast in-network caching. SOSP.", "Sapio et al. (2021) Scaling distributed machine learning with in-network aggregation. NSDI."])

# =====================================================================
# WEEK 14
# =====================================================================
LAB(14, "A training-step budget: compute, tensor, pipeline and data-parallel communication", "An illustrative model of one step of a GPT-3-scale training job (175 B parameters, 96 layers, hidden size 12,288, 3.1 M tokens per step) on 1,024 GPUs with 300 TFLOP/s effective per GPU, 300 GB/s inside a server and 50 GB/s per GPU across servers. Tensor parallelism (t) does four all-reduces per layer per microbatch, pipeline parallelism (p) sends activations between stages, data parallelism (d) all-reduces gradients. Memory limits are ignored; this shows where network time goes.", """
def step(t, p, N=1024, P=175e9, L=96, h=12288, tokens=3.1e6, seq=2048, F=300e12, bw_in=300e9, bw_net=50e9, by=2):
    d = N // (t * p)
    comp = 6 * P * tokens / (N * F)
    mb = tokens / d / seq                                  # microbatches (one sequence each) per replica
    act = seq * h * by                                     # one activation tensor (bytes)
    tp = (L / p) * mb * 4 * (2 * (t - 1) / t) * act / bw_in
    pp = mb * 2 * act / bw_net
    dp = 2 * (d - 1) / d * (P / (t * p) * by) / bw_net
    bubble = comp * (p - 1) / mb
    return d, mb, comp, tp, pp, dp, bubble
print(" t  p   d  microb | compute  TP-comm  PP-comm  DP-comm  pipe-bubble | efficiency if comm not overlapped")
for t, p in ((8, 8), (8, 16), (4, 8), (8, 4)):
    d, mb, comp, tp, pp, dp, bub = step(t, p)
    eff = comp / (comp + tp + pp + dp + bub)
    print(f"{t:2d} {p:2d} {d:3d} {mb:7.0f} | {comp:6.2f}s {tp:7.2f}s {pp:7.2f}s {dp:7.2f}s {bub:9.2f}s | {eff:6.1%}")
""")
LAB(14, "RoCEv2 packet overhead and line-rate packet rates", "RoCEv2 adds Ethernet, IP, UDP (destination port 4791), the 12-byte InfiniBand base transport header (BTH) and a 4-byte ICRC to each payload; on the wire add preamble and inter-frame gap.", """
overhead = 8 + 12 + 14 + 4 + 20 + 8 + 12 + 4       # preamble, IFG, Ethernet, FCS, IPv4, UDP, BTH, ICRC
print("per-packet overhead on the wire:", overhead, "bytes")
for payload in (256, 1024, 2048, 4096):
    eff = payload / (payload + overhead); pps = 400e9 / 8 / (payload + overhead)
    print(f"payload {payload:5d} B: efficiency {eff:6.1%}  line-rate packet rate at 400 Gb/s {pps/1e6:6.1f} Mpps  goodput {eff*400:6.1f} Gb/s")
""")
LAB(14, "PFC deadlock: finding cyclic buffer dependencies", "With priority flow control a queue cannot drain while the downstream queue it feeds is full and has paused it. Draw an edge X → Y when X waits for room in Y; a cycle means a possible deadlock. Up-then-down (valley-free) routing in a Clos fabric has no cycle; a detour that goes down, up and down again can.", """
def has_cycle(graph):
    color = {}
    def dfs(u):
        color[u] = 1
        for v in graph.get(u, []):
            if color.get(v) == 1: return True
            if color.get(v) is None and dfs(v): return True
        color[u] = 2; return False
    return any(color.get(u) is None and dfs(u) for u in list(graph))
tree = {"leaf1.up": ["spine1.down"], "spine1.down": ["leaf2.host"], "leaf2.host": []}
bounce = {"leaf1.up": ["spine1.down"], "spine1.down": ["leaf2.up"], "leaf2.up": ["spine2.down"], "spine2.down": ["leaf1.up"]}
print("valley-free routing, cyclic buffer dependency:", has_cycle(tree))
print("down-up-down detour after a link failure, cyclic buffer dependency:", has_cycle(bounce))
""")
LAB(14, "A simplified DCQCN rate controller", "Two flows (starting at 80 and 10 Gb/s) share a 100 Gb/s link. When the aggregate exceeds capacity, flows are marked with probability proportional to their rate and cut their rate by α/2 (α is an EWMA of marks); otherwise they recover towards their target rate and then add a small increment. A fluid caricature of DCQCN: it shows the control law, not hardware timing.", """
import random
def dcqcn(C=100.0, start=(80.0, 10.0), steps=48000, g=1 / 16, rai=0.02, seed=1):
    rnd = random.Random(seed); rc = list(start); rt = list(start); al = [1.0] * len(rc); st = [0] * len(rc); out = []
    for t in range(steps):
        over = sum(rc) > C
        for i in range(len(rc)):
            if over and rnd.random() < rc[i] / sum(rc):
                rt[i] = rc[i]; rc[i] *= 1 - al[i] / 2; al[i] = (1 - g) * al[i] + g; st[i] = 0
            else:
                al[i] *= 1 - g; st[i] += 1
                if st[i] > 5: rt[i] += rai
                rc[i] = (rc[i] + rt[i]) / 2
        if t % 8000 == 0 or t == steps - 1: out.append((t, [round(x, 1) for x in rc]))
    return out
for t, r in dcqcn(): print(f"step {t:6d}: rates (Gb/s) {r}   total {sum(r):6.1f}")
""")
LAB(14, "Sizing a GPU fabric and choosing a checkpoint interval", "A non-blocking fat-tree built from k-port switches supports k²/2 endpoints with two tiers and k³/4 with three. Large clusters fail often; Young's formula gives the checkpoint interval T = √(2·δ·M) that minimises lost work (δ = checkpoint time, M = cluster mean time between failures).", """
import math
print("radix  2-tier GPUs  3-tier GPUs  3-tier switches  3-tier links")
for k in (32, 64, 128): print(f"{k:5d} {k*k//2:12d} {k**3//4:12d} {5*k*k//4:15d} {3*k**3//4:13d}")
N, mtbf_gpu_h, ckpt = 16384, 50000.0, 60.0
M = mtbf_gpu_h / N * 3600
T = math.sqrt(2 * ckpt * M)
print(f"{N} GPUs, per-GPU MTBF {mtbf_gpu_h:.0f} h -> cluster MTBF {M/3600:.2f} h")
print(f"checkpoint cost {ckpt:.0f} s: optimal interval {T/60:.1f} min, expected overhead about {math.sqrt(2 * ckpt / M):.1%}")
""")
extend(14, r"""
## Basics: the numbers you need to reason about AI clusters
### Sizes
A model with P parameters stored in 16-bit format takes 2P bytes; a 70-billion-parameter model's gradients are 140 GB. Training also stores optimiser state (often 8 to 16 bytes per parameter) and activations, which is why one GPU (80 GB-class memory) cannot hold a large model and the work is split. The compute per training step is approximately 6 × P × (tokens in the batch) floating-point operations (2 for the forward pass, 4 for the backward pass), which fixes the compute time for a given number of GPUs and their sustained speed. Lab 14.3 uses exactly this.

### A step in the life of one GPU
1. Receive a microbatch of tokens. 2. Compute the forward pass layer by layer (tensor-parallel layers need an all-reduce after some operations). 3. Send activations to the next pipeline stage. 4. Compute the backward pass in reverse, producing gradients. 5. All-reduce gradients with data-parallel peers (overlapped with step 4 where possible). 6. Update parameters. The network appears in steps 2, 3 and 5, and each uses a different pattern and a different part of the fabric.

### Four network tiers
| Tier | Typical bandwidth per GPU | Used by |
|---|---|---|
| On-package memory (HBM) | thousands of GB/s | the GPU itself |
| Intra-server (NVLink/NVSwitch-class) | hundreds of GB/s | tensor parallelism |
| Server NIC to leaf switch | 25 to 100 GB/s (200 to 800 Gb/s) | pipeline and data parallelism |
| Across the fabric (spine, super-spine) | shared and often tapered | data parallelism, mixture-of-experts all-to-all |

### RDMA verbs in one picture
An application registers memory with the NIC, creates a **queue pair** (a send queue and a receive queue), and posts **work requests** (send, receive, RDMA write, RDMA read) to it. The NIC executes them and posts **completion entries** to a completion queue that the application polls, with no system call on the fast path. *One-sided* operations (RDMA write/read) touch remote memory without involving the remote CPU. RoCEv2 packets are Ethernet + IP + UDP (port 4791) + a 12-byte base transport header + payload + ICRC; Lab 14.4 shows the resulting efficiency (about 98% for 4 KB payloads, 76% for 256 B).

### Why a lossless network?
Early RDMA NICs recovered from loss by *go-back-N*: on a gap the sender resends everything after the lost packet. With thousands of packets in flight, even a 10⁻⁴ loss rate wastes a few percent of capacity, and a larger rate collapses throughput, so operators built *lossless* Ethernet using **priority flow control (PFC)**: a switch whose queue is nearly full sends a pause frame upstream so no packet is dropped. The price is that pauses propagate: a congested port can block unrelated flows sharing the upstream queue (head-of-line blocking), and cyclic dependencies can deadlock (Lab 14.5).

### Self-check
Roughly how many FLOPs does a step with a 7 B-parameter model and a 1 M-token batch need? (6 × 7×10⁹ × 10⁶ = 4.2×10¹⁶.) Which parallelism needs the fastest links? Why is a lost packet more costly with go-back-N than with selective retransmission?

[[demo:train]]
""", r"""
## Advanced: the training-step budget in detail
Lab 14.3 builds an explicit model. Compute time = 6·P·tokens/(N·F). Tensor parallelism of degree t performs, per layer and microbatch, two all-reduces in the forward pass and two in the backward pass, each over an activation tensor of seq·h·bytes (one sequence per microbatch here), so its traffic per GPU is (L/p)·m·4·2(t−1)/t·seq·h·bytes with m microbatches; because this is frequent and on the critical path, it must stay inside the fast intra-server domain. Pipeline parallelism sends one activation tensor forward and one gradient backward per microbatch per stage boundary, and idles during the pipeline *bubble*, a fraction (p−1)/m of compute for m microbatches (interleaved schedules reduce it). Data parallelism all-reduces the gradient shard of P/(t·p) parameters among d replicas, once per step, and can overlap with the backward pass. Reading the lab's table: for this configuration compute dominates, tensor-parallel traffic is the largest communication term yet stays on the fast links, and data-parallel traffic over the fabric is small per step; but if the fabric were slower, shrinking the number of GPUs per replica group, or the model's width, changes the balance. The principal design rule: **map the most frequent, largest collectives to the fastest links** and reserve the oversubscribed fabric for infrequent traffic.

## Advanced: sharded data parallelism and memory-driven communication
Data parallelism replicates the whole model on each GPU, which wastes memory. Sharded schemes (ZeRO, fully-sharded data parallel) split optimiser state, gradients and parameters across the data-parallel group, then **all-gather parameters just before use and reduce-scatter gradients just after**. Communication volume rises to about 1.5× that of plain data parallelism (an all-gather in the forward pass, another in the backward pass, plus a reduce-scatter), but memory per GPU falls roughly in proportion to the group size, enabling larger models. Network consequence: many medium-sized collectives instead of one large all-reduce, so latency and overlap quality matter more.

## Advanced: mixture-of-experts and all-to-all
In mixture-of-experts layers each token is routed to a few experts held on different GPUs, requiring an all-to-all before and after the expert computation, per layer, in both passes. All-to-all has no locality: each GPU sends a distinct slice to every other GPU, so traffic crosses the full bisection of the fabric and is sensitive to load imbalance (a popular expert becomes a hotspot and an incast target). Mitigations: capacity factors and auxiliary balancing losses in the model, hierarchical all-to-all (aggregate by node first), placing expert groups within a rail or pod, and overlapping communication with computation by chunking.

## Advanced: congestion control for RDMA in more detail
In DCQCN, switches mark packets with ECN when the queue exceeds a threshold; the receiver NIC reflects marks as congestion notification packets (CNPs); the sender's reaction point cuts its rate, keeps an EWMA α of recent congestion, then raises its rate in three phases (fast recovery towards the previous target, additive increase, hyper increase). Lab 14.6 simulates a simplified version, showing the multiplicative cut α/2 and the recovery. Known issues include sensitivity to parameters (the marking thresholds and timers must be tuned to link speed and RTT), unfairness when flows have different RTTs, and slow convergence at 400 Gb/s and beyond. Alternatives: **TIMELY** (RTT-gradient rate control), **HPCC** (uses in-band telemetry to compute the exact inflight bytes per link), **Swift** (delay targets, host plus fabric), receiver-driven protocols (**Homa**, **NDP**: the receiver paces senders with credits or pulls, and switches may trim payloads on overflow, keeping headers), and the Ultra Ethernet design of packet-sprayed multipath transports with selective retransmission. Whatever the scheme, the fabric's load balancing and congestion control interact: per-packet spraying removes hash collisions but reorders packets, so the transport needs out-of-order tolerance.

## Advanced: PFC deadlock, storms and mitigation
A **deadlock** needs a cyclic buffer dependency (CBD). In a Clos fabric routed strictly up then down there is no cycle, but link failures or misconfigurations can force packets to go down, up and down again, creating one (Lab 14.5's second graph). A **pause storm** occurs when a faulty NIC keeps sending pause frames: the pause propagates upstream and can freeze large parts of the fabric. Mitigations: watchdogs that drop packets or disable PFC on a queue stuck paused for too long, routing that forbids valleys, separate priority classes for different path stages (rotating the priority at each valley), limiting PFC to the first hop (ToR-to-NIC) and relying on end-to-end congestion control and fast loss recovery elsewhere, and, for new designs, avoiding PFC through selective retransmission and trimming.

## Advanced: sizing the fabric and its cost
Lab 14.7 computes sizes: with 64-port switches a non-blocking two-tier fabric reaches 2,048 endpoints and a three-tier one 65,536, needing 5,120 switches and about 196,608 links (each of which, above the ToR, usually carries two optical transceivers). Optics and cabling dominate cost and failure rates, so designers trade oversubscription (tapering the upper tiers: 2:1 halves the upper-tier switches and links), bandwidth per GPU, and the number of tiers. Rail optimisation keeps same-rail traffic below the spine. Larger radix switches (51.2 Tb/s generations) reduce tiers; co-packaged optics and lower-power links reduce the cost per bit. Failure modelling: with many components the cluster's mean time between failures is the component MTBF divided by the number of components, so a 16,384-GPU job sees a failure every few hours; the checkpoint interval from Young's formula and fast job restart (spare nodes, localised restart, in-memory checkpoints) are essential parts of the design.

## Advanced: measuring and operating AI fabrics
Useful signals: collective completion times and their variance across ranks (stragglers), link utilisation at fine granularity, ECN mark and PFC pause counts per queue, retransmission and NIC error counters, and *burst* statistics. Debugging uses collective-level traces (which rank waited on which peer), synthetic benchmarks (NCCL tests across a sweep of message sizes and GPU counts), and topology-aware health checks that find a single slow cable or misconfigured port before it slows a whole job. Because one slow link slows every GPU, **tail behaviour**, not average bandwidth, defines usable capacity.

[[fig:hier]]
""", ex=[
    ("RoCEv2 with 1,024-byte payloads: wire efficiency?", "Overhead 82 B (preamble 8, IFG 12, Ethernet 14, FCS 4, IP 20, UDP 8, BTH 12, ICRC 4): 1024/1106 = 92.6%."),
    ("Gradients of a 70 B-parameter model in 16-bit format are all-reduced with plain data parallelism over a 50 GB/s network (large N, ignore latency). Time?", "Gradient size 140 GB; a ring sends ≈ 2×140 GB per GPU; 280/50 = 5.6 s."),
    ("Young's formula with checkpoint time 120 s and cluster MTBF 6 h?", "T = √(2 × 120 × 21,600) ≈ 2,277 s ≈ 38 min; overhead ≈ √(2·120/21,600) ≈ 10.5%."),
    ("How many GPUs does a non-blocking 32-port-switch fabric support with two tiers and with three?", "k²/2 = 512 and k³/4 = 8,192."),
    ("All-to-all with N = 256 GPUs, 2 GB per GPU, 50 GB/s, ignoring latency?", "(255/256) × 2 GB / 50 GB/s ≈ 39.8 ms."),
    ("Why does FSDP/ZeRO increase communication volume by about 1.5× yet remain popular?", "It adds a second all-gather of parameters (forward and backward) to the reduce-scatter, but memory per GPU falls roughly by the group size, which lets models fit that otherwise would not.")],
    obj=["Build a compute-versus-communication budget for a parallel training job and place each collective on the right network tier.", "Explain DCQCN-style control, PFC deadlocks and fabric sizing and failure arithmetic for GPU clusters."],
    rd=["Shoeybi et al. (2019) Megatron-LM: training multi-billion parameter language models using model parallelism.", "Narayanan et al. (2021) Efficient large-scale language model training on GPU clusters using Megatron-LM. SC.", "Rajbhandari et al. (2020) ZeRO: memory optimizations toward training trillion parameter models. SC.", "Jouppi et al. (2023) TPU v4: an optically reconfigurable supercomputer for machine learning. ISCA.", "Mittal et al. (2015) TIMELY: RTT-based congestion control for the datacenter. SIGCOMM.", "Li et al. (2019) HPCC: high precision congestion control. SIGCOMM.", "Montazeri et al. (2018) Homa: a receiver-driven low-latency transport protocol. SIGCOMM.", "Handley et al. (2017) Re-architecting datacenter networks and stacks for low latency and high performance (NDP). SIGCOMM.", "Daly (2006) A higher order estimate of the optimum checkpoint interval for restart dumps. FGCS."])
