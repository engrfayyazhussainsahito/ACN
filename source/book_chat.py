# Course chatbot: build-time indexer + browser retrieval engine. Executed inside build.py (shares globals).
import json as _json

CSS_EXTRA += """
.acnc-fab{position:fixed;right:18px;bottom:18px;z-index:50;background:#1f6f78;color:#fff;border:0;border-radius:26px;padding:12px 18px;font:600 15px system-ui;box-shadow:0 4px 14px rgba(0,0,0,.25);cursor:pointer}
.acnc-fab:hover{background:#185a62}
.acnc{display:none;position:fixed;right:18px;bottom:76px;z-index:51;width:400px;max-width:calc(100vw - 24px);height:600px;max-height:calc(100vh - 100px);background:#fff;border:1px solid #cfc7b6;border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.28);flex-direction:column;overflow:hidden;font:14px/1.5 system-ui}
.acnc.open{display:flex}
.acnc.page{display:flex;position:static;width:100%;max-width:none;height:70vh;min-height:480px;box-shadow:none;margin:14px 0}
.acnc-h{background:#1f6f78;color:#fff;padding:9px 12px;display:flex;align-items:center;gap:8px}
.acnc-h b{flex:1;font-size:15px}.acnc-h button{background:transparent;border:0;color:#fff;font-size:13px;cursor:pointer;padding:4px 6px;border-radius:5px}.acnc-h button:hover{background:rgba(255,255,255,.2)}
.acnc-m{flex:1;overflow-y:auto;padding:12px;background:#faf7f2}
.acnc-b{max-width:92%;margin:0 0 10px;padding:9px 12px;border-radius:12px;word-wrap:break-word}
.acnc-b.u{background:#1f6f78;color:#fff;margin-left:auto;border-bottom-right-radius:3px}
.acnc-b.b{background:#fff;border:1px solid #e3ddd0;border-bottom-left-radius:3px}
.acnc-b p{margin:.3em 0}.acnc-b mark{background:#fde9a8;padding:0 2px;border-radius:2px}
.acnc-src{font-size:12px;color:#666;margin-top:6px}.acnc-src a,.acnc-b a{color:#1f6f78}
.acnc-more{margin:6px 0 0;padding-left:1.2em;font-size:13px}.acnc-more li{margin:.2em 0}
.acnc-b details{margin-top:6px;background:#f5f1e8;border:1px solid #e3ddd0;border-radius:6px;padding:4px 10px}
.acnc-chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 10px}
.acnc-chip{background:#fff;border:1px solid #1f6f78;color:#1f6f78;border-radius:14px;padding:4px 10px;font:13px system-ui;cursor:pointer}.acnc-chip:hover{background:#e6f2f3}
.acnc-f{display:flex;gap:6px;padding:8px;border-top:1px solid #e3ddd0;background:#fff}
.acnc-f textarea{flex:1;resize:none;border:1px solid #cfc7b6;border-radius:8px;padding:7px 9px;font:14px system-ui;height:42px}
.acnc-f button{background:#1f6f78;color:#fff;border:0;border-radius:8px;padding:0 14px;font:600 14px system-ui;cursor:pointer}
.acnc-set{display:none;padding:10px 12px;background:#f5f1e8;border-bottom:1px solid #e3ddd0;font-size:12.5px}.acnc-set.open{display:block}
.acnc-set input{width:100%;margin:2px 0 6px;padding:5px;border:1px solid #cfc7b6;border-radius:5px;font:12.5px system-ui}
.acnc-set label.acnc-r{display:block;margin:3px 0;cursor:pointer}.acnc-set i{color:#777;font-style:normal}.acnc-set select{padding:4px;border:1px solid #cfc7b6;border-radius:5px}.acnc-set p{margin:6px 0;color:#555}.acnc-b sup a{text-decoration:none;font-weight:600}
@media(max-width:600px){.acnc{right:6px;bottom:70px;height:calc(100vh - 90px)}}
"""

CHAT_JS = open(os.path.join(_B, 'chatbot.src.js'), encoding='utf-8').read()

open(OUT + "/assets/chatbot.js", "w", encoding="utf-8").write(CHAT_JS)
_proxy = os.environ.get("ACN_PROXY_URL", "").strip()
_backend = os.environ.get("ACN_DEFAULT_BACKEND", "proxy" if _proxy else "extractive").strip()
open(OUT + "/assets/chatbot-config.js", "w", encoding="utf-8").write("// Site-wide chatbot defaults. backend: extractive | proxy | webllm | openai. Visitors can override in the AI mode panel.\nwindow.ACN_RAG_CONFIG=" + _json.dumps({"backend": _backend, "proxyUrl": _proxy, "quality": "fast"}) + ";\n")
os.makedirs(OUT + "/worker", exist_ok=True)
open(OUT + "/worker/acn-rag-proxy.js", "w", encoding="utf-8").write(open(os.path.join(_B, "acn-rag-proxy.js"), encoding="utf-8").read())
open(OUT + "/worker/wrangler.toml", "w").write('name = "acn-rag-proxy"\nmain = "acn-rag-proxy.js"\ncompatibility_date = "2024-11-01"\n\n[vars]\n# Comma-separated list of sites allowed to call this proxy, e.g. "https://yourname.github.io". "*" allows any site (not recommended).\nALLOWED_ORIGINS = "*"\nANTHROPIC_MODEL = "claude-haiku-5-5"\nRATE_LIMIT = "20"\nMAX_TOKENS = "700"\n# Set the key as a secret, never in this file:  wrangler secret put ANTHROPIC_API_KEY\n')
open(OUT + "/worker/README.md", "w", encoding="utf-8").write("""# ACN RAG proxy (Cloudflare Worker)

The chatbot retrieves passages from the course in the browser and, in *cloud AI* mode, sends the question plus those passages to this proxy, which asks a Claude model to write a grounded, cited answer and streams it back. The proxy exists so your API key never appears on the public site.

## Deploy (about 5 minutes)
1. Install Node.js, then `npm install -g wrangler` and `wrangler login`.
2. In this folder: `wrangler secret put ANTHROPIC_API_KEY` (paste your key when asked).
3. Edit `wrangler.toml`: set `ALLOWED_ORIGINS` to your site, for example `https://yourname.github.io` (several origins can be comma-separated).
4. `wrangler deploy`. Note the URL it prints, such as `https://acn-rag-proxy.yourname.workers.dev`.
5. Point the site at it, either by rebuilding with `ACN_PROXY_URL=https://acn-rag-proxy.yourname.workers.dev python build.py` (from `source/`), or by editing `assets/chatbot-config.js` and setting `"proxyUrl"` and `"backend": "proxy"`.

## What the proxy enforces
- Only listed origins may call it (browsers send the Origin header); requests from other sites get HTTP 403.
- Input limits: question 600 characters, at most 8 passages of 2,500 characters (13,000 in total), at most 6 history messages.
- A fixed system prompt (answer only from the numbered passages, cite them, say when the course does not cover something). Callers cannot change it.
- A best-effort rate limit per IP (`RATE_LIMIT` requests per 10 minutes). For real abuse protection add a Cloudflare Rate Limiting rule.
- `max_tokens` is capped (`MAX_TOKENS`), which bounds cost per request.

## Cost and privacy
Each answer uses roughly 1.5 to 3 thousand input tokens and a few hundred output tokens. Choose a small model (the default is `claude-haiku-5-5`) and set a monthly spend limit in your provider console. Visitors' questions and the retrieved passages go to your Worker and the model provider; tell your users.

## Other hosts
The logic is a plain `fetch` handler. To run it on Vercel, Netlify or Deno Deploy, keep `validate`, `toText` and the request to `https://api.anthropic.com/v1/messages`, and adapt the entry point and environment variable access.
""")

# ---------------- build-time indexer ----------------
def _clean(h):
    h = re.sub(r"<svg.*?</svg>", " ", h, flags=re.S); h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    h = re.sub(r'<div class="toc">.*?</div>', " ", h, flags=re.S); h = re.sub(r'<div class="demo"[^>]*></div>', " [interactive demo] ", h)
    h = re.sub(r"</t[dh]>", " | ", h); h = re.sub(r"</tr>", ". ", h); h = re.sub(r"</(p|li|div|h\d|figcaption)>", " ", h)
    h = re.sub(r"<[^>]+>", " ", h); h = html.unescape(h)
    return re.sub(r"\s+", " ", h).strip()
def _passages(text, maxw=150, minw=25):
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\[“])", text); out, cur, n = [], [], 0
    for s in sents:
        k = len(s.split())
        if cur and n + k > maxw: out.append(" ".join(cur)); cur, n = [], 0
        cur.append(s); n += k
    if cur:
        if out and n < minw: out[-1] += " " + " ".join(cur)
        else: out.append(" ".join(cur))
    return [p for p in out if len(p.split()) >= 6]
def _chunk_html(h, w, head, base, docs, keep_intro=False):
    parts = re.split(r'(<h2 id="[^"]*"[^>]*>.*?</h2>|<h3 id="[^"]*">.*?</h3>)', h, flags=re.S)
    h2t, h2i, h3t, h3i = "Introduction", "", "", ""
    for seg in parts:
        m = re.match(r'<h([23]) id="([^"]*)"[^>]*>(.*?)</h[23]>', seg, flags=re.S)
        if m:
            if m.group(1) == "2": h2t, h2i, h3t, h3i = _clean(m.group(3)), m.group(2), "", ""
            else: h3t, h3i = _clean(m.group(3)), m.group(2)
            continue
        if not h2i and not h3i and not keep_intro: continue
        for q_, a_ in re.findall(r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", seg, flags=re.S):
            q_, a_ = _clean(q_), _clean(a_); q_ = re.sub(r"^Exercise \d+:\s*", "", q_)
            docs.append(dict(w=w, k="ex", t=f"{head} › Exercise", u=f"{base}#exercises", x=f"Exercise: {q_} Solution: {a_}", q=q_, a=a_))
        seg = re.sub(r"<details>.*?</details>", " ", seg, flags=re.S)
        islab = h3i.startswith("lab-") or h2i == "lab"
        pres = re.findall(r"<pre><code>(.*?)</code></pre>", seg, flags=re.S); outs = re.findall(r'<div class="out"><b>Output</b><pre>(.*?)</pre>', seg, flags=re.S)
        seg2 = re.sub(r'<div class="out">.*?</pre></div>', " ", seg, flags=re.S)
        if islab:
            desc = _clean(re.sub(r"<pre>.*?</pre>", " ", seg2, flags=re.S)); code = html.unescape(pres[0]) if pres else ""; o = html.unescape(outs[0]) if outs else ""
            title = h3t or "Code lab"
            docs.append(dict(w=w, k="lab", t=f"{head} › {title}", u=f"{base}#{h3i or h2i}", x=f"{re.sub(r'^Lab [0-9.]+: ', '', title)}. {desc} Code: {re.sub(chr(10)+'+', chr(10), code)[:900]} Output: {o[:600]}"))
            continue
        seg3 = re.sub(r"<pre><code>(.*?)</code></pre>", lambda mm: " Code: " + re.sub(r"\s+", " ", html.unescape(mm.group(1)))[:700] + " ", seg2, flags=re.S)
        txt = _clean(seg3)
        for p in _passages(txt): docs.append(dict(w=w, k="c", t=f"{head} › {h2t}" + (f" › {h3t}" if h3t else ""), u=f"{base}#{h3i or h2i}" if (h3i or h2i) else base, x=p))

def post_chat():
    docs, weeks = [], []
    for w in ALL:
        n = w["n"]; head = f"Week {n}: {w['title']}"; base = f"week-{n:02d}.html"
        _chunk_html(PB[n], n, head, base, docs)
        secs = re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', PB[n], flags=re.S)
        weeks.append(dict(n=n, title=w["title"], summary=w["summary"], obj=list(w["obj"]), secs=[[i, _clean(t)] for i, t in secs]))
        docs.append(dict(w=n, k="syl", t=f"Syllabus › {head}", u=base, x=f"Week {n}: {w['title']}. {w['summary']} Based on: {w['src']}."))
        if w["rd"]: docs.append(dict(w=n, k="rd", t=f"{head} › Further reading", u=base + "#reading", x="Further reading and papers for Week %d (%s): " % (n, w["title"]) + " ".join(w["rd"])))
        if n in ASSIGN: docs.append(dict(w=n, k="asg", t=f"{head} › Programming assignment", u=base + "#programming-assignment", x=f"Programming assignment for Week {n}: {ASSIGN[n]}"))
    for slug, title, text in APPX: _chunk_html(md(text), 0, title, slug + ".html", docs, True)
    for term, dfn in sorted(GL.items()): docs.append(dict(w=0, k="gl", t=f"Glossary › {term}", u="glossary.html", x=f"{term}: {dfn}"))
    docs.append(dict(w=0, k="faq", t="About this course", u="index.html", x="Advanced Computer Networks is a 16-week graduate course covering Internet architecture, queueing, routing and BGP, congestion control (Reno, CUBIC, BBR), QUIC and TLS, data center networks, software-defined networking and P4, wireless, CDNs and video streaming, network security, measurement and satellites, AI cluster networking, and WAN traffic engineering with overlays and DNS. Each chapter has basics, core and advanced sections, interactive demos, runnable labs, exercises with solutions, a programming assignment and a paper-reading guide."))
    docs.append(dict(w=0, k="faq", t="How to use this site", u="downloads.html", x="Each week page has a table of contents, interactive demos you can drag, code labs whose output is shown, exercises with hidden solutions and a mark-as-complete button. The Downloads page offers a PDF of every chapter, the complete notes as one PDF, reference cards, and lab files (lab.py and Jupyter notebooks). The labs folder also has two Mininet scripts. The sidebar search filters the topic list. This chatbot answers questions from the site content and links to the source section."))
    docs.append(dict(w=0, k="faq", t="Grading and assessment", u="app-d.html#assessment-as-a-formal-course", x="Suggested assessment: problem sets and labs 25%, midterm in Week 8 20%, paper critiques 15%, project 25% with proposal in Week 3 and final report and talk in Week 16, final exam 15%."))
    os.makedirs(OUT + "/training", exist_ok=True); qa = []
    def _msg(u, a): qa.append({"messages": [{"role": "system", "content": "You are the teaching assistant for an Advanced Computer Networks course. Answer accurately and concisely."}, {"role": "user", "content": u}, {"role": "assistant", "content": a}]})
    for d_ in docs:
        if d_["k"] == "ex": _msg(d_["q"], d_["a"] + " (See " + d_["u"] + ")")
        elif d_["k"] == "gl": t_, df_ = d_["x"].split(": ", 1); _msg("What is " + t_ + "?", df_)
    for w_ in weeks: _msg("What is Week %d of the ACN course about?" % w_["n"], "Week %d: %s. %s Learning objectives: %s" % (w_["n"], w_["title"], w_["summary"], " ".join(w_["obj"])))
    with open(OUT + "/training/acn-qa-pairs.jsonl", "w", encoding="utf-8") as f_:
        for r_ in qa: f_.write(_json.dumps(r_, ensure_ascii=False) + "\n")
    open(OUT + "/training/README.md", "w", encoding="utf-8").write("# Optional fine-tuning data\n\n`acn-qa-pairs.jsonl` has %d question-answer pairs in the chat format used by most fine-tuning services, generated from the exercises (with solutions), the glossary and the week summaries. The chatbot does NOT need it: it uses retrieval-augmented generation, so the model always answers from freshly retrieved course passages and cites them. Fine-tuning a model on this small set mainly teaches style and vocabulary, can make it overconfident about things the course does not say, and goes stale whenever you edit the course. If you still want to fine-tune (for example a small local model), use this file for style and keep retrieval on for facts.\n" % len(qa))
    data = dict(docs=docs, weeks=weeks)
    open(OUT + "/assets/chatbot-data.js", "w", encoding="utf-8").write("window.ACN_INDEX=" + _json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
    body = ('<h1>Ask the course</h1><p class="lead">A chatbot grounded in every page of this site. It retrieves the relevant passages, optionally has an AI model write an answer from them, cites the sections it used, and says so when the course does not cover a question.</p>'
            '<div id="acn-chat-page"></div>'
            '<h2>How the RAG pipeline works</h2><ol><li><b>Index (build time).</b> Every section, worked example, exercise with solution, lab, glossary term, appendix, assignment and reading list is split into passages (about 690 in total).</li>'
            '<li><b>Retrieve (in your browser).</b> Your question is expanded with acronyms and synonyms and the passages are ranked with BM25 plus phrase matching. If nothing in the course is a confident match, the chatbot stops there and says so; the AI model is never asked to guess.</li>'
            '<li><b>Augment.</b> The best passages (and the continuation of the top one) are numbered and packed into a prompt together with the last few turns of the conversation.</li>'
            '<li><b>Generate.</b> A language model writes the answer using only those passages and cites them as [1], [2]. The answer streams in word by word.</li>'
            '<li><b>Check.</b> Citations are turned into links to the exact section, invalid citations are dropped, and any number in the answer that does not appear in the retrieved text is flagged for you to check.</li></ol>'
            '<h2>Choose how answers are generated (the ⚙ AI mode button)</h2>'
            '<ul><li><b>Course search only</b> (default unless the site owner configured AI): no model; you get the best passage and links. Works offline.</li>'
            '<li><b>In-browser AI</b>: a small open model (about 1–3 billion parameters) runs on your own GPU through WebGPU. Free and private, but the first question downloads the model (hundreds of MB to a few GB, then cached) and quality is that of a small model.</li>'
            '<li><b>Cloud AI via the course proxy</b>: best quality. The site owner deploys the small proxy in <code>worker/</code> (instructions in <code>worker/README.md</code>), which holds the API key and calls a Claude model.</li>'
            '<li><b>OpenAI-compatible endpoint</b>: for example Ollama or LM Studio running on your own computer, or any provider with a chat-completions API.</li></ul>'
            '<h2>What to ask</h2><ul><li>Concepts: “What is head-of-line blocking?”, “Why does CUBIC beat Reno on long paths?”.</li><li>Calculations: “Walk me through the Mathis formula”, “Little’s law example”.</li><li>Navigation: “What is in Week 9?”, “show the syllabus”, “which lab simulates ECMP collisions?”.</li><li>Practice: “Quiz me on BGP” (then use the Show solution button).</li><li>Study help: “Which papers should I read for congestion control?”, “assignment for week 4”.</li></ul>'
            '<h2>Limits</h2><p>Answers are only as good as the retrieved passages: a very broad question may need several sections, and a small in-browser model can still mis-explain a passage it was given, so follow the citations for anything important. In search-only mode the chatbot quotes rather than reasons.</p>'
            '<h2>Training vs RAG</h2><p>RAG does not retrain a model: the knowledge lives in the index and is rebuilt with the site, so answers stay current with the course and are traceable to a section. If you want to fine-tune a model anyway, <code>training/acn-qa-pairs.jsonl</code> contains the exercises, glossary and week summaries in chat format.</p>')
    page("chatbot.html", "Ask the course", "chat", body, "Course chatbot")
    print("chatbot index:", len(docs), "passages,", round(os.path.getsize(OUT + "/assets/chatbot-data.js") / 1024), "KB")

_post_prev = post
def post():
    _post_prev(); post_chat()
