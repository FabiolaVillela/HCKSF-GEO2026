const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
// Exercise the actual canvas color helpers without a browser or calculation server.
const source=fs.readFileSync(path.join(__dirname,'../src/domestage/static/simulator.js'),'utf8');
const context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function forceLimits('),source.indexOf('function updateLegend(')),context);
const {forceLimits,forceColor}=context;
test('independent 80% thresholds saturate both signs and keep the intermediate palette',()=>{
 const result={stable:true,forces:{1:-2000,2:1000,3:0}},before=JSON.stringify(result);
 const limits=forceLimits(result);
 assert.equal(limits.compression,1600);assert.equal(limits.tension,800);
 assert.equal(forceColor(-1600,limits),'#ef4444');assert.equal(forceColor(-2000,limits),'#ef4444');
 assert.equal(forceColor(-800,limits),'#f5882d');assert.equal(forceColor(0,limits),'#facc15');
 assert.equal(forceColor(400,limits),'#22c55e');assert.equal(forceColor(800,limits),'#001b96');assert.equal(forceColor(1000,limits),'#001b96');
 assert.equal(JSON.stringify(result),before);
});
test('missing results, zero and one-sided loads do not create false force colors',()=>{
 for(const value of [null,undefined,NaN,Infinity])assert.equal(forceColor(value,{compression:0,tension:0}),'#737373');
 assert.equal(forceColor(0,forceLimits({stable:true,forces:{1:0}})),'#facc15');
 assert.equal(forceLimits({stable:false,forces:{1:1000}}).tension,0);
 assert.equal(forceLimits({stable:true,forces:{1:-1000}}).tension,0);
 assert.equal(forceLimits({stable:true,forces:{1:1000}}).compression,0);
});
