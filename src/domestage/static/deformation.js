/* Deformada nodal: metros, sin modificar geometría ni resultados del solver. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.DomeDeformation=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const MAX_FACTOR=100000;
  function view(geometry,result,show=false,factor=10){
    const factorValid=Number.isFinite(factor)&&factor>=0&&factor<=MAX_FACTOR;
    const state={available:false,enabled:false,factor_valid:factorValid,factor,points:new Map(),max_real_mm:null,max_drawn_mm:null};
    if(!geometry||!result?.stable)return state;
    const active=new Set(result.active_bar_ids||[]);
    const ids=new Set(geometry.bars.filter(b=>active.has(b.id)).flatMap(b=>[b.i,b.j]));
    if(!ids.size)return state;
    const nodes=new Map(geometry.nodes.map(n=>[n.id,n]));
    const displacements=new Map((result.displacements||[]).map(n=>[n.node_id,n.values]));
    for(const id of ids){
      const u=displacements.get(id),n=nodes.get(id);
      if(!n||!Array.isArray(u)||u.length<3||!u.slice(0,3).every(Number.isFinite))return state;
    }
    state.available=true;
    state.max_real_mm=Math.max(...Array.from(ids,id=>Math.hypot(...displacements.get(id).slice(0,3))))*1000;
    state.max_drawn_mm=factorValid?state.max_real_mm*factor:null;
    state.enabled=show&&factorValid;
    if(state.enabled){
      for(const id of ids){
        const n=nodes.get(id),u=displacements.get(id),p=[n.x,n.y,n.z].map((x,i)=>x+factor*u[i]);
        if(!p.every(Number.isFinite))return {...state,enabled:false,points:new Map()};
        state.points.set(id,p);
      }
    }
    return state;
  }
  return Object.freeze({view,MAX_FACTOR});
});
