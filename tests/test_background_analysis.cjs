const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('src/domestage/static/simulator.js','utf8');
function setup(){
 const nodes={};const c={window:{},selectionDetail:()=>{},draw:()=>{},language:'en',analysisToken:0,analyzing:false,playbackToken:0,revision:0,playing:false,geometry:{},currentStage:1,plan:[0,1,2].map(stage=>({stage})),calculated:new Map(),calls:[],shown:[],
 $:id=>nodes[id]??={style:{},setAttribute(k,v){this[k]=v;}},config:()=>({}),translate:s=>s,history:()=>{},setTimeout:fn=>fn(),
 stop:()=>{c.playbackToken++;c.playing=false;},setStage:async n=>{c.currentStage=n;c.shown.push(n);return c.calculated.get(n)||{stable:true};},
 api:async(path,p)=>{c.calls.push(p.stage);return {stable:p.stage!==1};}};
 vm.createContext(c);vm.runInContext(source.slice(source.indexOf('function showAnalysisProgress('),source.indexOf("$('btn-analyze').onclick=analyzeStages;")),c);return c;
}
test('analysis preserves selected stage, never plays, completes green and caches results',async()=>{const c=setup();await c.analyzeStages();assert.deepEqual(c.shown,[]);assert.equal(c.currentStage,1);assert.equal(c.calculated.size,3);assert.equal(c.$('btn-analyze').disabled,true);assert.equal(c.$('analysis-fill').style.background,'#16a34a');assert.equal(c.$('analysis-meter')['aria-valuenow'],100);await c.analyzeStages();assert.deepEqual(c.calls,[0,1,2]);});
test('play starts at selected stage and does not wrap from last stage',async()=>{const c=setup();await c.analyzeStages();await c.playAssembly();assert.deepEqual(c.shown,[1,2]);c.shown=[];await c.playAssembly();assert.deepEqual(c.shown,[2]);});
test('pause invalidates playback and prevents further stages',async()=>{const c=setup();c.setTimeout=fn=>{c.stop();fn();};await c.playAssembly();assert.deepEqual(c.shown,[1]);});
test('model change discards stale pending results',async()=>{const c=setup();c.api=async()=>{c.revision++;return {};};await c.analyzeStages();assert.equal(c.calculated.size,0);assert.notEqual(c.$('analysis-fill').style.background,'#16a34a');});
test('failed request does not mark analysis complete',async()=>{const c=setup();c.api=async()=>{throw Error('failed');};await c.analyzeStages();assert.equal(c.analyzing,false);assert.match(c.$('analysis-status').textContent,/failed/);assert.notEqual(c.$('analysis-fill').style.background,'#16a34a');});

test('completion waits for utilization checks for every stage',async()=>{const c=setup(),checked=[];c.window.AISCView={precompute:async stage=>{assert.notEqual(c.$('analysis-fill').style.background,'#16a34a');checked.push(stage);},update:()=>{}};await c.analyzeStages();assert.deepEqual(checked,[0,1,2]);assert.equal(c.$('analysis-fill').style.background,'#16a34a');});
