const {test}=require('node:test');const assert=require('node:assert/strict');
const {center,cylindrical}=require('../src/domestage/static/reactions.js');
const close=(a,b)=>assert(Math.abs(a-b)<1e-10,`${a} != ${b}`);
test('translated center uses all configured supports, not all nodes',()=>{
 assert.deepEqual(center({nodes:[{id:1,x:9,y:20},{id:2,x:11,y:20},{id:3,x:99,y:99}],support_nodes:[1,2]}),[10,20]);
});
test('signed cylindrical components reconstruct global force and preserve norm',()=>{
 for(const node of [{x:11,y:20},{x:10,y:21},{x:9,y:20},{x:11,y:21}]){
 const values=[3,-4,12,99,99,99],before=JSON.stringify(values),r=cylindrical(node,values,[10,20]);
 for(let i=0;i<3;i++)close(r.vectors.reduce((s,v)=>s+v[i],0),values[i]);
 close(Math.hypot(...r.values),13);assert.equal(JSON.stringify(values),before);
 }
 assert.deepEqual(cylindrical({x:10,y:21},[3,-4,12],[10,20]).values,[-4,-3,12]);
});
test('axis has no unique radial or tangential direction',()=>{
 assert.equal(cylindrical({x:10,y:20},[3,4,5],[10,20]),null);
});
