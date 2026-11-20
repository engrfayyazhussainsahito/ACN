const {JSDOM}=require('jsdom'); const {TextDecoder,TextEncoder}=require('util'); const path=require('path').resolve(__dirname,'../../')+'/';
let pass=0,fail=0; const ok=(c,m)=>{c?pass++:fail++; console.log((c?'PASS ':'FAIL ')+m)};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const errs=[]; const dom=await JSDOM.fromFile(path+'week-04.html',{runScripts:'dangerously',resources:'usable',pretendToBeVisual:true});
 const w=dom.window; w.TextDecoder=TextDecoder; w.addEventListener('error',e=>errs.push(e.message)); await sleep(800);
 const d=w.document, enc=new TextEncoder(); const calls=[];
 let mode='ok';
 w.fetch=async(url,opts)=>{ calls.push({url,body:JSON.parse(opts.body)}); if(mode==='fail') return {ok:false,status:503};
   const text='CUBIC grows its window as a cubic function of the time since the last loss [1], while Reno adds one segment per round trip [2]. A worked figure: 9999 packets [1].';
   const parts=text.match(/.{1,17}/g).map(t=>'data: '+JSON.stringify({choices:[{delta:{content:t}}]})+'\n\n').concat(['data: [DONE]\n\n']);
   return {ok:true,headers:{get:()=>'text/event-stream'},body:{getReader(){let i=0;return{read:async()=>{await sleep(5);return i<parts.length?{done:false,value:enc.encode(parts[i++])}:{done:true}}}}}}; };
 const fab=d.querySelector('.acnc-fab'); fab.click();
 ok(!!d.querySelector('.acnc-set input[name=acnbk][value=webllm]')&&!!d.querySelector('.acnc-set input[name=acnbk][value=proxy]')&&!!d.querySelector('.acnc-set input[name=acnbk][value=openai]'),'settings panel offers search-only / in-browser / proxy / OpenAI-compatible modes');
 ok(d.querySelector('.acnc-set input[name=acnbk][value=extractive]').checked,'default mode is course search only');
 d.querySelector('[data-a=set]').click(); ok(d.querySelector('.acnc-set').classList.contains('open'),'AI mode button opens the panel');
 d.querySelector('input[name=acnbk][value=openai]').checked=true; d.querySelector('input[name=acnbk][value=openai]').dispatchEvent(new w.Event('change'));
 ok(d.querySelector('[data-for=openai]').style.display==='block'&&d.querySelector('[data-for=proxy]').style.display==='none','choosing a mode shows only its fields');
 // configure through the site config (as an owner would) since storage is blocked on file://
 w.ACN_RAG_CONFIG={backend:'openai',url:'http://mock/v1/chat/completions',model:'m'};
 async function ask(q){const t=d.querySelector('.acnc textarea'); t.value=q; d.querySelector('.acnc-f').dispatchEvent(new w.Event('submit',{cancelable:true,bubbles:true})); await sleep(1500); const b=d.querySelectorAll('.acnc-b.b'); return b[b.length-1];}
 let b=await ask('How does CUBIC differ from Reno?');
 ok(calls.length===1&&calls[0].body.stream===true&&calls[0].body.messages[0].role==='system','model endpoint called once with a streaming chat request');
 ok(calls[0].body.messages[calls[0].body.messages.length-1].content.includes('Course excerpts:')&&/\[2\]/.test(calls[0].body.messages[calls[0].body.messages.length-1].content),'prompt contains numbered course excerpts');
 ok(/cubic function/.test(b.textContent)&&b.querySelectorAll('sup a').length>=2,'streamed answer rendered with clickable citations');
 ok(/Sources:/.test(b.textContent)&&b.querySelectorAll('.acnc-src a').length>=1,'sources line links to course sections');
 ok(/9999/.test(b.querySelector('.acnc-src:last-child').textContent)&&/do not appear in the retrieved course text/.test(b.textContent),'invented figure 9999 is flagged to the reader');
 const chips=[...d.querySelectorAll('.acnc-chips:last-of-type .acnc-chip')].map(x=>x.textContent); ok(chips.includes('Explain more simply')&&chips.includes('Quiz me on this topic'),'follow-up chips offered: '+chips.join(' | '));
 // follow-up goes through with history
 await ask('explain more simply'); const last=calls[calls.length-1].body.messages;
 ok(last.some(m=>m.role==='assistant')&&last.some(m=>m.role==='user'&&/CUBIC differ/.test(m.content)),'follow-up sends conversation history to the model');
 // off-topic: no model call
 const n=calls.length; b=await ask('how do I bake sourdough bread'); ok(calls.length===n&&/not guess/.test(b.textContent),'off-topic question does not reach the model');
 // failure → fallback
 mode='fail'; b=await ask('What is head-of-line blocking?'); ok(/AI answer unavailable \(the endpoint returned HTTP 503\)/.test(b.textContent)&&b.textContent.length>200,'model failure shows the course text plus a clear note');
 // no-config backends
 w.ACN_RAG_CONFIG={backend:'proxy',proxyUrl:''}; b=await ask('What is the bandwidth-delay product?'); ok(/no proxy URL/.test(b.textContent),'proxy mode without URL explains what is missing');
 w.ACN_RAG_CONFIG={backend:'webllm'}; b=await ask('What is the bandwidth-delay product?'); ok(/WebGPU/.test(b.textContent),'in-browser mode without WebGPU explains why it cannot run and falls back to course text');
 w.ACN_RAG_CONFIG={backend:'extractive'}; const m=calls.length; b=await ask('What is the bandwidth-delay product?'); ok(calls.length===m&&b.textContent.length>50,'search-only mode still works and makes no network calls');
 d.querySelector('[data-a=clear]').click(); await sleep(50); ok(d.querySelectorAll('.acnc-b').length===1,'Clear resets the conversation');
 ok(errs.length===0,'no JavaScript errors'+(errs.length?': '+errs.join('; '):''));
 console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
