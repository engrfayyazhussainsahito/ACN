"""Week 12: Network Security: DDoS, DNS, TLS and BGP
Run: python3 lab.py"""


# ===== Code lab =====
def attack(attacker_gbps, factor): return attacker_gbps * factor
for name, f in (("DNS", 54), ("NTP", 557), ("memcached", 51000)):
    print(f"{name:10s} 0.1 Gb/s botnet -> {attack(0.1, f):8.1f} Gb/s at victim")

backlog, life = 1024, 1 + 2 + 4 + 8 + 16 + 32
print("half-open lifetime:", life, "s;  SYN/s to fill backlog:", round(backlog / life, 1))
def roa(prefix_len, maxlen, origin, roa_as): return "valid" if origin == roa_as and prefix_len <= maxlen else "invalid"
print("/16 from owner:", roa(16, 16, 64500, 64500), "  /24 hijack from owner AS:", roa(24, 16, 64500, 64500), "  /16 from attacker:", roa(16, 16, 666, 64500))


# ===== A toy SYN-cookie =====
# Encode the connection's 4-tuple, a coarse timestamp and an MSS index into the 32-bit initial sequence number, authenticated with a keyed hash, so the server stores nothing until the final ACK returns a valid cookie. (Educational only, not the Linux algorithm.)
import hmac, hashlib
SECRET = b"server-secret-key"
def cookie(src, sport, dst, dport, t, mss_idx):
    msg = f"{src}:{sport}>{dst}:{dport}:{t}".encode()
    h = int.from_bytes(hmac.new(SECRET, msg, hashlib.sha256).digest()[:3], "big")      # 24-bit MAC
    return ((t & 31) << 27) | (mss_idx << 24) | h                                       # 5-bit time + 3-bit MSS index + MAC
def validate(c, src, sport, dst, dport, now, max_age=2):
    t5, mss_idx = c >> 27, (c >> 24) & 7
    for age in range(max_age + 1):
        t = now - age
        if t & 31 == t5 and cookie(src, sport, dst, dport, t, mss_idx) == c: return True, mss_idx
    return False, None
c = cookie("203.0.113.9", 40000, "198.51.100.1", 443, t=100, mss_idx=3)
print("cookie:", hex(c))
print("valid ACK, 1 tick later  :", validate(c, "203.0.113.9", 40000, "198.51.100.1", 443, now=101))
print("valid ACK, 10 ticks later:", validate(c, "203.0.113.9", 40000, "198.51.100.1", 443, now=110))
print("spoofed source address   :", validate(c, "203.0.113.10", 40000, "198.51.100.1", 443, now=101))
print("forging a 24-bit MAC by guessing succeeds with probability", 2 ** -24)


# ===== DNS cache poisoning odds =====
# A blind attacker must guess the 16-bit query ID (and, with source-port randomisation, the port) before the real answer arrives. Probability that k spoofed packets win a single race, and over many races.
ports = 64511
for k in (100, 1000):
    p_id = k / 65536; p_both = k / (65536 * ports)
    print(f"{k:5d} spoofed packets per race: ID only {p_id:.4%}   ID + random port {p_both:.2e}")
races = 5000     # Kaminsky: unlimited fresh races using non-existent subdomains
p1 = 100 / 65536
print(f"ID only, {races} races: P(poisoned) = {1 - (1 - p1) ** races:.4f}")
p2 = 100 / (65536 * ports)
print(f"ID + port, {races} races: P(poisoned) = {1 - (1 - p2) ** races:.2e}")
