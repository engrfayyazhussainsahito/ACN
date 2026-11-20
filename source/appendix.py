APPX.append(("app-a", "Appendix A: Mathematics and Units Primer", r"""
This appendix gives you every piece of mathematics the course uses, starting from scratch. If a symbol in a chapter is unfamiliar, it is defined here.

## Units, orders of magnitude and the dB scale
Networking mixes bits and bytes, so be systematic.

| Quantity | Convention | Example |
|---|---|---|
| Link rate | bits per second (b/s), decimal prefixes: 1 Gb/s = 10⁹ b/s | 100 Mb/s Ethernet |
| Data size | bytes (B); 1 KB = 1000 B, 1 KiB = 1024 B | a 1500 B packet |
| Conversion | 8 bits = 1 byte | 1 Gb/s = 125 MB/s |
| Time | s, ms = 10⁻³ s, µs = 10⁻⁶ s, ns = 10⁻⁹ s | light crosses 1 km of fibre in 5 µs |

!! Worked example: how long does a 1500 B packet take to transmit on a 1 Gb/s link? 1500 × 8 = 12,000 bits; 12,000 / 10⁹ = 12 µs.

Ratios of power are often written in decibels: dB = 10·log₁₀(P₂/P₁). Useful anchors: +3 dB ≈ ×2, +10 dB = ×10, +20 dB = ×100, −3 dB ≈ ×½. Absolute power is quoted in dBm: dBm = 10·log₁₀(P in milliwatts), so 0 dBm = 1 mW and 20 dBm = 100 mW. Because logarithms turn products into sums, a radio link budget is simply additions: received (dBm) = transmitted (dBm) + gains (dB) − losses (dB).

## Logarithms, exponentials and sums
log₂ x answers 'how many times can I halve x?'. log₂ 1024 = 10, log₂ 10⁶ ≈ 19.9, and log₂ 10⁹ ≈ 29.9. Changing base: log₂ x = ln x / ln 2 = 3.32 · log₁₀ x. The geometric series is used constantly (window growth, backoff, queueing):

$ 1 + r + r² + … + rⁿ = (1 − rⁿ⁺¹)/(1 − r),    and for |r| < 1:  Σ rⁿ = 1/(1 − r)

!! Worked example: slow start doubles the window each RTT, so after n RTTs it has sent 1 + 2 + 4 + … + 2ⁿ⁻¹ = 2ⁿ − 1 segments. The harmonic number Hₙ = 1 + 1/2 + … + 1/n ≈ ln n + 0.577 appears in Zipf caching.

## Probability from the beginning
A random variable X takes values with some probabilities. Its expectation (mean) is E[X] = Σ x·P(X = x), and its variance is Var(X) = E[X²] − (E[X])². Two random variables are independent if knowing one tells you nothing about the other, and then the variances of their sum add. For n independent samples the sample mean has standard deviation σ/√n, which is why 4× more measurements halve the error.

Four distributions run through networking:

| Distribution | Meaning | Key formulas |
|---|---|---|
| Bernoulli(p) | one packet is lost with probability p | mean p |
| Geometric | number of tries until the first success | P(k) = (1−p)ᵏ⁻¹p, mean 1/p |
| Poisson(λ) | number of arrivals in a unit time | P(k) = e^(−λ)·λᵏ / k!, mean λ |
| Exponential(λ) | time between Poisson arrivals | P(X > t) = e^(−λt), mean 1/λ |

The exponential distribution is memoryless: P(X > s + t | X > s) = P(X > t). That is why M/M/1 queues are tractable: the remaining service time never depends on how long the packet has already been served. Real traffic is often heavy-tailed (a few huge values, e.g. Pareto), where means can be dominated by rare events and percentiles are more informative.

!! Worked example: a link drops each packet independently with p = 1%. The expected number of packets until the first loss is 1/p = 100, and the chance that 100 packets contain no loss is 0.99¹⁰⁰ = 36.6%.

## Statistics for measurement
A percentile pₓ is the value below which x% of samples fall. The median is p50; p99 is the tail. A 95% confidence interval for a mean is x̄ ± 1.96·s/√n when samples are independent. Always report the number of runs, seeds, and the interval, not just a single number.

## Optimisation basics
A linear program maximises cᵀx subject to Ax ≤ b and x ≥ 0. Traffic engineering (Week 15) is such a problem: the variables are flow amounts on paths, and the constraints are link capacities. Convex problems have no spurious local optima, which is why congestion control can be analysed as distributed optimisation (Weeks 4 and 5). Gradient methods move in the direction that improves the objective; additive increase and multiplicative decrease can be seen as such a method.

## Information theory in one page
The entropy of a source with symbol probabilities pᵢ is H = −Σ pᵢ log₂ pᵢ bits per symbol. A fair coin has H = 1 bit; a coin that lands heads 90% of the time has H = 0.47 bits. Entropy is the lower bound on average code length. Shannon's channel capacity C = B·log₂(1 + SNR) is the highest error-free rate over a noisy channel of bandwidth B; it is the foundation of Week 10.

## Big-O notation
O(f(n)) says an algorithm's cost grows no faster than a constant times f(n). Dijkstra on E edges and V vertices costs O(E log V); a lookup in Chord costs O(log N); a naive scan of a forwarding table costs O(N). When N is a million, log₂ N ≈ 20, so the difference is dramatic.
"""))
APPX.append(("app-b", "Appendix B: Networking Fundamentals (from zero)", r"""
Start here if you have not taken an undergraduate networking course, or if you need a refresher. Everything in the advanced chapters builds on these ideas.

## What a network is
A network moves bits between computers. Data is cut into packets, each with a header (who it is for, where it came from, how to reassemble it) and a payload. Routers read the header and forward the packet toward its destination. Because many conversations share the same links, packets from different flows are interleaved (statistical multiplexing), which is efficient but means packets can queue, be delayed, be reordered, or be dropped.

## The layered model
Each layer uses the services of the one below and hides its details from the one above.

| Layer | Job | Examples | Unit |
|---|---|---|---|
| Application | what users and programs want | HTTP, DNS, SMTP, QUIC streams | message |
| Transport | process-to-process delivery, reliability, congestion control | TCP, UDP, QUIC | segment/datagram |
| Network | host-to-host delivery across networks, routing | IP, ICMP, BGP | packet |
| Link | delivery over one hop | Ethernet, Wi-Fi, PPP | frame |
| Physical | signals on a medium | copper, fibre, radio | bits |

Encapsulation: the application data is wrapped in a TCP header, then an IP header, then an Ethernet header and trailer. The receiver strips them in reverse order.

## Addresses
- **MAC address**: 48-bit hardware address valid on one link, written like `3c:22:fb:12:34:56`.
- **IPv4 address**: 32 bits, written as four decimal bytes, e.g. `192.168.10.37`. An address has a network part and a host part. CIDR notation `/n` says the first n bits are the network prefix.
- **IPv6 address**: 128 bits written in hexadecimal groups, e.g. `2001:db8::1`.
- **Port**: 16-bit number identifying an application on a host; TCP/UDP connections are identified by the 5-tuple (source IP, source port, destination IP, destination port, protocol).

### Subnetting by example
For `192.168.10.0/26`: the prefix is 26 bits, so the host part is 32 − 26 = 6 bits, giving 2⁶ = 64 addresses. The netmask is `255.255.255.192`. The first address (`.0`) is the network address and the last (`.63`) is the broadcast address, so 62 are usable for hosts.

!! Worked example: a department needs 500 hosts. 2⁹ = 512 addresses minus 2 reserved leaves 510 usable, so a /23 (32 − 9 = 23) is the smallest block that works.

Forwarding uses longest-prefix match: if a table contains 10.0.0.0/8 and 10.1.0.0/16, a packet to 10.1.2.3 matches both and the longer /16 wins. A default route 0.0.0.0/0 matches everything and has the lowest priority.

## How a packet gets from A to B
1. Host A checks whether the destination is in its own subnet (using its netmask). If so it sends directly; if not it sends to its default gateway.
2. To send on the local link, A finds the next hop's MAC address using ARP (IPv6 uses neighbour discovery).
3. Each router looks up the destination in its forwarding table, decrements the TTL (hop limit), and forwards. If TTL reaches 0, the router drops the packet and sends an ICMP Time Exceeded message; `traceroute` exploits exactly this.
4. The destination host passes the payload to the transport layer based on the protocol and port.

## UDP and TCP
**UDP** adds only ports and a checksum: no connection, no reliability. **TCP** provides a reliable, ordered byte stream. Key mechanisms:

- **Handshake:** SYN, SYN-ACK, ACK establishes initial sequence numbers (one round trip before data).
- **Sequence and ACK numbers** count bytes; the receiver acknowledges the next byte it expects. Lost data is detected by timeout or by duplicate ACKs and retransmitted.
- **Flow control:** the receiver advertises a window so the sender cannot overrun its buffer.
- **Congestion control:** the sender limits its window to what the network can carry (Weeks 4 and 5).
- **Teardown:** FIN/ACK in each direction; the closer lingers in TIME_WAIT for 2×MSL.

The maximum segment size (MSS) is usually 1460 bytes on Ethernet (1500-byte MTU minus 40 bytes of IPv4 and TCP headers).

## Name resolution and the web
DNS maps names such as `www.example.com` to IP addresses by asking a recursive resolver, which walks the hierarchy (root, `.com`, `example.com`) and caches the answer for the record's TTL. HTTP is a request/response protocol: HTTP/1.1 sends requests over TCP, HTTP/2 multiplexes streams over one TCP connection, and HTTP/3 uses QUIC (Week 6). TLS encrypts and authenticates the connection.

## Network address translation and middleboxes
NAT lets many hosts with private addresses (10/8, 172.16/12, 192.168/16) share one public address by rewriting ports and remembering the mapping. Firewalls, load balancers and proxies are other middleboxes. They are useful but break the simple end-to-end model, a recurring theme in this course.

## Putting numbers on it: the four delays
A packet's delay at each hop is the sum of processing, queueing, transmission (L/R) and propagation (distance/speed). Over a long path propagation dominates; over a busy link queueing dominates; for big files transmission dominates. Chapter 1 builds the model carefully.

## Self-check
Answer without looking: What is in the 5-tuple? Why can a /24 not hold 256 hosts? Which layer retransmits lost packets in TCP? What does a router do with the TTL? If you struggle, re-read the section above before starting Week 1.
"""))
APPX.append(("app-c", "Appendix C: Tools and Lab Environment", r"""
All labs run on Linux (a VM or WSL2 is fine). The Python labs need only Python 3.10+. The emulation labs need Mininet.

## Set-up checklist
```
sudo apt update
sudo apt install -y python3 python3-pip git iperf3 tcpdump wireshark tshark mtr-tiny dnsutils
sudo apt install -y mininet openvswitch-switch      # emulation labs
pip install scapy matplotlib numpy                   # optional, for packet crafting and plots
```

## Measuring: the everyday commands
| Task | Command | What to read |
|---|---|---|
| Reachability, RTT | `ping -c 20 example.com` | min/avg/max/mdev and loss |
| Path | `mtr -rwz example.com` | per-hop loss and latency |
| DNS | `dig +trace www.example.com` | the delegation chain and TTLs |
| TCP internals | `ss -ti dst example.com` | cwnd, rtt, retransmits, pacing rate |
| Throughput | `iperf3 -s` on one side, `iperf3 -c HOST -t 30 -P 4 -C bbr` on the other | goodput, retransmissions |
| Capture | `sudo tcpdump -i eth0 -nn -w out.pcap 'tcp port 443'` | open `out.pcap` in Wireshark |

Useful Wireshark display filters: `tcp.analysis.retransmission`, `tcp.analysis.zero_window`, `dns`, `quic`, `tls.handshake.type == 1` (ClientHello), `ip.ttl < 5`.

## Shaping the network with tc and netem
Emulate a 50 Mb/s link with 40 ms of added delay and 1% loss on interface `eth0`:
```
sudo tc qdisc add dev eth0 root handle 1: netem delay 40ms loss 1%
sudo tc qdisc add dev eth0 parent 1:1 handle 10: tbf rate 50mbit burst 32kbit latency 400ms
tc qdisc show dev eth0          # inspect
sudo tc qdisc del dev eth0 root # remove when finished
```
The `tbf` queue sets the bottleneck rate and its `latency` parameter bounds the buffer, which is exactly the buffer-size variable in the congestion-control experiments of Weeks 4 and 5.

Switch congestion-control algorithms: `sysctl net.ipv4.tcp_available_congestion_control`, `sudo modprobe tcp_bbr`, `sudo sysctl -w net.ipv4.tcp_congestion_control=bbr`, or per-flow with `iperf3 -C`.

## Mininet in five minutes
Mininet builds a virtual network of hosts and switches on one machine using Linux namespaces. Try:
```
sudo mn --topo single,3 --test pingall
sudo mn --topo tree,depth=2,fanout=2 --link tc,bw=10,delay=10ms
mininet> h1 iperf3 -s &
mininet> h2 iperf3 -c h1 -t 10
```
For custom topologies write a Python script (see `labs/mininet/dumbbell_cc.py`). Always run `sudo mn -c` to clean up after a crash.

## ns-3 in brief
ns-3 is a discrete-event packet-level simulator written in C++ with Python bindings. After downloading a release: `./ns3 configure --enable-examples --enable-tests && ./ns3 build && ./ns3 run tcp-variants-comparison`. Use it when you need thousands of nodes, exact reproducibility, or protocols the kernel does not implement. Mininet runs real kernel code and is better for realism; ns-3 is better for scale.

## Crafting packets with scapy
```
from scapy.all import IP, ICMP, sr1
reply = sr1(IP(dst="1.1.1.1", ttl=3) / ICMP(), timeout=2, verbose=0)
print(reply.src if reply else "no reply")     # the router 3 hops away answers with Time Exceeded
```

## Lab rules
Do experiments that generate attack-like traffic (floods, reflection, spoofing) only inside an isolated virtual network that you own. Never aim them at real hosts. When measuring the Internet, send low-rate probes, respect rate limits, and follow your institution's acceptable-use policy.

## Reporting results
For every experiment record: topology, link rates and delays, buffer sizes, congestion control, tool versions, number of runs and random seeds. Plot medians with 10th/90th percentile bands or 95% confidence intervals, and keep the raw data.
"""))
APPX.append(("app-d", "Appendix D: Study Guide and Course Policies", r"""
## How to use this course on your own
1. Read the **Basics** section of the chapter first. If it feels easy, skim it; if not, also read Appendix A or B.
2. Read the core sections and work each worked example on paper before reading the answer.
3. Run every code lab, then change one parameter and predict the effect before running it again.
4. Try the interactive demos to build intuition for how quantities scale.
5. Do the exercises, then compare with the solution. Re-attempt any you missed a week later.
6. Read the **Advanced** section and the paper guide; read at least the essential papers fully.
7. Do the programming assignment: it is the part that turns knowledge into skill.

## Suggested weekly rhythm (about 9 to 10 hours)
Two lectures or reading sessions (3 hours), one lab session (2 hours), exercises (2 hours), paper reading (1 hour), assignment work (2 hours).

## Assessment (as a formal course)
| Component | Weight | Notes |
|---|---|---|
| Problem sets / labs | 25% | one per two weeks, from the exercises and assignments |
| Midterm (Week 8) | 20% | Weeks 1 to 7, 75 minutes |
| Paper critiques | 15% | one page each, using the paper guide template |
| Project | 25% | proposal Week 3, report and 10-minute talk Week 16 |
| Final exam | 15% | cumulative, weighted to Weeks 9 to 15 |

## Paper critique template
State the problem and claim in two sentences; the method; the main evidence (which figure supports which claim); one baseline that is missing; one threat to validity; one follow-up experiment you would run.

## Academic integrity
Discussion of ideas is encouraged; submit your own code and writing, cite sources, and report all experimental settings honestly. Do not present generated or copied results as your own measurements.

## Where to go next
Read recent SIGCOMM, NSDI and CoNEXT proceedings; join the IETF mailing lists for QUIC, TCPM and BGP operations; reproduce a figure from a paper and publish the artefact. The best way to know whether you have mastered this material is to explain a protocol's design to someone else, including why each simpler alternative fails.
"""))
