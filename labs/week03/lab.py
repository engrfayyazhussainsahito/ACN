"""Week 3: Routing: Link-State, Distance-Vector and BGP
Run: python3 lab.py"""


# ===== Code lab =====
import heapq
G = {"A": {"B": 2, "C": 5}, "B": {"A": 2, "C": 1, "D": 4}, "C": {"A": 5, "B": 1, "D": 1}, "D": {"B": 4, "C": 1}}
def dijkstra(G, s):
    dist, prev, pq = {s: 0}, {}, [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v, w in G[u].items():
            if d + w < dist.get(v, 1e9): dist[v], prev[v] = d + w, u; heapq.heappush(pq, (d + w, v))
    return dist, prev
dist, prev = dijkstra(G, "A")
print(dist)
path, n = ["D"], "D"
while n != "A": n = prev[n]; path.append(n)
print("A->D:", " ".join(reversed(path)))

def bellman_ford(nodes, edges, src):
    d = {n: float("inf") for n in nodes}; d[src] = 0
    for _ in range(len(nodes) - 1):
        for u, v, w in edges:
            if d[u] + w < d[v]: d[v] = d[u] + w
            if d[v] + w < d[u]: d[u] = d[v] + w
    return d
print(bellman_ford("xyz", [("x", "y", 2), ("y", "z", 3), ("x", "z", 7)], "x"))


# ===== Distance-vector count-to-infinity =====
# Replay the classic two-router failure and measure how many exchanges it takes with and without poisoned reverse.
INF = 16
def count_to_infinity(poison):
    a, b = 2, INF          # B just lost its direct route to C (cost 1); A still believes 'B can reach C' (cost 2)
    msgs = 0
    while not (a >= INF and b >= INF):
        # A advertises its cost to B; with poison reverse A reports INF because A's next hop is B
        adv_a = INF if poison else a
        nb = min(INF, adv_a + 1); msgs += 1
        if nb == b and poison: break
        b = nb
        adv_b = INF if poison else b
        a = min(INF, adv_b + 1); msgs += 1
    return a, b, msgs
for poison in (False, True):
    print("poisoned reverse" if poison else "plain DV         ", "-> final costs (A,B) and messages:", count_to_infinity(poison))


# ===== The BGP decision process =====
# A toy router with candidate routes to one prefix. BGP prefers (1) highest local preference, (2) shortest AS path, (3) lowest origin type, (4) lowest MED (same neighbour AS), (5) eBGP over iBGP, (6) lowest IGP cost to next hop, (7) lowest router ID.
routes = [
    dict(via="provider-1", lp=100, aspath=[701, 3356, 15169], origin=0, med=0, ebgp=True, igp=10, rid="1.1.1.1"),
    dict(via="peer-1",     lp=200, aspath=[2914, 15169],       origin=0, med=0, ebgp=True, igp=20, rid="2.2.2.2"),
    dict(via="customer-1", lp=300, aspath=[64500, 64501, 64502, 15169], origin=0, med=0, ebgp=True, igp=5, rid="3.3.3.3"),
]
def key(r): return (-r["lp"], len(r["aspath"]), r["origin"], r["med"], not r["ebgp"], r["igp"], r["rid"])
for r in sorted(routes, key=key): print(f"{r['via']:11s} lp={r['lp']} path_len={len(r['aspath'])}")
print("best:", min(routes, key=key)["via"], "(local-pref encodes business policy and overrides path length)")


# ===== Valley-free path checker =====
# Check whether an AS path respects Gao-Rexford export rules, given relationship labels between consecutive ASes.
# 'c2p' = customer->provider (going up), 'p2p' = peer, 'p2c' = provider->customer (going down)
def valley_free(rels):
    phase = 0                      # 0 = climbing, 1 = crossed the single peer link, 2 = descending
    for r in rels:
        if r == "c2p":
            if phase != 0: return False
        elif r == "p2p":
            if phase != 0: return False
            phase = 1
        else: phase = 2
    return True
tests = {"up,peer,down": ["c2p", "p2p", "p2c"], "up,up,down": ["c2p", "c2p", "p2c"], "down,up (valley)": ["p2c", "c2p"], "two peers": ["p2p", "p2p"]}
for name, rels in tests.items(): print(f"{name:18s} valley-free: {valley_free(rels)}")
