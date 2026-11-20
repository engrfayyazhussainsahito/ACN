const vm=require('vm'),fs=require('fs');
global.window=global; global.document=undefined;
vm.runInThisContext(fs.readFileSync('assets/chatbot-data.js','utf8'));
vm.runInThisContext(fs.readFileSync('assets/chatbot.js','utf8'));
ACNChat.build(window.ACN_INDEX);
const strip=h=>h.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
const tests=[
 // [question, expected substring in top source url or title, should answer?]
 ["What is the bandwidth-delay product?", /week-01|glossary|Week 1/i, true],
 ["bdp", /week-01|glossary/i, true],
 ["How does CUBIC differ from Reno?", /week-04/i, true],
 ["Explain head-of-line blocking", /week-06|glossary/i, true],
 ["How does BGP choose a route?", /week-03/i, true],
 ["What is little's law?", /week-02|glossary/i, true],
 ["why do queues build below capacity", /week-02/i, true],
 ["Mathis formula", /week-0[45]/i, true],
 ["what is incast", /week-07|glossary/i, true],
 ["explain ECMP hash collisions", /week-07|week-14|glossary/i, true],
 ["how does DCTCP react to ECN marks", /week-0[57]/i, true],
 ["what is a count-min sketch", /week-09/i, true],
 ["Shannon capacity formula", /week-10/i, true],
 ["zipf cache hit ratio", /week-11/i, true],
 ["what is a SYN cookie", /week-12|glossary/i, true],
 ["how does RPKI stop hijacks", /week-12|week-03/i, true],
 ["LEO satellite latency compared to fibre", /week-13/i, true],
 ["ring all-reduce time", /week-14/i, true],
 ["what is PFC deadlock", /week-14|glossary/i, true],
 ["how does chord lookup work", /week-15/i, true],
 ["max-min fairness water filling", /week-15/i, true],
 ["how to emulate delay and loss with netem", /app-c/i, true],
 ["how do I install mininet", /app-c/i, true],
 ["what is a subnet mask", /app-b/i, true],
 ["QUIC 0-RTT replay risk", /week-06/i, true],
 ["TLS 1.3 handshake round trips", /week-06/i, true],
 ["BBR probing gain", /week-05/i, true],
 ["bufferbloat", /week-05|glossary/i, true],
 ["what is a P4 parser", /week-09/i, true],
 ["how many hosts in a fat-tree", /week-07|glossary/i, true],
 ["how do I compute the checksum of an IPv4 header", /week-09/i, true],
 ["what is the difference between link state and distance vector", /week-03/i, true],
 ["why does wifi get slow with many stations contending", /week-10/i, true],
 ["how does adaptive bitrate decide quality", /week-11/i, true],
 ["what does anycast do", /week-11|week-15|glossary/i, true],
 ["how do I choose a checkpoint interval for training", /week-14/i, true],
 ["difference between RIP and OSPF", /week-03/i, true],
 ["what is the grading scheme", /app-d|index/i, true],
 ["where can I download the PDF", /downloads/i, true],
 ["what is congestion collapse", /week-04|glossary/i, true],
 ["what causes packet loss on wireless links", /week-10/i, true],
 ["how big should router buffers be", /week-0[25]/i, true],
 ["why does my video keep buffering", /week-11/i, true],
 ["how do cdns work", /week-11/i, true],
 ["explain tcp slow start", /week-04/i, true],
 ["what happens when a bgp route is withdrawn", /week-03/i, true],
 ["how does a switch parse headers in p4", /week-09/i, true],
 ["why do gpus need a lossless network", /week-14/i, true],
 ["how does dns caching and ttl affect latency", /week-15/i, true],
 ["what is the difference between tcp and udp", /app-b/i, true],
 // out of scope: must refuse
 ["who won the world cup in 2018", null, false],
 ["best pizza recipe with mushrooms", null, false],
 ["how do I train a convolutional neural network for image classification", null, false],
 ["what is the capital of france", null, false],
 ["how do I bake sourdough bread", null, false],
 ["explain the theory of relativity", null, false],
 ["write me a poem about the ocean", null, false],
 ["how to fix my car engine", null, false],
];
let pass=0, fail=0;
for (const [q,exp,should] of tests){
  const r=ACNChat.ask(q); const miss=!!r.miss; const top=ACNChat.search(q).res[0];
  const src=r.doc?r.doc.u+' | '+r.doc.t:'(none)';
  let ok = should ? (!miss && exp.test(src)) : miss;
  ok?pass++:fail++;
  console.log((ok?'PASS':'FAIL'), '|', q, '=>', miss?'REFUSED':src, top?`[score ${top.s.toFixed(1)}, cov ${top.cov.toFixed(2)}]`:'');
}
console.log(`\n${pass} passed, ${fail} failed`);
// special modes
for (const q of ["what is in week 9","show the syllabus","quiz me on queueing","help","assignment for week 4","which papers should I read for BGP","which lab simulates head-of-line blocking","what is a subnet mask","explain quantum computing"]){
  const r=ACNChat.ask(q); console.log('\n##',q,'\n',strip(r.html).slice(0,260));
}
