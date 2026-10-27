const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/domestage/static/aisc-view.js'),'utf8'),context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf(' const utilizationStops='),source.indexOf(' function color(id)')),context);
const color=context.utilizationColor;
test('absolute utilization palette follows reference with a sharp exceedance boundary',()=>{
 assert.equal(color(0),'#00ffff');assert.equal(color(.5),'#00aaff');assert.equal(color(.75),'#0000ff');assert.equal(color(1),'#000000');
 assert.equal(color(1.00000001),'#ffff00');assert.equal(color(1.1),'#ff9900');assert.equal(color(1.25),'#ff0000');assert.equal(color(5),'#ff0000');
 assert.equal(color(.875),'#000080');assert.equal(color(1.175),'#ff4d00');
});
test('missing and invalid results stay gray, not zero-utilization cyan',()=>{
 for(const value of [null,undefined,NaN,Infinity,-1,'0.5'])assert.equal(color(value),'#737373');
});
