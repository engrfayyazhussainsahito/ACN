#!/usr/bin/env python3
"""k-ary fat-tree topology for Mininet (k even). Hosts: k^3/4, switches: 5k^2/4.
Loops exist by design: use a multipath-aware controller (Ryu/ONOS with ECMP) or enable STP.
Usage: sudo mn --custom fattree.py --topo fattree,4 --controller remote
NOTE: topology only; provided for the course labs and not executed in the build environment."""
from mininet.topo import Topo

class FatTree(Topo):
    def build(self, k=4):
        half, n = k // 2, [0]
        def sw(name): n[0] += 1; return self.addSwitch(name, dpid=f"{n[0]:016x}")
        cores = [sw(f"c{i}") for i in range(half * half)]
        for p in range(k):
            aggs = [sw(f"a{p}x{i}") for i in range(half)]; edges = [sw(f"e{p}x{i}") for i in range(half)]
            for i, a in enumerate(aggs):
                for j in range(half): self.addLink(a, cores[i * half + j])
                for e in edges: self.addLink(a, e)
            for i, e in enumerate(edges):
                for h in range(half): self.addLink(e, self.addHost(f"h{p}x{i}x{h}"))

topos = {"fattree": FatTree}
