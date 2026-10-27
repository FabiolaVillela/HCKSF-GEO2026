const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/domestage/static/simulator.js'),'utf8'),context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function modelDimensions('),source.indexOf('function drawDimensions(')),context);
test('diameter is rotation/translation invariant horizontal span; height uses vertical extrema',()=>{
 const nodes=[{x:-5,y:0,z:2},{x:5,y:0,z:2},{x:0,y:0,z:6}],before=JSON.stringify(nodes);
 for(const angle of [0,.4,1.7]){
 const n=nodes.map(p=>({x:20+p.x*Math.cos(angle)-p.y*Math.sin(angle),y:-7+p.x*Math.sin(angle)+p.y*Math.cos(angle),z:p.z+10}));
 const d=context.modelDimensions(n);assert(Math.abs(d.diameter-10)<1e-10);assert.equal(d.height,4);
 }
 assert.equal(JSON.stringify(nodes),before);
});
test('flat, single-node and empty models have well-defined dimensions',()=>{
 assert.equal(context.modelDimensions([]),null);
 const d=context.modelDimensions([{x:3,y:4,z:5}]);assert.equal(d.diameter,0);assert.equal(d.height,0);
 assert.equal(context.modelDimensions([{x:0,y:0,z:8},{x:3,y:4,z:8}]).diameter,5);
});
test('dimension lines stay in world XY/vertical planes and height anchors touch real apex/base nodes',()=>{
 const nodes=[{x:-5,y:2,z:7},{x:5,y:2,z:7},{x:0,y:2,z:11}];
 const d=context.modelDimensions(nodes);
 assert.equal(d.apex,nodes[2]);assert(nodes.includes(d.base));assert.equal(d.base.z,7);
 for(const p of d.diameterLine)assert.equal(p[2],7);
 for(const p of d.heightLine)assert.equal(p[0],d.apex.x);
 assert.equal(d.heightLine[0][0],d.heightLine[1][0]);
 assert.equal(d.heightLine[0][2],d.base.z);assert.equal(d.heightLine[1][2],d.apex.z);
 assert(Math.abs(Math.hypot(...d.diameterLine[0].map((v,i)=>v-d.diameterLine[1][i]))-d.diameter)<1e-10);
});
test('height placement is a quarter-turn from diameter offset for any plan orientation',()=>{
 for(const angle of [0,.3,1.2]){
 const nodes=[{x:-5,y:0,z:0},{x:5,y:0,z:0},{x:0,y:0,z:3}].map(p=>({x:12+p.x*Math.cos(angle),y:-4+p.x*Math.sin(angle),z:p.z}));
 const d=context.modelDimensions(nodes);
 const center=[(d.pair[0].x+d.pair[1].x)/2,(d.pair[0].y+d.pair[1].y)/2];
 const dv=[0,1].map(i=>(d.diameterLine[0][i]+d.diameterLine[1][i])/2-center[i]);
 const hv=[0,1].map(i=>d.heightLine[0][i]-center[i]);
 assert(Math.abs(dv[0]*hv[0]+dv[1]*hv[1])<1e-9);
 assert(dv[0]*hv[1]-dv[1]*hv[0]<0);
 assert(nodes.includes(d.base));assert(nodes.includes(d.apex));
 }
});
