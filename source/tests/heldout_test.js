const vm=require('vm'),fs=require('fs');global.window=global;global.document=undefined;
vm.runInThisContext(fs.readFileSync('assets/chatbot-data.js','utf8'));vm.runInThisContext(fs.readFileSync('assets/chatbot.js','utf8'));ACNChat.build(window.ACN_INDEX);
const T=[
 ["what is the maximum segment size", /week-0|app-b|glossary/i, 1],
 ["how does slow start grow the window", /week-04/i, 1],
 ["what is an autonomous system", /week-03|glossary|app-b/i, 1],
 ["explain the fat tree topology", /week-07|glossary/i, 1],
 ["how does fq-codel work", /week-05/i, 1],
 ["what is the purpose of connection ids in quic", /week-06/i, 1],
 ["explain pass time of a satellite overhead", /week-13/i, 1],
 ["what is the ring algorithm", /week-14/i, 1],
 ["how are exercises graded or assignments assessed", /app-d|asg|week/i, 1],
 ["what is segment routing", /week-15|glossary/i, 1],
 ["how does tcp detect packet loss", /week-04|app-b|week-06/i, 1],
 ["what is a middlebox", /week-01|app-b|week-06/i, 1],
 ["difference between throughput and latency", /week-01|week-05/i, 1],
 ["explain mixture of experts traffic", /week-14/i, 1],
 ["how does wireshark capture packets", /app-c/i, 1],
 ["what is the erlang b formula", /week-02/i, 1],
 ["who is the president of the united states", null, 0],
 ["how do vaccines work", null, 0],
 ["what is the stock price of apple", null, 0],
 ["translate hello into spanish", null, 0],
 ["how do i learn guitar quickly", null, 0],
 ["what is photosynthesis", null, 0],
 ["explain blockchain consensus", null, 0],
 ["python list comprehension syntax", null, 0],
];
let right=0;
for(const [q,exp,should] of T){const r=ACNChat.ask(q);const src=r.doc?r.doc.u:'';const ok=should?(!r.miss&&exp.test(src+' '+(r.doc?r.doc.k:''))):!!r.miss;right+=ok;
 console.log(ok?'ok  ':'MISS',q,'=>',r.miss?'REFUSED':src);}
console.log(`\nheld-out: ${right}/${T.length}`);
