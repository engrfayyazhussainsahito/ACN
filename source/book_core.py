# executed inside build.py (shares globals). Provides deepen(), LAB(), APPX and post_book().
import json
APPX = []
LABS = {}
CSS_EXTRA += (".toc{background:#fff;border:1px solid #e3ddd0;border-radius:8px;padding:10px 16px;margin:1em 0;font:14px/1.9 system-ui}.toc a{display:inline-block;margin-right:14px;color:#1f6f78;text-decoration:none}"
              ".tw{overflow-x:auto}h3{margin-top:1.6em;color:#1f6f78}h2.lv-b::before,h2.lv-a::before{font:700 11px system-ui;letter-spacing:.06em;padding:3px 8px;border-radius:10px;margin-right:10px;vertical-align:middle;color:#fff}"
              "h2.lv-b::before{content:'BASICS';background:#6a9955}h2.lv-a::before{content:'ADVANCED';background:#c0562b}ul,ol{padding-left:1.4em}li{margin:.25em 0}")

def LAB(n, title, desc, code): LABS.setdefault(n, []).append((title, desc, code.strip("\n")))
def deepen(n, prime, adv):
    w = BYN[n]; w["body"] = prime.strip() + "\n\n" + w["body"]
    tail = adv.strip() + ("\n\n[[lab:%d]]" % n if LABS.get(n) else "")
    mk = "\n\n## Programming assignment"
    w["body"] = w["body"].replace(mk, "\n\n" + tail + mk, 1) if mk in w["body"] else w["body"] + "\n\n" + tail

MININET_DUMBBELL = '''#!/usr/bin/env python3
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
'''
MININET_FATTREE = '''#!/usr/bin/env python3
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
'''
PRINT_CSS = ("@page{size:A4;margin:17mm 15mm;@bottom-center{content:counter(page);font:9pt sans-serif;color:#888}}body{display:block;background:#fff;font:10.3pt/1.5 'DejaVu Serif',Georgia,serif}"
             "aside,.pn,button,.toc,footer{display:none}main{padding:0;max-width:none}h1{font-size:21pt}h2{break-after:avoid;font-size:14pt}h3{break-after:avoid}pre{white-space:pre-wrap;font-size:8pt;padding:8px}"
             "figure,.box,.note,.eq,details,table,.out{break-inside:avoid}details{display:block}details>p{display:block}svg{max-width:100%;height:auto}.chap{break-before:page}.cover{text-align:center;margin-top:80mm}.cover h1{font-size:30pt}")

def to_pdf(body, title, path):
    import weasyprint
    body = re.sub(r'<div class="demo"[^>]*></div>', '<p class="note">Interactive demo: available on the website.</p>', body)
    body = re.sub(r'<div class="toc">.*?</div>', "", body, flags=re.S).replace("<details>", "<details open>")
    css = open(OUT + "/assets/style.css", encoding="utf-8").read()
    weasyprint.HTML(string=f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{css}{PRINT_CSS}</style></head><body><main>{body}</main></body></html>").write_pdf(path)

def post_book():
    for slug, title, text in APPX: page(slug + ".html", title, slug, f"<h1>{html.escape(title)}</h1>" + md(text))
    os.makedirs(OUT + "/labs/mininet", exist_ok=True)
    open(OUT + "/labs/mininet/dumbbell_cc.py", "w").write(MININET_DUMBBELL); open(OUT + "/labs/mininet/fattree.py", "w").write(MININET_FATTREE)
    idx = ["# Labs\nEvery week has a folder with `lab.py` (runs with plain Python 3.10+, no packages), `lab.ipynb` (the same code as a Jupyter notebook) and a README with the assignment. `mininet/` holds two emulation labs that need Linux, root and Mininet.\n\n"]
    for w in ALL:
        n = w["n"]; codes = ([("Code lab", "", w["code"])] if w["code"] else []) + LABS.get(n, [])
        if not codes: continue
        d = f"{OUT}/labs/week{n:02d}"; os.makedirs(d, exist_ok=True)
        py = f'"""Week {n}: {w["title"]}\nRun: python3 lab.py"""\n'
        cells = [{"cell_type": "markdown", "metadata": {}, "source": [f"# Week {n}: {w['title']}\n", "Run the cells in order, then change one parameter at a time."]}]
        for t, desc, c in codes:
            py += f"\n\n# ===== {t} =====\n" + (("# " + desc.replace("\n", " ") + "\n") if desc else "") + c + "\n"
            cells += [{"cell_type": "markdown", "metadata": {}, "source": [f"## {t}\n", desc]}, {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": c.splitlines(True)}]
        open(d + "/lab.py", "w", encoding="utf-8").write(py)
        json.dump({"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}, "nbformat": 4, "nbformat_minor": 5}, open(d + "/lab.ipynb", "w", encoding="utf-8"))
        open(d + "/README.md", "w", encoding="utf-8").write(f"# Week {n}: {w['title']}\n\n## Assignment\n{ASSIGN.get(n, 'See the chapter.')}\n\n## Files\n- `lab.py`: runnable labs from the chapter\n- `lab.ipynb`: same code as a notebook\n")
        idx.append(f"- `week{n:02d}/`: {w['title']}\n")
    open(OUT + "/labs/README.md", "w").write("".join(idx))
    os.makedirs(OUT + "/pdf", exist_ok=True)
    try:
        for w in ALL: to_pdf(PB[w["n"]], f"Week {w['n']}: {w['title']}", f"{OUT}/pdf/week-{w['n']:02d}.pdf")
        toc = "<ol>" + "".join(f"<li>Week {w['n']}: {html.escape(w['title'])}</li>" for w in ALL) + "".join(f"<li>Appendix: {html.escape(t)}</li>" for _, t, _ in APPX) + "</ol>"
        book = f'<div class="cover"><h1>Advanced Computer Networks</h1><p class="lead">A self-contained graduate course: notes, derivations, labs and exercises</p><p>Open course · CC BY 4.0</p></div><section class="chap"><h1>Contents</h1>{toc}</section>'
        book += "".join(f'<section class="chap">{PB[w["n"]]}</section>' for w in ALL)
        book += "".join(f'<section class="chap"><h1>{html.escape(t)}</h1>{md(x)}</section>' for _, t, x in APPX)
        to_pdf(book, "Advanced Computer Networks: complete notes", OUT + "/pdf/ACN-complete-notes.pdf")
        ref = "<h1>Reference cards</h1><h2>Key relations by week</h2>" + md("[[sheet2]]") + "<h2>Glossary</h2><dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in sorted(GL.items())) + "</dl><h2>Reading list</h2>" + "".join(f"<h3>Week {w['n']}: {html.escape(w['title'])}</h3><ul>" + "".join(f"<li>{html.escape(r)}</li>" for r in w["rd"]) + "</ul>" for w in ALL)
        to_pdf(ref, "ACN reference cards", OUT + "/pdf/ACN-reference-cards.pdf"); pdf_ok = True
    except Exception as e:
        print("PDF generation failed:", e); pdf_ok = False
    rows = "".join(f'<tr><td><a href="pdf/week-{w["n"]:02d}.pdf">Week {w["n"]}: {html.escape(w["title"])}</a></td><td>' + (f'<a href="labs/week{w["n"]:02d}/lab.py">lab.py</a> · <a href="labs/week{w["n"]:02d}/lab.ipynb">notebook</a>' if (w["code"] or LABS.get(w["n"])) else "-") + "</td></tr>" for w in ALL)
    dl = ('<h1>Downloads</h1><p class="lead">Everything needed to study offline.</p>' + (('<ul><li><a href="pdf/ACN-complete-notes.pdf"><b>Complete notes (PDF)</b></a>: every chapter and appendix in one book</li><li><a href="pdf/ACN-reference-cards.pdf"><b>Reference cards (PDF)</b></a>: formulas, glossary and reading list</li><li><a href="labs/mininet/dumbbell_cc.py">Mininet: CUBIC vs BBR dumbbell</a> and <a href="labs/mininet/fattree.py">fat-tree topology</a> (need Linux + Mininet)</li></ul>') if pdf_ok else "<p>PDFs were not generated in this build.</p>") +
          '<h2>Per-week PDFs and lab files</h2><div class="tw"><table><tr><th>Chapter PDF</th><th>Lab files</th></tr>' + rows + "</table></div>")
    page("downloads.html", "Downloads", "dl", dl)
