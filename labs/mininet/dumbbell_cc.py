#!/usr/bin/env python3
"""Dumbbell: h1,h2 -- s1 ==bottleneck== s2 -- h3,h4. CUBIC (h1->h3) competes with BBR (h2->h4).
Needs Linux, root, Mininet, iperf3 and the tcp_bbr module (sudo modprobe tcp_bbr).
Usage: sudo python3 dumbbell_cc.py --bw 50 --delay 20ms --buf 100 --secs 30
NOTE: provided for the course labs; not executed in the build environment."""
import argparse, json
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import setLogLevel

class Dumbbell(Topo):
    def build(self, bw=50, delay="20ms", buf=100):
        s1, s2 = self.addSwitch("s1"), self.addSwitch("s2")
        for i in (1, 2): self.addLink(self.addHost(f"h{i}"), s1, cls=TCLink, bw=1000, delay="1ms")
        for i in (3, 4): self.addLink(self.addHost(f"h{i}"), s2, cls=TCLink, bw=1000, delay="1ms")
        self.addLink(s1, s2, cls=TCLink, bw=bw, delay=delay, max_queue_size=buf)

def goodput(out):
    return json.loads(out)["end"]["sum_received"]["bits_per_second"] / 1e6

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bw", type=float, default=50); ap.add_argument("--delay", default="20ms")
    ap.add_argument("--buf", type=int, default=100); ap.add_argument("--secs", type=int, default=30)
    a = ap.parse_args(); setLogLevel("warning")
    net = Mininet(topo=Dumbbell(a.bw, a.delay, a.buf), switch=OVSBridge, controller=None, link=TCLink); net.start()
    h1, h2, h3, h4 = (net.get(f"h{i}") for i in range(1, 5))
    h3.cmd("iperf3 -s -D"); h4.cmd("iperf3 -s -p 5202 -D")
    h1.sendCmd(f"iperf3 -c {h3.IP()} -t {a.secs} -C cubic -J")
    h2.sendCmd(f"iperf3 -c {h4.IP()} -p 5202 -t {a.secs} -C bbr -J")
    c, b = goodput(h1.waitOutput()), goodput(h2.waitOutput())
    print(f"CUBIC {c:.1f} Mb/s   BBR {b:.1f} Mb/s   (bottleneck {a.bw} Mb/s, buffer {a.buf} pkts, one-way {a.delay})")
    net.stop()
