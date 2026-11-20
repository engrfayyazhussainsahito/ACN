"""Week 14: AI Cluster Networking: RDMA, Collectives and Rail Design
Run: python3 lab.py"""


# ===== Code lab =====
import math
def ring(N, S, B=50e9, a=5e-6): return 2 * (N - 1) / N * S / B + 2 * (N - 1) * a
def rhd(N, S, B=50e9, a=5e-6): return 2 * (N - 1) / N * S / B + 2 * math.log2(N) * a
print(f"10 GB, N=64 : ring {ring(64, 10e9)*1e3:.1f} ms")
print(f"1 MB, N=1024: ring {ring(1024, 1e6)*1e3:.2f} ms, halving-doubling {rhd(1024, 1e6)*1e3:.2f} ms")
print(f"P(no ECMP collision, 8 flows / 8 links) = {math.factorial(8) / 8**8:.2%}")
W = 400e9 / 8 * 10e-6 / 1024
for p in (1e-5, 1e-4, 1e-3): print(f"go-back-N efficiency, window {W:.0f} pkts, p={p:g}: {1/(1+p*W):.1%}")


# ===== A cost calculator for collective operations =====
# Time models for the collectives used in training (per-GPU message size S, per-GPU bandwidth B, per-step latency α), then a two-level hierarchical all-reduce (fast links inside a server, rails across servers) versus one flat ring over the network.
def ring_allreduce(N, S, B, a): return 2 * (N - 1) / N * S / B + 2 * (N - 1) * a
def reduce_scatter(N, S, B, a): return (N - 1) / N * S / B + (N - 1) * a
def all_gather(N, S, B, a): return (N - 1) / N * S / B + (N - 1) * a
def all_to_all(N, S, B, a): return (N - 1) / N * S / B + (N - 1) * a
N, S, B, a = 64, 1e9, 50e9, 5e-6
for name, f in (("ring all-reduce", ring_allreduce), ("reduce-scatter", reduce_scatter), ("all-gather", all_gather), ("all-to-all", all_to_all)):
    print(f"{name:16s} N={N}, S=1 GB: {f(N, S, B, a) * 1e3:8.2f} ms")
g, B_in, B_out, S = 8, 300e9, 50e9, 10e9
print("\nhierarchical vs flat all-reduce, 10 GB gradients, 8 GPUs/server")
for M in (8, 32, 128):
    flat = ring_allreduce(g * M, S, B_out, a)
    hier = 2 * (g - 1) / g * S / B_in + ring_allreduce(M, S / g, B_out, a)
    print(f"  {g*M:5d} GPUs: flat {flat*1e3:7.1f} ms   hierarchical {hier*1e3:7.1f} ms   speed-up {flat/hier:4.1f}x")


# ===== Spraying beats hashing for elephants =====
# Eight equal elephant flows share 8 equal-cost links. Split each flow into `split` independently routed sub-flows (flowlets or packet spraying) and measure how much the busiest link exceeds the ideal load.
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


# ===== A training-step budget: compute, tensor, pipeline and data-parallel communication =====
# An illustrative model of one step of a GPT-3-scale training job (175 B parameters, 96 layers, hidden size 12,288, 3.1 M tokens per step) on 1,024 GPUs with 300 TFLOP/s effective per GPU, 300 GB/s inside a server and 50 GB/s per GPU across servers. Tensor parallelism (t) does four all-reduces per layer per microbatch, pipeline parallelism (p) sends activations between stages, data parallelism (d) all-reduces gradients. Memory limits are ignored; this shows where network time goes.
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


# ===== RoCEv2 packet overhead and line-rate packet rates =====
# RoCEv2 adds Ethernet, IP, UDP (destination port 4791), the 12-byte InfiniBand base transport header (BTH) and a 4-byte ICRC to each payload; on the wire add preamble and inter-frame gap.
overhead = 8 + 12 + 14 + 4 + 20 + 8 + 12 + 4       # preamble, IFG, Ethernet, FCS, IPv4, UDP, BTH, ICRC
print("per-packet overhead on the wire:", overhead, "bytes")
for payload in (256, 1024, 2048, 4096):
    eff = payload / (payload + overhead); pps = 400e9 / 8 / (payload + overhead)
    print(f"payload {payload:5d} B: efficiency {eff:6.1%}  line-rate packet rate at 400 Gb/s {pps/1e6:6.1f} Mpps  goodput {eff*400:6.1f} Gb/s")


# ===== PFC deadlock: finding cyclic buffer dependencies =====
# With priority flow control a queue cannot drain while the downstream queue it feeds is full and has paused it. Draw an edge X → Y when X waits for room in Y; a cycle means a possible deadlock. Up-then-down (valley-free) routing in a Clos fabric has no cycle; a detour that goes down, up and down again can.
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


# ===== A simplified DCQCN rate controller =====
# Two flows (starting at 80 and 10 Gb/s) share a 100 Gb/s link. When the aggregate exceeds capacity, flows are marked with probability proportional to their rate and cut their rate by α/2 (α is an EWMA of marks); otherwise they recover towards their target rate and then add a small increment. A fluid caricature of DCQCN: it shows the control law, not hardware timing.
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


# ===== Sizing a GPU fabric and choosing a checkpoint interval =====
# A non-blocking fat-tree built from k-port switches supports k²/2 endpoints with two tiers and k³/4 with three. Large clusters fail often; Young's formula gives the checkpoint interval T = √(2·δ·M) that minimises lost work (δ = checkpoint time, M = cluster mean time between failures).
import math
print("radix  2-tier GPUs  3-tier GPUs  3-tier switches  3-tier links")
for k in (32, 64, 128): print(f"{k:5d} {k*k//2:12d} {k**3//4:12d} {5*k*k//4:15d} {3*k**3//4:13d}")
N, mtbf_gpu_h, ckpt = 16384, 50000.0, 60.0
M = mtbf_gpu_h / N * 3600
T = math.sqrt(2 * ckpt * M)
print(f"{N} GPUs, per-GPU MTBF {mtbf_gpu_h:.0f} h -> cluster MTBF {M/3600:.2f} h")
print(f"checkpoint cost {ckpt:.0f} s: optimal interval {T/60:.1f} min, expected overhead about {math.sqrt(2 * ckpt / M):.1%}")
