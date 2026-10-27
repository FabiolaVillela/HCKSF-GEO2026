/* Base cilíndrica en planta: radial hacia afuera, tangencial antihoraria (+Z). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.DomeReactions=api;})(globalThis,function(){
 function center(geometry){
   const supports=new Set(geometry.support_nodes),nodes=geometry.nodes.filter(n=>supports.has(n.id));
   if(!nodes.length)return null;
   return [nodes.reduce((s,n)=>s+n.x,0)/nodes.length,nodes.reduce((s,n)=>s+n.y,0)/nodes.length];
 }
 function cylindrical(node,values,origin){
   if(!node||!origin)return null;
   const dx=node.x-origin[0],dy=node.y-origin[1],radius=Math.hypot(dx,dy);
   // En el eje no hay dirección radial única: no inventar componentes.
   if(radius<=1e-9)return null;
   const er=[dx/radius,dy/radius,0],et=[-er[1],er[0],0];
   const rr=values[0]*er[0]+values[1]*er[1],rt=values[0]*et[0]+values[1]*et[1];
   return {values:[rr,rt,values[2]],vectors:[er.map(x=>x*rr),et.map(x=>x*rt),[0,0,values[2]]]};
 }
 return Object.freeze({center,cylindrical});
});
