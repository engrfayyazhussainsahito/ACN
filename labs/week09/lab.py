"""Week 9: SDN and Programmable Data Planes
Run: python3 lab.py"""


# ===== Code lab =====
rules = [("10.0.0.0/8", "port1"), ("10.1.0.0/16", "port2"), ("10.1.2.0/24", "port3"), ("0.0.0.0/0", "drop")]
def ip(s): a = s.split("."); return sum(int(x) << (24 - 8 * i) for i, x in enumerate(a))
def lpm(addr):
    best = None
    for pre, act in rules:
        base, l = pre.split("/"); l = int(l); mask = (0xFFFFFFFF << (32 - l)) & 0xFFFFFFFF if l else 0
        if ip(addr) & mask == ip(base) & mask and (best is None or l > best[0]): best = (l, act)
    return best[1]
for a in ("10.1.2.7", "10.1.9.9", "10.200.0.1", "8.8.8.8"): print(a, "->", lpm(a))

import random
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
print("merged equals sketch of concatenation:", M == sketch(A + B))


# ===== A match-action switch =====
# A tiny interpreter for prioritised wildcard rules, the abstraction behind OpenFlow and P4 tables. Fields not mentioned in a rule are wildcards.
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


# ===== Consistent updates: naive versus two-phase =====
# Four switches A, B, C, D. The old routes are A→B→C→D; the new ones are A→C→B→D. Updating the switches one at a time in every possible order exposes transient loops; version-tagging (two-phase) never does.
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


# ===== Heavy-hitter detection with a count-min sketch =====
# Detect flows carrying at least 0.5% of 200,000 packets with a 4-row sketch of increasing width; report precision and recall against ground truth.
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


# ===== From bytes to headers: parsing IPv4 and updating the checksum =====
# A programmable parser extracts headers from raw bytes; a data-plane step decrements the TTL and fixes the checksum. The sample header is the standard Wikipedia example (checksum 0xb861). The incremental update is RFC 1624: HC' = ~(~HC + ~m + m').
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
z = bytearray(pkt); z[10:12] = b"\x00\x00"
print("incremental checksum:", hex(inc), "| full recomputation:", hex(csum(bytes(z))), "| equal:", inc == csum(bytes(z)))


# ===== Bloom filters: measured versus theoretical false-positive rate =====
# A Bloom filter of m bits and k hash functions holds n items with false-positive rate (1 − e^(−kn/m))^k. Insert 20,000 items, then query 50,000 items that were never inserted.
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


# ===== A miniature header-space analysis: finding a forwarding loop =====
# Packet headers are 8-bit strings over {0,1,x}. Each switch has ordered match rules. We propagate the set of headers that match each rule along the network and flag paths that revisit a switch. This is the core idea of Header Space Analysis.
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


# ===== Reactive versus proactive rule installation =====
# 200 hosts generate 20,000 random flows. A reactive controller installs an exact-match (source, destination) rule for each new pair via Packet-In and Flow-Mod; a proactive controller pre-installs one rule per destination.
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
