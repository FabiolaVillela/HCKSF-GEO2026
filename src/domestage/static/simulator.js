'use strict';
(()=>{
const $=id=>document.getElementById(id),canvas=$('viewport'),ctx=canvas.getContext('2d');
let geometry=null,plan=[],currentStage=0,current=null,revision=0,requestId=0,playing=false,selected='',segments=[],projected=new Map(),deformedSegments=[];
const calculated=new Map();let q=normalize([.87,-.35,.12,.32]),zoom=1;const pointers=new Map();let dragged=false,pinch=null,sliderTimer;
const fmt=(x,n=3)=>Number(x).toLocaleString('es-MX',{maximumFractionDigits:n});
function normalize(a){const n=Math.hypot(...a);return a.map(v=>v/n);}
function mul(a,b){return [a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]];}
function rotate(p){return mul(mul(q,[0,...p]),[q[0],-q[1],-q[2],-q[3]]).slice(1);}
async function api(path,data,options={}){
 const response=await fetch(path,{...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{}),...options});
 let value;try{value=await response.json();}catch{throw Error('No se encontró el motor. Inicia PYTHONPATH=src python -m domestage.server y abre su dirección local.');}
 if(!response.ok)throw Error(value.message||'El motor rechazó la solicitud.');return value;
}
function config(){return {material:$('sel-material').value,profile:$('sel-profile').value,connection:$('sel-connection').value,support:$('sel-support').value,bars_per_step:+$('sel-step').value,worker_kg:+$('worker-kg').value};}
function stop(){clearTimeout(sliderTimer);playing=false;$('btn-play').textContent='▶ Recorrer etapas';}
function clearAnalysis(){++requestId;current=null;$('download-stage').disabled=true;$('max-tension').textContent='—';$('max-compression').textContent='—';$('max-displacement').textContent='—';$('installed-weight').textContent='—';$('worker-load').textContent='—';badge('PENDIENTE','pending');updateDeformation();selectionDetail();draw();}
function badge(label,status){$('status-badge').textContent=label;$('status-badge').className='badge badge-'+(status==='stable'?'stable':status==='unstable'||status==='error'?'unstable':'pending');}
function populateSupports(){
 $('support-nodes').replaceChildren();const supports=new Set(geometry.support_nodes);
 for(const n of geometry.nodes){const o=document.createElement('option');o.value=n.id;o.textContent=`Nodo ${n.id} · Z ${fmt(n.z)} m`;o.selected=supports.has(n.id);$('support-nodes').append(o);}
 $('element-select').replaceChildren(new Option('Sin selección',''));
 for(const b of geometry.bars)$('element-select').append(new Option('Barra '+b.id,'b'+b.id));
 for(const n of geometry.support_nodes)$('element-select').append(new Option('Apoyo '+n,'s'+n));
 selected='';$('element-select').value='';
}
async function replan(reset=false){
 const rev=++revision;stop();calculated.clear();$('stage-history').textContent='Pendiente de cálculo.';clearAnalysis();if(!geometry){$('message').textContent='Carga una geometría válida.';return;}
 $('message').textContent='Preparando secuencia de montaje…';
 try{const p=await api('/api/plan',{geometry,bars_per_step:config().bars_per_step});if(rev!==revision)return;plan=p;
 $('stage-slider').max=plan.length-1;$('last-stage').textContent=plan.length-1;
 await setStage(reset?0:Math.min(currentStage,plan.length-1));
 }catch(error){if(rev!==revision)return;badge('ERROR','error');$('message').textContent=error.message;}
}
function pendingStage(stage){
 currentStage=stage;clearAnalysis();const s=plan[stage];if(!s)return;
 $('stage-slider').value=stage;$('stage-num').textContent=stage;
 $('active-bars-count').textContent=s.active_count;$('total-bars-count').textContent=s.total_bars;
 $('progress-text').textContent=fmt(s.progress_pct,1)+'%';$('progress-fill').style.width=s.progress_pct+'%';
 $('newest-bar-text').textContent=s.new_bar_ids.length?s.new_bar_ids.map(i=>'#'+i).join(', '):'Sin barras nuevas';draw();
}
async function setStage(stage){
 if(!plan.length)return;stage=Math.max(0,Math.min(stage,plan.length-1));pendingStage(stage);
 const token=++requestId,rev=revision;$('message').textContent='Calculando equilibrio de la etapa '+stage+'…';badge('CALCULANDO','pending');
 try{const value=calculated.get(stage)||await api('/api/stage',{geometry,config:config(),stage});
 if(token!==requestId||rev!==revision)return null;calculated.set(stage,value);current=value;
 badge(value.status==='stable'?'EQUILIBRIO CALCULADO':value.status==='unstable'?'MECANISMO DETECTADO':value.status==='empty'?'SIN BARRAS':'ERROR',value.status);
 $('message').textContent=value.message;
 $('installed-weight').textContent=fmt(value.mass_kg*9.80665/1000)+' kN ('+fmt(value.mass_kg,1)+' kg)';
 $('worker-load').textContent=fmt(value.worker_load_N/1000)+' kN'+(value.worker_node===null?'':` · nodo ${value.worker_node}`);
 if(value.stable){$('max-tension').textContent=fmt(value.max_tension_kn)+' kN';$('max-compression').textContent='−'+fmt(value.max_compression_kn)+' kN';$('max-displacement').textContent=fmt(value.max_displacement_mm)+' mm';}
 $('download-stage').disabled=false;updateDeformation();selectionDetail();history();draw();return value;
 }catch(error){if(token!==requestId||rev!==revision)return null;current=null;badge('ERROR','error');$('message').textContent=error.message;updateDeformation();selectionDetail();draw();return null;}
}
function table(rows){const t=document.createElement('table');for(const [a,b] of rows){const r=t.insertRow(),th=document.createElement('th');th.scope='row';th.textContent=a;r.append(th);r.insertCell().textContent=b;}return t;}
function selectionDetail(){
 const box=$('selection-detail');box.replaceChildren();if(!selected||!geometry){box.textContent='Selecciona una barra instalada o un apoyo.';return;}
 const id=+selected.slice(1),isBar=selected[0]==='b',title=document.createElement('strong');title.textContent=(isBar?'Barra ':'Apoyo · nodo ')+id;box.append(title);
 const active=new Set(plan[currentStage]?.active_bar_ids||[]);
 if(isBar&&!active.has(id)){box.append(document.createTextNode(' · pendiente de instalar; sin peso ni rigidez en esta etapa.'));return;}
 if(!current?.stable){box.append(document.createTextNode(' · sin resultados de fuerzas: '+(current?.message||'cálculo pendiente.')));return;}
 if(isBar){const e=current.elements.find(e=>e.id===id);if(!e)return;const s=e.stations;box.append(table([['Nodos',e.i+' → '+e.j],['Longitud',fmt(e.length_m)+' m'],['Axial i / centro / j',[s[0],s[Math.floor(s.length/2)],s[s.length-1]].map(v=>fmt(v.N_Vy_Vz_T_My_Mz[0]/1000)).join(' / ')+' kN'],['Momentos My / Mz al centro',s[Math.floor(s.length/2)].N_Vy_Vz_T_My_Mz.slice(4).map(v=>fmt(v/1000)).join(' / ')+' kN·m']]));}
 else{const r=current.reactions.find(r=>r.node_id===id);if(!r){box.append(document.createTextNode(' · sin barras activas conectadas.'));return;}box.append(table([['Rx / Ry / Rz',r.values.slice(0,3).map(v=>fmt(v/1000)).join(' / ')+' kN'],['Mx / My / Mz',r.values.slice(3).map(v=>fmt(v/1000)).join(' / ')+' kN·m']]));}
}
function history(){const div=$('stage-history');div.replaceChildren();const t=document.createElement('table'),head=t.insertRow();for(const label of ['Etapa','Barras','Estado','Tracción (kN)','Compresión (kN)']){const th=document.createElement('th');th.textContent=label;head.append(th);}for(const s of plan){const r=calculated.get(s.stage),tr=t.insertRow();for(const value of [s.stage,s.active_count,r?({stable:'Equilibrio',unstable:'Mecanismo',empty:'Sin barras',error:'Error'}[r.status]):'Pendiente',r?.stable?fmt(r.max_tension_kn):'—',r?.stable?fmt(r.max_compression_kn):'—'])tr.insertCell().textContent=value;}div.append(t);}
function deformationView(){
 return DomeDeformation.view(geometry,current,$('show-deformation').checked,+$('deformation-factor').value);
}
function updateReactions(){
 const available=!!current?.stable&&current.reactions.length>0,show=$('show-reactions').checked&&available;
 $('show-reactions').disabled=!available;
 $('reaction-panel').hidden=!show;
 $('reaction-mode').disabled=!show;
 $('reaction-legend').hidden=!show||$('reaction-mode').value!=='components';
 $('reaction-note').textContent=!available?'Reacciones no disponibles sin equilibrio de esta etapa.':show?'Vectores en ejes globales · escala común independiente de la deformada. Selecciona un apoyo para ver sus etiquetas.':'Reacciones ocultas.';
 const box=$('reaction-table');box.replaceChildren();
 if(!show)return;
 const t=document.createElement('table'),head=t.insertRow();
 for(const label of ['Nodo','Rx','Ry','Rz','Mx','My','Mz']){const th=document.createElement('th');th.scope='col';th.textContent=label;head.append(th);}
 for(const r of current.reactions){const row=t.insertRow();row.insertCell().textContent=r.node_id;for(const value of r.values)row.insertCell().textContent=fmt(value/1000);}
 box.append(t);
}
for(const id of ['show-reactions','reaction-mode'])$(id).addEventListener('input',()=>{updateReactions();draw();});
function drawReactions(){
 if(!$('show-reactions').checked||!current?.stable)return;
 // Una escala común para resultantes y componentes conserva sus proporciones.
 const max=Math.max(...current.reactions.map(r=>Math.hypot(...r.values.slice(0,3))),1e-12);
 const components=$('reaction-mode').value==='components';
 ctx.save();ctx.setLineDash([]);ctx.lineWidth=2;ctx.font='12px sans-serif';
 for(const r of current.reactions){
   const p=projected.get(r.node_id);if(!p)continue;
   const vectors=components?r.values.slice(0,3).map((value,i)=>({v:[0,1,2].map(j=>i===j?value:0),value,label:['Rx','Ry','Rz'][i],color:['#15803D','#DC2626','#2563EB'][i]})):[{v:r.values.slice(0,3),value:Math.hypot(...r.values.slice(0,3)),label:'R',color:'#087F8C'}];
   for(const [i,vector] of vectors.entries()){
     ctx.strokeStyle=vector.color;ctx.fillStyle=vector.color;
     const v=rotate(vector.v.map(x=>x/max*65)),dx=v[0],dy=-v[1],end=[p[0]+dx,p[1]+dy],length=Math.hypot(dx,dy);
     if(length>1){const a=Math.atan2(dy,dx);ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(...end);ctx.stroke();ctx.beginPath();ctx.moveTo(...end);ctx.lineTo(end[0]-7*Math.cos(a-.45),end[1]-7*Math.sin(a-.45));ctx.lineTo(end[0]-7*Math.cos(a+.45),end[1]-7*Math.sin(a+.45));ctx.closePath();ctx.fill();}
     // Anclar etiquetas en una lista junto al nodo para evitar solapes de componentes pequeños.
     if(selected==='s'+r.node_id){
       const text=vector.label+' · nodo '+r.node_id+' · '+fmt(vector.value/1000)+' kN',x=p[0]+12,y=p[1]-15-i*17;
       ctx.save();ctx.fillStyle='rgba(255,255,255,.92)';ctx.fillRect(x-3,y-12,ctx.measureText(text).width+6,16);ctx.restore();ctx.fillText(text,x,y);
     }
   }
 }
 ctx.restore();
}
function updateDeformation(){
 updateReactions();
 const state=deformationView(),factor=$('deformation-factor');
 $('show-deformation').disabled=!state.available;
 factor.disabled=!state.available||!$('show-deformation').checked;
 if(!state.available)$('deformation-note').textContent='Deformada no disponible sin equilibrio y desplazamientos de esta etapa.';
 else if(!state.factor_valid)$('deformation-note').textContent='Introduce un factor visual entre 0 y 100000.';
 else if(!state.enabled)$('deformation-note').textContent='Vista apagada · máximo real '+fmt(state.max_real_mm)+' mm.';
 else $('deformation-note').textContent='×'+fmt(state.factor)+' · máximo real '+fmt(state.max_real_mm)+' mm → dibujado '+fmt(state.max_drawn_mm)+' mm. Referencia tenue; barras rectas entre nodos desplazados.';
}
for(const id of ['show-deformation','deformation-factor'])$(id).addEventListener('input',()=>{updateDeformation();draw();});
function draw(){
 const w=canvas.clientWidth,h=canvas.clientHeight,dpr=window.devicePixelRatio||1;canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);deformedSegments=[];if(!geometry)return;
 const min=[0,1,2].map(i=>Math.min(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),max=[0,1,2].map(i=>Math.max(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),center=min.map((v,i)=>(v+max[i])/2),diameter=Math.max(.01,Math.hypot(...max.map((v,i)=>v-min[i]))),scale=Math.min(w-35,h-65)/diameter*zoom;
 projected=new Map(geometry.nodes.map(n=>{const p=rotate([n.x-center[0],n.y-center[1],n.z-center[2]]);return [n.id,[w/2+p[0]*scale,h/2-p[1]*scale,p[2]]];}));
 const active=new Set(plan[currentStage]?.active_bar_ids||[]),fresh=new Set(plan[currentStage]?.new_bar_ids||[]),deformation=deformationView();
 segments=geometry.bars.map(b=>({b,a:projected.get(b.i),z:projected.get(b.j)})).sort((a,b)=>(a.a[2]+a.z[2])-(b.a[2]+b.z[2]));
 for(const s of segments){ctx.globalAlpha=deformation.enabled ? 0.35 : 1;const installed=active.has(s.b.id),f=current?.stable?current.forces[s.b.id]:null;ctx.beginPath();ctx.moveTo(s.a[0],s.a[1]);ctx.lineTo(s.z[0],s.z[1]);ctx.setLineDash(installed?[]:[3,4]);ctx.strokeStyle=selected==='b'+s.b.id?'#000000':!installed?'#CACACA':fresh.has(s.b.id)?'#00C853':f===null||f===undefined?'#737373':f<0?'#EF4444':'#001B96';ctx.lineWidth=selected==='b'+s.b.id?4:installed?2:1;ctx.stroke();}
 ctx.globalAlpha=1;
 // Usar la misma cámara y escala de la referencia: el factor no se cancela con un autozoom.
 const deformedProjection=new Map();
 if(deformation.enabled){
   for(const [id,world] of deformation.points){const p=rotate(world.map((v,i)=>v-center[i]));deformedProjection.set(id,[w/2+p[0]*scale,h/2-p[1]*scale,p[2]]);}
   deformedSegments=geometry.bars.filter(b=>active.has(b.id)).map(b=>({b,a:deformedProjection.get(b.i),z:deformedProjection.get(b.j)})).sort((a,b)=>(a.a[2]+a.z[2])-(b.a[2]+b.z[2]));
   ctx.setLineDash([]);ctx.strokeStyle='#8B5CF6';
   for(const s of deformedSegments){ctx.lineWidth=selected==='b'+s.b.id?4:2.5;ctx.beginPath();ctx.moveTo(s.a[0],s.a[1]);ctx.lineTo(s.z[0],s.z[1]);ctx.stroke();}
 }
 ctx.setLineDash([]);for(const id of geometry.support_nodes){const p=projected.get(id);ctx.beginPath();ctx.arc(p[0],p[1],selected==='s'+id?7:4,0,2*Math.PI);ctx.fillStyle='#F59E0B';ctx.fill();}
 drawReactions();
 if(current?.worker_node!==null&&current?.worker_node!==undefined){const p=deformedProjection.get(current.worker_node)||projected.get(current.worker_node);ctx.fillStyle='#000000';ctx.font='12px sans-serif';ctx.fillText('↓ '+fmt(current.worker_load_N/1000)+' kN',p[0]+8,p[1]-8);}
}
$('element-select').addEventListener('change',()=>{selected=$('element-select').value;selectionDetail();draw();});
$('stage-slider').addEventListener('input',()=>{stop();clearTimeout(sliderTimer);const stage=+$('stage-slider').value;pendingStage(stage);sliderTimer=setTimeout(()=>setStage(stage),130);});
$('btn-prev').onclick=()=>{stop();setStage(currentStage-1);};$('btn-next').onclick=()=>{stop();setStage(currentStage+1);};
$('btn-play').onclick=async()=>{if(playing){stop();return;}playing=true;$('btn-play').textContent='⏸ Pausar';if(currentStage===plan.length-1)await setStage(0);while(playing&&currentStage<plan.length-1){const r=await setStage(currentStage+1);if(!r||!r.stable){stop();break;}await new Promise(r=>setTimeout(r,250));}stop();};
for(const id of ['sel-profile','sel-material','sel-connection','sel-support','worker-kg'])$(id).addEventListener('change',()=>replan());$('sel-step').addEventListener('change',()=>replan(true));
$('apply-supports').onclick=()=>{if(!geometry)return;geometry.support_nodes=Array.from($('support-nodes').selectedOptions,o=>+o.value);populateSupports();replan();};
async function importDXF(){const file=$('dxf-file-input').files[0];if(!file)return;const rev=++revision;stop();calculated.clear();geometry=null;plan=[];clearAnalysis();$('message').textContent='Revisando conectividad del DXF…';try{const value=await api('/api/import?units='+encodeURIComponent($('dxf-units').value)+'&tolerance='+encodeURIComponent(+$('dxf-tolerance').value/1000),null,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:await file.arrayBuffer()});if(rev!==revision)return;geometry=value.geometry;$('import-report').textContent=JSON.stringify(value.report,null,2);populateSupports();await replan(true);}catch(e){if(rev!==revision)return;badge('DXF NO VÁLIDO','error');$('message').textContent=e.message;}}
for(const id of ['dxf-file-input','dxf-units','dxf-tolerance'])$(id).addEventListener('change',importDXF);
$('download-stage').onclick=()=>{if(!current)return;const blob=new Blob([JSON.stringify({geometry,config:config(),result:current},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='etapa-'+currentStage+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,sx:e.clientX,sy:e.clientY});if(pointers.size===1)dragged=false;if(pointers.size===2){dragged=true;const a=[...pointers.values()];pinch={d:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y),zoom};}});
canvas.addEventListener('pointermove',e=>{const p=pointers.get(e.pointerId);if(!p)return;const dx=e.clientX-p.x,dy=e.clientY-p.y;p.x=e.clientX;p.y=e.clientY;if(Math.hypot(p.x-p.sx,p.y-p.sy)>4)dragged=true;if(pointers.size===2&&pinch){const a=[...pointers.values()];zoom=Math.max(.25,Math.min(10,pinch.zoom*Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y)/Math.max(1,pinch.d)));}else{const n=Math.hypot(dx,dy);if(n){const t=n*.004;q=normalize(mul([Math.cos(t),dy/n*Math.sin(t),dx/n*Math.sin(t),0],q));}}draw();});
canvas.addEventListener('pointerup',e=>{const click=!dragged&&pointers.size===1;pointers.delete(e.pointerId);pinch=null;if(!click||!geometry)return;const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;let value='',best=12;for(const id of geometry.support_nodes){const p=projected.get(id),d=Math.hypot(p[0]-x,p[1]-y);if(d<best){best=d;value='s'+id;}}if(!value){best=10;for(const s of [...segments,...deformedSegments]){const dx=s.z[0]-s.a[0],dy=s.z[1]-s.a[1],t=Math.max(0,Math.min(1,((x-s.a[0])*dx+(y-s.a[1])*dy)/(dx*dx+dy*dy||1))),d=Math.hypot(x-s.a[0]-t*dx,y-s.a[1]-t*dy);if(d<best){best=d;value='b'+s.b.id;}}}selected=value;$('element-select').value=value;selectionDetail();draw();});
canvas.addEventListener('pointercancel',e=>{pointers.delete(e.pointerId);pinch=null;});canvas.style.touchAction='none';canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.25,Math.min(10,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});new ResizeObserver(draw).observe(canvas);
(async()=>{try{const c=await api('/api/catalog');for(const item of c.profiles)$('sel-profile').append(new Option(item,item));$('sel-profile').selectedIndex=2;for(const item of c.materials)$('sel-material').append(new Option(item,item));geometry=await api('/api/demo');populateSupports();await replan(true);}catch(e){badge('MOTOR NO DISPONIBLE','error');$('message').textContent=e.message+' · Inicia PYTHONPATH=src python -m domestage.server';}})();
})();
