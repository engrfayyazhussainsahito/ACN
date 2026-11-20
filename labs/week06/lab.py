"""Week 6: Modern Transport: QUIC, TLS 1.3 and Multipath
Run: python3 lab.py"""


# ===== Code lab =====
def ttfb(rtt_ms, setup): return {"tcp+tls12": 4, "tcp+tls13": 3, "quic": 2, "quic0": 1}[setup] * rtt_ms
for s in ("tcp+tls12", "tcp+tls13", "quic", "quic0"): print(f"{s:10s} @150 ms RTT: {ttfb(150, s):4.0f} ms")

def p_loss(p, n): return 1 - (1 - p) ** n
for p, n in ((0.01, 100), (0.005, 40), (0.001, 100)): print(f"p={p:.3f} n={n:3d}: P(>=1 loss) = {p_loss(p, n):.1%}")


# ===== Measuring head-of-line blocking =====
# 10 streams of 30 packets are interleaved on one connection (window 20 packets per RTT, random loss p). A packet is *usable* by the application only when every earlier packet in its ordering domain has arrived: the whole connection for TCP/HTTP/2, only its own stream for QUIC. The head-of-line (HOL) delay is usable time minus arrival time, in RTTs.
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


# ===== ACK ranges and the probe timeout =====
# QUIC acknowledges ranges of packet numbers, and its probe timeout (RFC 9002) is PTO = SRTT + max(4·RTTVAR, 1 ms) + max_ack_delay, doubling on each consecutive PTO.
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


# ===== QUIC variable-length integers and stream IDs =====
# QUIC encodes integers in 1, 2, 4 or 8 bytes; the two top bits of the first byte give the length. The sample values are the examples in RFC 9000 Appendix A. Stream IDs carry the initiator and direction in their two low bits.
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


# ===== The QUIC RTT estimator, probe timeout and loss threshold =====
# RFC 9002: the first sample sets smoothed_rtt = sample and rttvar = sample/2; later samples subtract the peer's ack delay when that keeps the result above the minimum RTT. PTO = smoothed_rtt + max(4·rttvar, 1 ms) + max_ack_delay and doubles on each consecutive PTO. A packet is declared lost when older than 9/8·max(smoothed, latest) RTT.
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


# ===== HKDF (RFC 5869) and a toy Diffie-Hellman exchange =====
# TLS 1.3 and QUIC derive every key with HKDF-Extract and HKDF-Expand. This lab checks our implementation against RFC 5869 test case 1, derives labelled keys the way the TLS 1.3 key schedule does (with simplified labels), and runs Diffie-Hellman with tiny numbers.
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
hs = extract(b"\x00" * 32, secret)                          # handshake secret
ck, sk = expand(hs, b"tls13 c hs traffic", 16), expand(hs, b"tls13 s hs traffic", 16)
print("client key:", ck.hex(), "\nserver key:", sk.hex(), "\ndifferent labels give independent keys:", ck != sk)


# ===== Window-limited throughput and the BDP =====
# A sender may have at most one window per round trip in flight, so throughput = window / RTT (until the link rate). Tabulate Mb/s for typical receive windows and paths.
print("RTT      64 KB window   1 MB window   16 MB window   BDP of 1 Gb/s path")
for rtt in (0.005, 0.020, 0.100, 0.300):
    row = [min(1000.0, w * 8 / rtt / 1e6) for w in (64e3, 1e6, 16e6)]
    print(f"{rtt*1000:4.0f} ms " + "".join(f"{x:13.1f} Mb/s" for x in row) + f"   {1e9*rtt/8/1e6:8.2f} MB")
