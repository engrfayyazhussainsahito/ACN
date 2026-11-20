# ACN RAG proxy (Cloudflare Worker)

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
