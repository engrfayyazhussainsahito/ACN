# ---------------- Week 10 ----------------
LAB(10, "BPSK bit errors versus theory", "Send random bits as ±1 over additive white Gaussian noise and count errors at several Eb/N0 values. Theory: BER = ½·erfc(√(Eb/N0)).", """
import math, random
def ber_bpsk(ebn0_db, n=300000, seed=1):
    random.seed(seed); ebn0 = 10 ** (ebn0_db / 10); sigma = math.sqrt(1 / (2 * ebn0)); err = 0
    for _ in range(n):
        bit = random.random() < 0.5
        r = (1.0 if bit else -1.0) + random.gauss(0, sigma)
        err += (r > 0) != bit
    return err / n
print("Eb/N0(dB)  simulated BER   theory")
for db in (0, 2, 4, 6, 8):
    print(f"{db:8d}  {ber_bpsk(db):13.2e} {0.5 * math.erfc(math.sqrt(10 ** (db / 10))):10.2e}")
""")
LAB(10, "Wi-Fi contention: slotted CSMA/CA with binary exponential backoff", "N saturated stations with CWmin = 16 and up to 6 doublings. In each slot every station whose counter is zero transmits: one transmitter succeeds, two or more collide and double their windows. Reports the collision probability seen by a transmission attempt and the fraction of slots carrying a success.", """
import random
def csma(N, slots=60000, cwmin=16, stages=6, seed=1):
    random.seed(seed); cw = [cwmin] * N; cnt = [random.randrange(cwmin) for _ in range(N)]; ok = col = 0
    for _ in range(slots):
        tx = [i for i in range(N) if cnt[i] == 0]
        if len(tx) == 1:
            ok += 1; i = tx[0]; cw[i] = cwmin; cnt[i] = random.randrange(cw[i])
        elif len(tx) > 1:
            col += 1
            for i in tx: cw[i] = min(cw[i] * 2, cwmin * 2**stages); cnt[i] = random.randrange(cw[i])
        for i in range(N):
            if cnt[i] > 0 and i not in tx: cnt[i] -= 1
    return col / max(1, ok + col), ok / slots
print("stations  P(collision | busy slot)  success slots")
for N in (2, 5, 10, 20, 50): c, s = csma(N); print(f"{N:8d} {c:22.1%} {s:15.1%}")
""")
LAB(10, "Schedulers: round robin, max rate and proportional fair", "Three users with average SNR of 20, 10 and 0 dB and Rayleigh fading (instantaneous rate = log2(1 + SNR·X), X ~ exponential). Proportional fair serves the user with the highest instantaneous-to-average rate ratio.", """
import random, math
def sched(policy, snr=(100, 10, 1), T=60000, seed=2, tc=100):
    random.seed(seed); n = len(snr); avg = [1e-3] * n; tot = [0.0] * n
    for t in range(T):
        r = [math.log2(1 + snr[i] * random.expovariate(1)) for i in range(n)]
        if policy == "round robin": k = t % n
        elif policy == "max rate": k = max(range(n), key=lambda i: r[i])
        else: k = max(range(n), key=lambda i: r[i] / avg[i])
        for i in range(n): avg[i] = (1 - 1 / tc) * avg[i] + (1 / tc) * (r[k] if i == k else 0)
        tot[k] += r[k]
    return [x / T for x in tot]
def jain(x): return sum(x) ** 2 / (len(x) * sum(v * v for v in x))
for pol in ("round robin", "max rate", "proportional fair"):
    th = sched(pol); print(f"{pol:18s} per-user bits/s/Hz {[round(v, 2) for v in th]}  total {sum(th):.2f}  Jain {jain(th):.2f}")
""")
deepen(10, r"""
## Basics: sending bits through the air
A wireless signal is a wave. Its **frequency** (cycles per second) determines the channel; its **bandwidth** is the width of the frequency band it occupies (e.g. 20 MHz). Information is carried by changing a property of the wave, a process called **modulation**.

### Modulation: bits per symbol
Send one of 2^k distinct waveforms (symbols) and each symbol carries k bits. BPSK uses 2 phases (1 bit/symbol), QPSK 4 (2 bits), 16-QAM 16 combinations of amplitude and phase (4 bits), 256-QAM 8 bits. More bits per symbol means a higher rate, but the points sit closer together, so a little noise causes errors. That is why the rate you get depends on signal quality.

### Signal, noise and SNR
Signal power falls with distance (free-space path loss grows 20 dB per decade of distance), while thermal noise is roughly constant. The **signal-to-noise ratio** SNR = S/N, usually quoted in dB, decides which modulation works. The Shannon limit C = B·log₂(1 + SNR) is the ceiling no scheme can beat. The first lab shows how bit-error rate falls steeply as SNR rises.

### Why wireless is different from wires
- **Shared medium:** all nearby radios hear each other, so access must be coordinated.
- **Variable quality:** fading (multipath) makes the signal strength fluctuate over centimetres and milliseconds; movement changes it further.
- **Half duplex and no collision detection:** a radio cannot reliably listen while transmitting, so Wi-Fi *avoids* collisions (CSMA/CA) rather than detecting them.
- **Hidden terminals:** A and C can both reach B but not each other, so they may transmit at the same time and collide at B.
- **Loss unrelated to congestion:** packets are corrupted by noise, which TCP misreads as congestion.

### Two families
**Wi-Fi** (IEEE 802.11) uses unlicensed spectrum and contention-based access: stations listen, wait a random backoff, then transmit. **Cellular** (LTE, 5G) uses licensed spectrum and a central scheduler: the base station tells each phone when and on which frequencies to transmit. Scheduling gives better control and efficiency under load; contention is cheaper to deploy.

### Self-check
If SNR drops from 30 dB to 20 dB, what should a rate-adaptation algorithm do? (Choose a lower-order modulation and stronger coding.) Why is a hidden terminal not solved by 'listen before talk'?
""", r"""
## Advanced: OFDM, MIMO and the PHY
**OFDM** divides a wideband channel into many orthogonal narrow subcarriers (e.g. 64 in 20 MHz 802.11a/g, 256 in 802.11n/ac, up to 2048+ in 802.11ax/be). Each symbol is long compared with the multipath delay spread and is preceded by a cyclic prefix, so inter-symbol interference is absorbed and equalisation is a single complex multiplication per subcarrier. Subcarrier loading adapts modulation to each subcarrier's SNR in cellular systems.

**MIMO.** With Nt transmit and Nr receive antennas and channel matrix H, capacity is C = log₂ det(I + (SNR/Nt)·H·Hᴴ) per Hz, which scales roughly with min(Nt, Nr) in rich-scattering channels. Spatial multiplexing sends independent streams; beamforming steers energy towards a receiver (array gain ≈ 10·log₁₀(N) dB); MU-MIMO serves several users simultaneously with zero-forcing precoding, at the cost of channel-state feedback overhead. Massive MIMO in 5G uses dozens to hundreds of base-station antennas.

**802.11 evolution.** 802.11n/ac/ax/be add wider channels (up to 160 and 320 MHz), higher-order modulation (256-QAM, 1024-QAM, 4096-QAM in Wi-Fi 7), more streams, OFDMA (scheduled sub-channel access, so many small packets share one transmission) and multi-link operation (Wi-Fi 7). PHY rates have grown from 11 Mb/s to many Gb/s, but the MAC adds fixed overheads per transmission (DIFS, backoff, preamble, SIFS, ACK), so small frames waste airtime; **frame aggregation** (A-MPDU) amortises it: efficiency = payload time ÷ (payload time + fixed overhead), which approaches 1 only for large aggregates.

## Advanced: 802.11 MAC analysis
In the DCF, a station waits DIFS, picks a backoff uniform in [0, CW−1], counts down only in idle slots, transmits, and doubles CW after a collision (up to CWmax = 1023). Bianchi (2000) modelled each station with a two-dimensional Markov chain and obtained fixed-point equations for the per-slot transmission probability τ and the conditional collision probability p = 1 − (1−τ)^(N−1); saturation throughput peaks at a modest N and then declines as collisions grow. The second lab reproduces the qualitative trend (collision probability rising with N). The **performance anomaly** (Heusse et al.): because DCF gives each station equal *transmission opportunities*, a station at 1 Mb/s occupies the channel 11× longer per frame than an 11 Mb/s one, dragging all stations to nearly the same low throughput; airtime fairness schedulers and OFDMA fix it. Rate adaptation (Minstrel, RRAA, SampleRate) probes rates and uses delivery statistics; ML-based schemes are an active area.

## Advanced: cellular scheduling and 5G
LTE/5G schedule resource blocks every 1 ms (LTE) or fractions of a millisecond (NR with numerology μ: subcarrier spacing 15·2^μ kHz, slot length 1/2^μ ms). The classical **proportional-fair** scheduler selects the user maximising r_i(t)/R_i(t) (instantaneous achievable rate over average served rate): it exploits fading peaks (multiuser diversity) while keeping long-term fairness; the third lab compares it with round robin and a max-rate scheduler (which maximises total throughput but starves the cell-edge user). HARQ combines retransmissions with soft combining for fast, efficient recovery at the link layer; RLC and PDCP provide further reliability and ordering. 5G NR adds three service classes: eMBB (high throughput), URLLC (≈1 ms latency, 10⁻⁵ reliability, via mini-slots, grant-free access, and robust MCS) and mMTC (massive low-power devices). **Millimetre-wave** bands (24 to 100 GHz) offer GHz of bandwidth but have short range (path loss, blockage by bodies), so they need dense cells and beam tracking. Handover moves a call between cells: break-before-make in 2G, soft/make-before-break in later generations; at the transport layer it looks like an RTT step and possibly burst loss.

## Advanced: transport over wireless
Wireless links hide loss with link-layer ARQ and FEC at the price of variable delay (jitter); TCP then sees RTT variance and spurious timeouts (Eifel and F-RTO detect spurious retransmissions). ACK compression and aggregation break ACK clocking; BBR's bandwidth filter must cope with aggregated ACKs. Cellular operators deploy performance-enhancing proxies (split TCP), which help throughput but conflict with end-to-end encryption such as QUIC. Radio-aware congestion control (e.g., using PHY-rate feedback) and L4S marking in access networks are research and deployment topics.
""")

# ---------------- Week 11 ----------------
LAB(11, "Cache replacement policies on a Zipf workload", "LRU versus LFU for a 5,000-object catalogue with Zipf(1.0) popularity, 100,000 requests and a cache holding 1%, 5% or 10% of the catalogue. The 'ideal' policy keeps the most popular objects.", """
import random
from collections import OrderedDict, Counter
random.seed(4); N, R = 5000, 100000
w = [1 / (i + 1) for i in range(N)]
req = random.choices(range(N), w, k=R)
def lru(c):
    cache = OrderedDict(); hit = 0
    for x in req:
        if x in cache: hit += 1; cache.move_to_end(x)
        else:
            cache[x] = 1
            if len(cache) > c: cache.popitem(last=False)
    return hit / R
def lfu(c):
    cache, freq, hit = set(), Counter(), 0
    for x in req:
        freq[x] += 1
        if x in cache: hit += 1
        else:
            if len(cache) >= c:
                victim = min(cache, key=lambda y: freq[y])
                if freq[victim] < freq[x]: cache.remove(victim); cache.add(x)
            else: cache.add(x)
    return hit / R
tot = sum(w)
print("cache  LRU     LFU     ideal")
for pc in (0.01, 0.05, 0.10):
    c = int(pc * N); print(f"{pc:4.0%}  {lru(c):6.1%}  {lfu(c):6.1%}  {sum(w[:c]) / tot:6.1%}")
""")
LAB(11, "Throughput-based versus buffer-based adaptive bitrate", "A Markov-modulated bandwidth trace drives two players with the same ladder and 4 s chunks. The throughput player picks the highest bitrate under 80% of the last chunk's throughput; the buffer player maps buffer level (5 s reservoir, 15 s cushion) to a bitrate.", """
import random
ladder = [0.3, 0.75, 1.2, 2.4, 4.5]; CH = 4.0
def trace(n, seed):
    rnd = random.Random(seed); states = [0.8, 1.5, 3.0, 6.0]; i = 2; out = []
    for _ in range(n):
        if rnd.random() > 0.85: i = max(0, min(3, i + rnd.choice((-1, 1))))
        out.append(states[i] * rnd.uniform(0.8, 1.2))
    return out
def play(policy, bw):
    b, last, stall, tot, sw, prev = 8.0, bw[0], 0.0, 0.0, 0, None
    for x in bw:
        if policy == "throughput": r = max([l for l in ladder if l <= 0.8 * last] or [ladder[0]])
        else: r = ladder[round(min(1, max(0, (b - 5) / 15)) * (len(ladder) - 1))]
        dl = r * CH / x
        if dl > b: stall += dl - b; b = 0
        else: b -= dl
        b = min(30, b + CH); last = x; tot += r; sw += prev is not None and r != prev; prev = r
    return tot / len(bw), stall, sw
for pol in ("throughput", "buffer"):
    res = [play(pol, trace(150, s)) for s in range(60)]
    print(f"{pol:10s} mean bitrate {sum(r[0] for r in res)/60:5.2f} Mb/s   stall {sum(r[1] for r in res)/60:6.1f} s per session   switches {sum(r[2] for r in res)/60:5.1f}")
""")
deepen(11, r"""
## Basics: caches, CDNs and video
Most of what people watch and download is the *same* popular content fetched many times. Instead of serving each request from one distant origin server, a **content delivery network (CDN)** keeps copies in caches close to users. A request that finds the object in the cache is a **hit** (fast, cheap, no load on the origin); otherwise it is a **miss**, and the cache fetches from the origin or a bigger cache and usually stores the result.

### The hit ratio is everything
Mean latency = h·t_hit + (1 − h)·t_miss. If a hit costs 10 ms and a miss 200 ms, h = 90% gives 29 ms, and h = 99% gives 12 ms. Because origin servers are far fewer than caches, a high hit ratio also divides origin traffic by 1/(1−h): at 90% the origin sees one tenth of the load.

### How caches decide what to keep
A cache has limited space, so it must evict. **LRU** (least recently used) evicts the object unused for the longest time; **LFU** evicts the least frequently used. Web popularity follows a **Zipf** law: a few objects get most requests, so even a small cache helps a lot (Week 11's chart), while the long tail of rarely requested objects mostly misses.

### How does a user reach the nearest cache?
- **DNS-based redirection:** the CDN's authoritative DNS answers with the address of a good cache for the resolver's location.
- **Anycast:** many sites announce the same IP address and BGP delivers each user to a nearby one.
- **HTTP redirection / manifest rewriting** by the application.

### HTTP caching in two lines
`Cache-Control: max-age=3600` lets a cache reuse a response for an hour without asking; validators (`ETag`, `Last-Modified`) let it ask 'has this changed?' and get a small 304 reply.

### Video streaming basics
A video is encoded at several bitrates (a **ladder**, e.g. 0.3 to 4.5 Mb/s) and cut into chunks of 2 to 6 seconds. A manifest (DASH `.mpd` or HLS `.m3u8`) lists them. The player downloads chunks into a **buffer** and picks the bitrate of each next chunk. Too high a bitrate for the current bandwidth drains the buffer and causes a **rebuffering stall**; too low wastes quality. Viewers tolerate low quality much better than stalls.

### Self-check
A cache hit takes 5 ms, a miss 100 ms, the hit ratio is 80%. Mean latency? (0.8×5 + 0.2×100 = 24 ms.) Why does a 1% cache already give a high hit ratio on Zipf traffic?
""", r"""
## Advanced: modelling caches
**Zipf and the Che approximation.** For independent references with request probabilities pᵢ, the hit probability of object i in an LRU cache of size C is approximately 1 − e^(−pᵢ·T_C), where the characteristic time T_C solves Σᵢ (1 − e^(−pᵢ·T_C)) = C (Che et al. 2002). It is accurate for many workloads and lets operators dimension caches without simulation. For Zipf(α) popularity with α ≈ 0.8 to 1.0, hit ratio grows roughly logarithmically in cache size, so each doubling of cache buys a diminishing increment. In the first lab LFU beats LRU on a stationary Zipf workload (it is near-optimal), but real traffic is non-stationary (viral content, diurnal shifts) where LFU is slow to adapt; **TinyLFU/W-TinyLFU** and **ARC** combine recency and frequency, and admission filters keep one-hit wonders out (important when a large share of requested objects are requested once).

## Advanced: CDN architecture and economics
A CDN has edge caches in ISPs and IXPs, parent or regional caches, and often an **origin shield** to collapse many misses into one origin request (request coalescing). Content is mapped to servers within a cluster by **consistent hashing** (adding or removing a server remaps about 1/n of objects) and replicated for hot objects. Mapping users to clusters combines DNS/anycast with real-time measurements of latency, load and cost. ISPs host **embedded caches** (e.g., content provider appliances inside their network) because it cuts transit costs; large content providers peer directly at IXPs, shrinking the AS-path between users and content, one reason why the Internet has flattened. Transit is billed on the 95th percentile of 5-minute samples, while settlement-free peering exchanges traffic at no charge when flows are roughly balanced or mutually beneficial.

## Advanced: ABR algorithms
**Throughput-based** rules (the first player of the second lab) track a smoothed bandwidth estimate (the harmonic mean over recent chunks is robust to spikes) with a safety margin; they react quickly but oscillate. **Buffer-based** rules (BBA, Huang et al. 2014) ignore bandwidth estimates and map buffer occupancy to bitrate with a reservoir (always low bitrate below it) and a cushion (linear region), which makes them stable and rarely stall in steady state, but start-up needs special handling. **BOLA** derives an online rule from Lyapunov optimisation with a provable utility-vs-buffer trade-off. **MPC** chooses the next several chunks to maximise a QoE objective (bitrate − λ·rebuffer − μ·switches) using a throughput predictor; **RobustMPC** uses worst-case predictions; **Pensieve** trains a neural policy with reinforcement learning in simulation. Challenges: shared bottlenecks and fairness between competing players, on-off download patterns that confuse bandwidth estimation, and live streaming with 2 to 6 s latency targets where the buffer is tiny (low-latency HLS/DASH with CMAF chunked transfer, or WebRTC for sub-second latency).

## Advanced: quality of experience and encoding
User studies show that rebuffering ratio and start-up delay strongly affect engagement, with stall time being far worse than a modest quality drop. Encoding improvements shift the ladder: per-title and per-shot encoding choose bitrate by content complexity; perceptual metrics such as VMAF replace PSNR; newer codecs (HEVC, VP9, AV1, VVC) save tens of percent of bitrate at the same quality, at higher encode cost and sometimes licensing complexity. Network and application must be tuned together: for example HTTP/3 and BBR change throughput estimates, and server-side pacing and bitrate caps reduce burst losses.
""")

# ---------------- Week 12 ----------------
LAB(12, "A toy SYN-cookie", "Encode the connection's 4-tuple, a coarse timestamp and an MSS index into the 32-bit initial sequence number, authenticated with a keyed hash, so the server stores nothing until the final ACK returns a valid cookie. (Educational only, not the Linux algorithm.)", """
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
""")
LAB(12, "DNS cache poisoning odds", "A blind attacker must guess the 16-bit query ID (and, with source-port randomisation, the port) before the real answer arrives. Probability that k spoofed packets win a single race, and over many races.", """
ports = 64511
for k in (100, 1000):
    p_id = k / 65536; p_both = k / (65536 * ports)
    print(f"{k:5d} spoofed packets per race: ID only {p_id:.4%}   ID + random port {p_both:.2e}")
races = 5000     # Kaminsky: unlimited fresh races using non-existent subdomains
p1 = 100 / 65536
print(f"ID only, {races} races: P(poisoned) = {1 - (1 - p1) ** races:.4f}")
p2 = 100 / (65536 * ports)
print(f"ID + port, {races} races: P(poisoned) = {1 - (1 - p2) ** races:.2e}")
""")
deepen(12, r"""
## Basics: what can go wrong and what we want
Security is defined by goals. **Confidentiality**: only intended parties can read data. **Integrity**: data cannot be altered undetected. **Authenticity**: you know who you are talking to. **Availability**: the service works when needed. Networks threaten all four because packets cross machines you do not control.

### Attackers and capabilities
A *passive* attacker only reads traffic (a Wi-Fi eavesdropper). An *active* attacker can inject, modify, drop or replay packets (a rogue access point, a compromised router). An *off-path* attacker cannot see your packets but can send packets with forged source addresses. An *on-path* attacker can do all of this. The design question is always: against which attacker, and what do we assume stays secret (usually just keys)?

### The four crypto building blocks you need
- **Hash function:** a fixed-size fingerprint of data (SHA-256); any change alters it.
- **MAC / HMAC:** a hash that also needs a shared secret key, proving integrity and authenticity.
- **Symmetric encryption (AES, ChaCha20):** fast; encrypts bulk data with a shared key.
- **Public-key cryptography:** key exchange (Diffie-Hellman) to create a shared key over an open channel, and digital signatures (RSA, ECDSA, Ed25519) to prove identity.
A **certificate** is a signed statement 'this public key belongs to example.com'. Browsers trust a set of certificate authorities, and TLS uses certificates to authenticate servers.

### Three families of network attacks
1. **Denial of service (DoS/DDoS):** exhaust bandwidth, state or CPU. *Volumetric* (flood the link), *protocol* (SYN floods exhaust connection tables), *application-layer* (expensive requests).
2. **Spoofing and hijacking:** forging source addresses (UDP reflection), forging DNS answers, announcing someone else's IP prefix in BGP.
3. **Interception and tampering:** man-in-the-middle, downgrade attacks, traffic analysis.

### Defence in depth
No single mechanism is enough: filter spoofed packets near their source, encrypt and authenticate end to end (TLS), sign names and routes (DNSSEC, RPKI), absorb floods with distributed capacity (CDNs, anycast), and monitor everything.

### Self-check
Why can TLS protect a web page's contents but not hide which IP address you are visiting? What does a firewall that allows only established connections stop?
""", r"""
## Advanced: DDoS taxonomy and mitigation
**Reflection and amplification.** The attacker sends small requests with the victim's address as the source to many open servers (DNS, NTP, memcached, CLDAP, SSDP), which reply to the victim with large responses; the amplification factor is response size ÷ request size, with reported maxima from tens (DNS) to hundreds (NTP monlist) to tens of thousands (memcached). Defences: stop spoofing (BCP 38 ingress filtering and unicast reverse-path forwarding), close open reflectors, rate-limit responses (DNS RRL), and require validation before large replies (QUIC's 3× limit).

**Mitigation architecture.** Attack traffic is absorbed where capacity is: anycast spreads it over many sites; scrubbing centres drop malicious packets and return clean traffic (GRE tunnels or BGP diversion); remotely triggered blackhole (RTBH) and BGP FlowSpec push filters upstream; rate limiting and connection-level defences (SYN cookies, TCP Fast Open cookies, QUIC retry tokens) protect state; application-layer defences use challenges, caching and behavioural analysis. Economics favour the defender with large shared capacity and the attacker who rents botnets, which is why mitigation is mostly outsourced to a few large providers.

## Advanced: DNS security
The classic weakness is that responses are accepted if they match the query ID and, with randomisation, the source port. Kaminsky (2008) showed that an attacker can race repeatedly using made-up subdomains, poisoning the *delegation* (NS records) rather than a single name; the second lab quantifies why source-port randomisation (adding ~16 bits) was the emergency fix. **DNSSEC** signs record sets (RRSIG), publishes keys (DNSKEY) and links child to parent with DS records up to the root trust anchor; NSEC/NSEC3 prove non-existence (NSEC3 hashes names to hinder zone walking); key rollover needs care (KSK/ZSK). Costs: larger responses (amplification and fragmentation), operational complexity, and no confidentiality, which is addressed by DNS over TLS (DoT), DNS over HTTPS (DoH) and DNS over QUIC (DoQ), at the cost of moving trust to the resolver and complicating enterprise filtering.

## Advanced: TLS and the web PKI
TLS 1.3 removes static RSA key exchange and weak ciphers, mandates forward secrecy, and encrypts the certificate. Remaining threats: compromised or mis-issuing certificate authorities (mitigated by **Certificate Transparency** logs that make issuance publicly auditable, and by CAA records), stale or revoked certificates (OCSP stapling, short-lived certificates), downgrade attacks (prevented by HSTS and the TLS 1.3 downgrade sentinels), and metadata leaks (SNI, mitigated by Encrypted Client Hello). Traffic analysis can still identify websites from packet sizes and timing (website fingerprinting), motivating padding and Tor-like designs. Modern VPNs such as WireGuard use the Noise framework for a one-round-trip handshake with a minimal codebase.

## Advanced: routing security
**RPKI** lets a prefix holder publish a Route Origin Authorisation (prefix, maximum length, origin AS); routers perform route-origin validation (valid / invalid / unknown) and drop invalid routes. It stops accidental origin errors and simple hijacks, but not forged paths, and a permissive maxLength re-enables sub-prefix hijacks. **ASPA** adds authorisation of customer-provider relationships to detect route leaks; **BGPsec** signs the whole path but is deployed almost nowhere because of performance and incremental-deployment limits. Industry norms (MANRS: filtering, anti-spoofing, coordination, global validation) and IRR-based prefix filters complement the cryptographic tools. The 2008 YouTube hijack and the 2019 leak by a small provider that propagated through a larger one illustrate the stakes.

## Advanced: network defence and measurement
Firewalls enforce policy on connection state; IDS/IPS match signatures or detect anomalies (flows, DNS patterns, entropy); zero-trust designs authenticate every request rather than trusting network location. Measuring attacks uses **network telescopes** (unused address space that captures backscatter and scans), honeypots, flow records and active scans (which must follow ethical guidelines: low rate, abuse contacts, opt-out). Security of the network itself also includes DNS and BGP monitoring services, RPKI validator health, and incident response coordination through operator communities.
""")

# ---------------- Week 13 ----------------
LAB(13, "Why report medians: bootstrap confidence intervals", "RTT samples are heavy-tailed (lognormal here). Compare the sample mean and median and their bootstrap 95% confidence intervals for n = 50, 200 and 1000.", """
import random, statistics, math
def boot(data, stat, B=1000, seed=3):
    rnd = random.Random(seed); n = len(data)
    vals = sorted(stat([rnd.choice(data) for _ in range(n)]) for _ in range(B))
    return vals[int(0.025 * B)], vals[int(0.975 * B)]
rnd = random.Random(9)
print("true median RTT: 40 ms; true mean:", round(40 * math.exp(0.8 ** 2 / 2), 1), "ms")
for n in (50, 200, 1000):
    d = [rnd.lognormvariate(math.log(40), 0.8) for _ in range(n)]
    m = boot(d, statistics.mean); md = boot(d, statistics.median)
    print(f"n={n:4d}  mean {statistics.mean(d):5.1f} CI [{m[0]:5.1f},{m[1]:5.1f}] width {m[1]-m[0]:5.1f}   median {statistics.median(d):5.1f} CI [{md[0]:5.1f},{md[1]:5.1f}] width {md[1]-md[0]:5.1f}")
""")
LAB(13, "LEO geometry: visibility, slant range and pass time", "For a satellite at altitude h seen at minimum elevation ε: central angle λ = arccos(R·cosε/(R+h)) − ε, slant range d = −R·sinε + √((R·sinε)² + h² + 2Rh), maximum pass time = 2λ/ω with ω = 2π/T and T = 2π√((R+h)³/μ).", """
import math
R, mu = 6371.0, 398600.0
for h in (550, 1200):
    T = 2 * math.pi * math.sqrt((R + h) ** 3 / mu)
    for eps_deg in (25, 40, 60):
        e = math.radians(eps_deg)
        lam = math.acos(R * math.cos(e) / (R + h)) - e
        d = -R * math.sin(e) + math.sqrt((R * math.sin(e)) ** 2 + h * h + 2 * R * h)
        print(f"h={h:4d} km  min elevation {eps_deg:2d} deg: slant range {d:7.0f} km  one-way {d/299792.458*1000:5.2f} ms  max pass {2*lam/(2*math.pi/T)/60:5.1f} min")
    print(f"        orbital period {T/60:.1f} min")
""")
deepen(13, r"""
## Basics: how we know what the Internet is doing
Nobody owns a complete view of the Internet, so we infer it from probes and logs. There are two styles. **Active measurement** sends probes: `ping` measures round-trip time and loss using ICMP echo; `traceroute` sends packets with increasing TTL so that each router on the path reveals itself with a Time Exceeded message. **Passive measurement** observes real traffic: packet captures, flow records (NetFlow/IPFIX, with sampling), DNS logs, BGP route collectors.

### Reading a traceroute
Each line is one hop with three RTT samples. The RTT at a hop includes the round trip to that router *and* the time it takes the router's slow path to generate the ICMP reply, so a single high-latency hop does not mean the path is slow unless later hops are also high. Paths can differ per flow because of load balancing, and forward and reverse paths are often different (asymmetric), so RTT cannot be split into two equal halves.

### Statistics you cannot skip
Measured delays are not bell-shaped: they have a floor (propagation) and a long tail (queueing, retransmissions). Use **medians and percentiles**; report the **number of samples**; give **confidence intervals**; repeat at different times of day; use several vantage points. A single traceroute from one laptop is an anecdote, not a measurement. The first lab shows why: with a heavy tail the sample mean (here about 55 ms) is pulled far above the typical value (the median, 40 ms), and with enough samples the median's confidence interval is also the tighter one.

### Satellite networks in one page
Geostationary (GEO) satellites at 35,786 km above the equator appear fixed in the sky, which makes ground antennas simple, but one-way up-and-down propagation alone is about 240 ms, so a round trip is about 480 ms. Low Earth orbit (LEO) satellites at 500 to 1,200 km have propagation delays of only a few milliseconds up and down, but they move at 7 km/s: each is overhead for only a few minutes, so a constellation of thousands is needed, and the network must hand over users between satellites continuously. LEO systems can also relay between satellites with laser links, travelling at the speed of light in vacuum, faster than in fibre.

### Self-check
Why is `ping` to a server not exactly twice the one-way delay? Why does the mean RTT of a path with occasional 2-second spikes mislead? (Spikes dominate the mean but not the median.)
""", r"""
## Advanced: measurement platforms and pitfalls
Platforms: RIPE Atlas (thousands of probes running scheduled pings, traceroutes and DNS queries), M-Lab NDT (throughput tests with open data), CAIDA Ark and Internet Topology Data Kit, RouteViews and RIPE RIS (BGP table and update collectors), Cloudflare Radar and similar public datasets, and the mobile-app crowd-sourced tests. **Traceroute pitfalls:** per-flow load balancers make classic traceroute show routers from different paths (Paris traceroute keeps the flow identifier constant), MPLS tunnels may hide hops or show label-switched routers, ICMP is rate-limited or filtered, interfaces have different addresses from the ones that forward (alias resolution is needed to build router-level maps), and mapping IP to AS or location is error-prone (geolocation databases are accurate at country level but poor at city level). **Passive pitfalls:** sampling bias (NetFlow at 1:1000 misses small flows), encryption hides transport details, and vantage point bias (a university campus is not representative).

## Advanced: experimental method
Treat measurements as experiments: define the question, the population and the metric before collecting; record the environment (tool versions, OS, congestion control, time); randomise or interleave treatments in time to avoid confounding with diurnal load; estimate uncertainty by bootstrap or repeated runs; and publish raw data and scripts. Typical errors: comparing algorithms on different days, confusing correlation with causation (a CDN node near fast users looks 'faster'), and reporting an average over a population of highly different networks. Emulation (Mininet, ns-3, Pantheon) gives control; the real Internet gives realism; good studies use both.

## Advanced: LEO constellations as networks
A Walker-style shell places satellites in planes at fixed inclination (e.g. 53° at 550 km). The standard topology '+grid' connects each satellite to two neighbours in its orbital plane and to the nearest satellite in each adjacent plane by lasers. Routing must handle topology that changes continuously but predictably, so routes can be pre-computed from ephemeris; the shortest great-circle-like path over the constellation can beat terrestrial fibre for long distances (Handley, 2018), because light in vacuum is about 47% faster than in fibre and fibre routes are circuitous. Challenges: handovers every few minutes (affecting TCP/QUIC with RTT steps and reordering), ground-station and user-terminal scheduling, inter-satellite link capacity bottlenecks near the poles and over oceans, interference with GEO and radio astronomy, and orbital debris. GEO systems use **performance-enhancing proxies** (split TCP, spoofed ACKs) to hide the 480 ms RTT, which breaks with encrypted transports such as QUIC unless the proxy cooperates.

## Advanced: machine learning for networks
ML is used for traffic classification, anomaly detection, congestion control, video bitrate adaptation, network planning and configuration synthesis. Pitfalls specific to networks: training data from one environment rarely generalises (distribution shift), labels are scarce, adversaries can craft inputs, and operators need explanations and bounded worst cases. Practical guidance: start with simple models and strong baselines (a well-tuned heuristic often matches a deep network), evaluate on held-out *networks* and time periods, add guard rails (fall back to a safe controller when predictions are out of range), and measure inference cost against the packet-time budget.

## Advanced: IoT and low-power wide-area networks
LoRaWAN, Sigfox and NB-IoT target devices that send a few bytes occasionally for years on a battery. They trade rate (hundreds of bit/s to tens of kb/s) for range (kilometres) using long symbols and low-order modulation, operate under duty-cycle limits (often 1% in unlicensed bands), and use asymmetric designs (devices sleep, gateways listen). Design issues: security with tiny processors, over-the-air updates, collisions in ALOHA-style access as the device count rises (throughput of pure ALOHA peaks at about 18% of channel capacity), and energy-aware protocols such as CoAP and 6LoWPAN header compression.
""")
