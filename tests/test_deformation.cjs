const {test}=require('node:test');
const assert=require('node:assert/strict');
const {view}=require('../src/domestage/static/deformation.js');
const geometry={nodes:[{id:10,x:0,y:0,z:0},{id:90,x:1,y:0,z:0},{id:99,x:2,y:0,z:1}],bars:[{id:201,i:10,j:90},{id:202,i:90,j:99}]};
const result={stable:true,active_bar_ids:[201],displacements:[{node_id:10,values:[0,0,0,0,0,0]},{node_id:90,values:[0,0,-.002,4,5,6]}]};
test('opt-in; 2 mm times 10 draws 20 mm without changing physics',()=>{
 const before=JSON.stringify({geometry,result});
 assert.equal(view(geometry,result).enabled,false);
 const v=view(geometry,result,true,10);
 assert.equal(v.enabled,true);assert.deepEqual(v.points.get(90),[1,0,-.02]);
 assert.equal(v.max_real_mm,2);assert.equal(v.max_drawn_mm,20);
 assert.equal(v.points.has(99),false);assert.deepEqual(v.points.get(10),[0,0,0]);
 assert.equal(JSON.stringify({geometry,result}),before);
 assert.deepEqual(view(geometry,result,true,0).points.get(90),[1,0,0]);
});
test('unstable, missing displacement and invalid scale never draw',()=>{
 assert.equal(view(geometry,{...result,stable:false},true).available,false);
 assert.equal(view(geometry,{...result,displacements:[]},true).enabled,false);
 for(const f of [-1,Infinity,NaN,100001])assert.equal(view(geometry,result,true,f).enabled,false);
});
