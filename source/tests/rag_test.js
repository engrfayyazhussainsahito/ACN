const vm=require('vm'),fs=require('fs');
global.window=global; global.document=undefined;
vm.runInThisContext(fs.readFileSync('assets/chatbot-data.js','utf8'));
vm.runInThisContext(fs.readFileSync('assets/chatbot.js','utf8'));
ACNChat.build(window.ACN_INDEX); const R=ACNChat.rag;
let pass=0,fail=0; const ok=(c,m)=>{c?pass++:fail++; console.log((c?'PASS ':'FAIL ')+m)};
(async()=>{
 // --- prompt construction
 const q='How does CUBIC differ from Reno?'; const r=ACNChat.ask(q); const ctx=R.fit(r.ctx,9000);
 const msgs=R.messages(q,[{role:'user',content:'hi'},{role:'assistant',content:'hello'}],ctx);
 ok(msgs[0].role==='system'&&/ONLY the numbered course excerpts/.test(msgs[0].content),'system prompt enforces grounding');
 ok(msgs.length===4&&/\[1\]/.test(msgs[3].content)&&msgs[3].content.endsWith('Question: '+q),'user message has numbered excerpts + question; history included');
 ok(ctx.length>=2&&ctx.length<=6,'context has 2-6 passages ('+ctx.length+')');
 const chars=ctx.reduce((a,d)=>a+d.x.length,0); ok(chars<=9000+1300,'context size within budget ('+chars+' chars)');
 ok(R.fit(r.ctx,1500).length>=2,'small-model budget keeps at least 2 passages, got '+R.fit(r.ctx,1500).length);
 // --- follow-up rewriting
 ok(R.rewrite('and for BBR?',[{role:'user',content:'how does cubic work'}]).includes('cubic'),'follow-up is rewritten with previous question');
 ok(R.rewrite('explain TCP slow start in detail',[{role:'user',content:'how does cubic work'}])==='explain TCP slow start in detail','self-contained question is not rewritten');
 ok(R.rewrite('more',[{role:'user',content:'x y z'}])==='more','"more" is left for the follow-up logic');
 // --- rendering & safety
 const c2=[{t:'T1',u:'week-04.html#a',x:'x'},{t:'T2',u:'week-05.html#b',x:'y'}];
 let h=R.renderRag('Answer **bold** [1] and [2].\n\n- item one [2]\n- item two\n\nTail [9]',c2);
 ok(/<sup><a href="week-04.html#a"/.test(h)&&/<b>bold<\/b>/.test(h)&&/<ul class="acnc-more"><li>item one/.test(h),'citations become links, bold and bullets render');
 ok(!/\[9\]/.test(h),'invalid citation [9] is dropped');
 h=R.renderRag('<img src=x onerror=alert(1)> <script>alert(2)</script> [1]',c2);
 ok(!/<img|<script/i.test(h)&&/&lt;img/.test(h),'model output is HTML-escaped (XSS)');
 h=R.renderRag('x [1]',[{t:'T"><script>',u:'a" onmouseover="alert(1)',x:''}]);
 ok(!/<script>/.test(h)&&!/" onmouseover=/.test(h),'link attributes are escaped');
 // --- verification of figures
 ok(R.verify('The BDP is 10 MB [1] and takes 777 ms',[{x:'a 1 Gb/s path with 80 ms RTT holds 10 MB'}],'q').join()==='777','invented number 777 flagged, 10 accepted');
 ok(R.verify('about 62% [1]',[{x:'hit ratio is 62%'}],'q').length===0,'number present in source passes');
 const fin=R.finishHtml('The window grows by 1 per RTT [1]. It reaches 12345 packets [2].',ctx,q);
 ok(/Sources: \[1\]/.test(fin)&&/12345/.test(fin)&&/do not appear in the retrieved course text/.test(fin),'finishHtml: sources list + unverified-figure warning');
 ok(/Closest course sections/.test(R.finishHtml('The course material does not cover this clearly.',ctx,q)),'refusal shows closest sections instead of fake sources');
 // --- orchestration with a mock model
 let calls=0,seenCtx=null; const mock=async(c,qq,hist,cx,onTok)=>{calls++;seenCtx=cx;const t='CUBIC grows its window as a cubic function of time since the last loss [1], while Reno adds one segment per RTT [2].';for(const w of t.split(' '))onTok(w+' ');return t;};
 const cfg={backend:'openai',url:'http://x'}; let toks=0,gotCtx=0;
 let out=await R.respond(cfg,q,[],{tok:()=>toks++,ctx:()=>gotCtx++},mock);
 ok(out.mode==='rag'&&calls===1&&toks>10&&gotCtx===1,'confident question: model called once, tokens streamed ('+toks+'), ctx callback fired');
 ok(/<sup><a/.test(out.html)&&/Sources:/.test(out.html),'RAG answer has citation links and a sources line');
 calls=0; out=await R.respond(cfg,'who won the world cup in 2018',[],{},mock);
 ok(calls===0&&out.mode==='extractive'&&/not guess/.test(out.html),'off-topic question: model NOT called, honest refusal');
 for(const sp of ['what is in week 9','show the syllabus','help','quiz me on queueing']){calls=0; out=await R.respond(cfg,sp,[],{},mock); ok(calls===0&&out.mode==='extractive','special intent "'+sp+'" bypasses the model');}
 out=await R.respond(cfg,q,[],{},async()=>{throw new Error('HTTP 500')});
 ok(out.mode==='fallback'&&/AI answer unavailable \(HTTP 500\)/.test(out.html)&&/CUBIC|cubic/i.test(out.html),'model failure: falls back to course text with a note');
 out=await R.respond(cfg,q,[],{},async()=>'   ');
 ok(out.mode==='fallback','empty model output: falls back');
 out=await R.respond({backend:'extractive'},q,[],{},mock); ok(out.mode==='extractive','extractive mode never calls the model');
 out=await R.respond({backend:'openai'},q,[],{}); ok(out.mode==='fallback'&&/no endpoint URL/.test(out.html),'openai backend without URL: clear fallback message');
 out=await R.respond({backend:'proxy'},q,[],{}); ok(out.mode==='fallback'&&/no proxy URL/.test(out.html),'proxy backend without URL: clear fallback message');
 // follow-up uses history for retrieval
 let seenQ=null; await R.respond(cfg,'and for BBR?',[{role:'user',content:'how does cubic work'},{role:'assistant',content:'...'}],{},async(c,qq,h,cx)=>{seenQ=qq;return 'BBR models bandwidth and RTT [1].'});
 ok(seenQ==='and for BBR?','user wording is sent to the model unchanged (retrieval used the rewritten query)');
 // --- real questions: context quality
 for(const qq of ['What is the bandwidth-delay product?','How does BGP choose a route?','Explain head-of-line blocking','What is a count-min sketch?','how does chord lookup work']){
   const rr=ACNChat.ask(qq); const cx=R.fit(rr.ctx||[],9000); ok(cx.length>=2,`"${qq}" -> ${cx.length} passages, top: ${cx[0].t.slice(0,60)}`);}
 // --- streaming parsers with mock fetch
 const enc=new TextEncoder(); const stream=(parts)=>({ok:true,headers:{get:()=>'text/event-stream'},body:{getReader(){let i=0;return{read:async()=>i<parts.length?{done:false,value:enc.encode(parts[i++])}:{done:true}}}}});
 const sse=(t)=>'data: '+JSON.stringify({choices:[{delta:{content:t}}]})+'\n\n';
 global.fetch=async()=>stream([sse('Hel'),sse('lo ').slice(0,12),sse('lo ').slice(12)+sse('wor'),sse('ld')+'data: [DONE]\n\n']);
 let acc=''; let full=await R.streamOpenAI({url:'http://x',model:'m'},[],t=>acc+=t);
 ok(full==='Hello world'&&acc==='Hello world','OpenAI SSE stream reassembled across chunk boundaries: "'+full+'"');
 global.fetch=async()=>({ok:true,headers:{get:()=>'application/json'},json:async()=>({choices:[{message:{content:'plain json answer'}}]})});
 full=await R.streamOpenAI({url:'http://x'},[],()=>{}); ok(full==='plain json answer','non-streaming JSON response handled');
 global.fetch=async()=>({ok:false,status:401}); let err=null; try{await R.streamOpenAI({url:'http://x'},[],()=>{})}catch(e){err=e.message}; ok(/401/.test(err),'HTTP error surfaces status: '+err);
 let sent=null; global.fetch=async(u,o)=>{sent=JSON.parse(o.body);return {ok:true,body:{getReader(){let i=0;const p=['Hello ','proxy'];return{read:async()=>i<p.length?{done:false,value:enc.encode(p[i++])}:{done:true}}}}}};
 acc=''; full=await R.streamProxy({proxyUrl:'http://p'},'Q?',[{role:'user',content:'a'}],ctx.slice(0,2),t=>acc+=t);
 ok(full==='Hello proxy'&&sent.question==='Q?'&&sent.sources.length===2&&sent.sources[0].n===1&&sent.history.length===1,'proxy payload {question, history, sources[n,title,url,text]} and plain-text stream');
 global.fetch=async()=>({ok:false,status:429,json:async()=>({error:'rate limit reached; please wait a few minutes'})}); err=null; try{await R.streamProxy({proxyUrl:'http://p'},'Q',[],ctx,()=>{})}catch(e){err=e.message}; ok(/rate limit/.test(err),'proxy error message passed through');
 // --- WebLLM model selection
 const L=['Llama-3.2-1B-Instruct-q4f16_1-MLC','Llama-3.2-3B-Instruct-q4f16_1-MLC','Qwen2.5-1.5B-Instruct-q4f16_1-MLC','Qwen2.5-3B-Instruct-q4f16_1-MLC','Qwen2.5-1.5B-Instruct-q4f16_1-MLC-1k','Qwen2.5-Coder-1.5B-Instruct-q4f16_1-MLC'];
 ok(R.pickModel(L,'fast')==='Qwen2.5-1.5B-Instruct-q4f16_1-MLC','pickModel fast -> Qwen2.5 1.5B (not the -1k or Coder variants)');
 ok(R.pickModel(L,'better')==='Qwen2.5-3B-Instruct-q4f16_1-MLC','pickModel better -> Qwen2.5 3B');
 ok(R.pickModel(['foo-instruct-q4f16_1','bar'],'fast')==='foo-instruct-q4f16_1','pickModel falls back to any instruct q4f16_1 model');
 err=null; try{await R.generate({backend:'webllm'},'q',[],ctx,()=>{},()=>{})}catch(e){err=e.message}; ok(/WebGPU/.test(err),'webllm without WebGPU gives a clear message');
 console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
