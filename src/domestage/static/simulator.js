'use strict';
(()=>{
const $=id=>document.getElementById(id), canvas=$('viewport'), ctx=canvas.getContext('2d');
let geometry=null, plan=[], currentStage=0, current=null, revision=0, requestId=0, playing=false, selected='', segments=[], projected=new Map(), deformedSegments=[];
const calculated=new Map(); let series=null, seriesToken=0; let q=normalize([.87,-.35,.12,.32]), zoom=1; const pointers=new Map(); let dragged=false, pinch=null, sliderTimer;
let supportOverrides = {}; // {node_id: 'articulado' | 'empotrado'}

const fmt=(x,n=3)=>Number(x).toLocaleString('en-US',{maximumFractionDigits:n});
function normalize(a){const n=Math.hypot(...a);return a.map(v=>v/n);}
function mul(a,b){return [a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]];}
function rotate(p){return mul(mul(q,[0,...p]),[q[0],-q[1],-q[2],-q[3]]).slice(1);}

async function api(path,data,options={}){
 const response=await fetch(path,{...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{}),...options});
 let value;try{value=await response.json();}catch{throw Error('Calculation server not found. Ensure server is running.');}
 if(!response.ok)throw Error(value.message||'Calculation engine error.');return value;
}

function config(){
  return {
    material: $('sel-material').value,
    profile: $('sel-profile').value,
    connection: $('sel-connection').value,
    support: $('sel-support').value,
    bars_per_step: +$('sel-step').value,
    support_overrides: supportOverrides
  };
}

function stop(){clearTimeout(sliderTimer);playing=false;$('btn-play').textContent='▶ Play Assembly';}

function clearAnalysis(){
  ++requestId; current=null;
  $('download-stage').disabled=true;
  $('max-tension').textContent='—'; $('max-compression').textContent='—';
  $('max-displacement').textContent='—'; $('installed-weight').textContent='—';
  badge('CALCULATING','pending'); updateDeformation(); selectionDetail(); draw();
}

function badge(label,status){
  $('status-badge').textContent=label;
  $('status-badge').className='badge badge-'+(status==='stable'?'stable':status==='unstable'||status==='error'?'unstable':'pending');
}

function populateSupports(){
  $('element-select').replaceChildren(new Option('Click member or select here…',''));
  for(const b of geometry.bars)$('element-select').append(new Option('Bar #'+b.id,'b'+b.id));
  for(const n of geometry.support_nodes)$('element-select').append(new Option('Support node '+n,'s'+n));
  selected=''; $('element-select').value='';
}

async function replan(reset=false){
  const rev=++revision; stop(); calculated.clear(); clearCharts();
  $('stage-history').textContent='Pending calculation.'; clearAnalysis();
  if(!geometry){$('message').textContent='Load a valid geometry model.'; return;}
  $('message').textContent='Planning stage assembly sequence…';
  try{
    const p=await api('/api/plan',{geometry,bars_per_step:config().bars_per_step});
    if(rev!==revision)return; plan=p;
    $('stage-slider').max=plan.length-1; $('last-stage').textContent=plan.length-1;
    await setStage(reset?0:Math.min(currentStage,plan.length-1));
  }catch(error){
    if(rev!==revision)return; badge('ERROR','error'); $('message').textContent=error.message;
  }
}

function pendingStage(stage){
  currentStage=stage; clearAnalysis(); const s=plan[stage]; if(!s)return;
  $('stage-slider').value=stage; $('stage-num').textContent=stage;
  $('active-bars-count').textContent=s.active_count; $('total-bars-count').textContent=s.total_bars;
  $('progress-text').textContent=fmt(s.progress_pct,1)+'%'; $('progress-fill').style.width=s.progress_pct+'%';
  $('newest-bar-text').textContent=s.new_bar_ids.length ? s.new_bar_ids.map(i=>'Bar #'+i).join(', ') : 'Base Ring Installed';
  draw();
}

async function setStage(stage){
  if(!plan.length)return; stage=Math.max(0,Math.min(stage,plan.length-1)); pendingStage(stage);
  const token=++requestId, rev=revision;
  $('message').textContent='Solving equilibrium for Stage '+stage+'…'; badge('SOLVING…','pending');
  try{
    const value=calculated.get(stage)||await api('/api/stage',{geometry,config:config(),stage});
    if(token!==requestId||rev!==revision)return null;
    calculated.set(stage,value); current=value;
    badge(value.status==='stable'?'STABLE EQUILIBRIUM':value.status==='unstable'?'MECHANISM / UNSTABLE':value.status==='empty'?'NO BARS':'ERROR',value.status);
    $('message').textContent=value.message;
    $('installed-weight').textContent=fmt(value.mass_kg*9.80665/1000)+' kN ('+fmt(value.mass_kg,1)+' kg)';
    if(value.stable){
      $('max-tension').textContent='+'+fmt(value.max_tension_kn)+' kN';
      $('max-compression').textContent='−'+fmt(value.max_compression_kn)+' kN';
      $('max-displacement').textContent=fmt(value.max_displacement_mm)+' mm';
    }
    $('download-stage').disabled=false; updateDeformation(); selectionDetail(); history(); draw(); renderCharts(); return value;
  }catch(error){
    if(token!==requestId||rev!==revision)return null; current=null;
    badge('ERROR','error'); $('message').textContent=error.message; updateDeformation(); selectionDetail(); draw(); return null;
  }
}

function table(rows){
  const t=document.createElement('table');
  for(const [a,b] of rows){
    const r=t.insertRow(), th=document.createElement('th');
    th.scope='row'; th.textContent=a; r.append(th); r.insertCell().textContent=b;
  }
  return t;
}

function selectionDetail(){
  const box=$('selection-detail'); box.replaceChildren();
  if(!selected||!geometry){box.textContent='Click any installed member or support node in the 3D model to inspect its forces.'; return;}
  const id=+selected.slice(1), isBar=selected[0]==='b', title=document.createElement('strong');
  title.textContent=(isBar?'Member #':'Support Node #')+id; box.append(title);
  const active=new Set(plan[currentStage]?.active_bar_ids||[]);
  if(isBar&&!active.has(id)){box.append(document.createTextNode(' · Pending installation (inactive in this stage).')); return;}
  if(!current?.stable){box.append(document.createTextNode(' · No force solution available: '+(current?.message||'Pending.'))); return;}
  if(isBar){
    const e=current.elements.find(e=>e.id===id); if(!e)return; const s=e.stations;
    box.append(table([
      ['End Nodes', e.i+' → '+e.j],
      ['Bar Length', fmt(e.length_m)+' m'],
      ['Axial Force (i / mid / j)', [s[0], s[Math.floor(s.length/2)], s[s.length-1]].map(v=>fmt(v.N_Vy_Vz_T_My_Mz[0]/1000)).join(' / ')+' kN'],
      ['Bending Moment My / Mz (mid)', s[Math.floor(s.length/2)].N_Vy_Vz_T_My_Mz.slice(4).map(v=>fmt(v/1000)).join(' / ')+' kN·m']
    ]));
  }else{
    const r=current.reactions.find(r=>r.node_id===id);
    const cond = supportOverrides[id] || config().support;
    if(!r){box.append(document.createTextNode(' · No active connected members yet.')); return;}
    const rows=[
      ['Boundary Condition', cond==='empotrado'?'Fixed (6 DOFs)':'Pinned (3 DOFs)'],
      ['Reactions Rx / Ry / Rz', r.values.slice(0,3).map(v=>fmt(v/1000)).join(' / ')+' kN'],
      ['Moments Mx / My / Mz', r.values.slice(3).map(v=>fmt(v/1000)).join(' / ')+' kN·m']
    ];
    if(window.DomeReactions){
      const center=window.DomeReactions.center(geometry);
      const cyl=window.DomeReactions.cylindrical(geometry.nodes.find(n=>n.id===id),r.values,center);
      if(cyl)rows.push(['Radial / Tangential / Z',[cyl.values[0],cyl.values[1],cyl.values[2]].map(v=>fmt(v/1000)).join(' / ')+' kN']);
    }
    box.append(table(rows));
  }
}

function history(){
  const div=$('stage-history'); div.replaceChildren();
  const t=document.createElement('table'), head=t.insertRow();
  for(const label of ['Stage','Active Bars','Status','Max Tension (kN)','Max Compression (kN)']){
    const th=document.createElement('th'); th.textContent=label; head.append(th);
  }
  for(const s of plan){
    const r=calculated.get(s.stage), tr=t.insertRow();
    for(const value of [s.stage, s.active_count, r?({stable:'Equilibrium',unstable:'Mechanism',empty:'No bars',error:'Error'}[r.status]):'Pending', r?.stable?fmt(r.max_tension_kn):'—', r?.stable?fmt(r.max_compression_kn):'—']){
      tr.insertCell().textContent=value;
    }
  }
  div.append(t);
}

// PR 11 Deformation & Reactions integration
function deformationView(){
  if(!window.DomeDeformation) return {available:false, enabled:false, points:new Map()};
  return window.DomeDeformation.view(geometry, current, $('show-deformation').checked, +$('deformation-factor').value);
}

function updateReactions(){
  const available=Boolean(current?.stable&&current.reactions?.length), show=$('show-reactions').checked&&available;
  $('show-reactions').disabled=!available;
  $('reaction-panel').hidden=!show;
  $('reaction-mode').disabled=!show;
  const radial=$('reaction-mode').value==='cylindrical';
  $('reaction-legend').hidden=!show||$('reaction-mode').value==='total';
  const legend=$('reaction-legend').querySelectorAll('span');
  if(legend.length===3){
    ['#15803D','#DC2626','#2563EB'].forEach((color,i)=>{
      legend[i].textContent=(radial?['Rr','Rt','Rz']:['X','Y','Z'])[i]+' · '+['Green','Red','Blue'][i];
    });
  }
  $('reaction-note').textContent=!available?'Reactions unavailable without stable solution.':
    show?'Reaction vectors in global axes. Select a support to view values.':'Support reaction vectors hidden.';
  if(show&&radial&&window.DomeReactions){
    const c=window.DomeReactions.center(geometry);
    if(c)$('reaction-note').textContent=`Support center in XY: (${fmt(c[0])}, ${fmt(c[1])}) m · Rr: radial outwards, Rt: tangential CCW.`;
  }
  reactionTable(show, radial);
}

function reactionTable(show, radial){
  const panel=$('reaction-panel'), div=$('reaction-table'); div.replaceChildren();
  if(!show||!current?.reactions?.length){panel.hidden=true; return;}
  panel.hidden=false;
  const t=document.createElement('table'), head=t.insertRow();
  for(const label of ['Node',...(radial?['Rr','Rt','Rz']:['Rx','Ry','Rz']),'Mx (kN·m)','My (kN·m)','Mz (kN·m)']){
    const th=document.createElement('th'); th.scope='col'; th.textContent=label; head.append(th);
  }
  const center=window.DomeReactions?window.DomeReactions.center(geometry):null;
  for(const r of current.reactions){
    const row=t.insertRow(); row.insertCell().textContent=r.node_id;
    const converted=radial&&window.DomeReactions?window.DomeReactions.cylindrical(geometry.nodes.find(n=>n.id===r.node_id),r.values,center):null;
    const values=radial?[...(converted?.values||[null,null,r.values[2]]),...r.values.slice(3)]:r.values;
    for(const value of values)row.insertCell().textContent=value===null?'N/A':fmt(value/1000);
  }
  div.append(t);
}

function updateDeformation(){
  updateReactions();
  const state=deformationView(), factor=$('deformation-factor');
  $('show-deformation').disabled=!state.available;
  factor.disabled=!state.available||!$('show-deformation').checked;
  if(!state.available)$('deformation-note').textContent='Deflection view unavailable without stage equilibrium and displacements.';
  else if(!state.factor_valid)$('deformation-note').textContent='Enter a visual scale factor between 0 and 100000.';
  else if(!state.enabled)$('deformation-note').textContent='Deflection view off · Max true displacement: '+fmt(state.max_real_mm)+' mm.';
  else $('deformation-note').textContent='Amplified ×'+fmt(state.factor)+' · Real max '+fmt(state.max_real_mm)+' mm → Visual '+fmt(state.max_drawn_mm)+' mm.';
}

function drawReactions(){
  if(!$('show-reactions').checked||!current?.stable||!window.DomeReactions)return;
  const max=Math.max(...current.reactions.map(r=>Math.hypot(...r.values.slice(0,3))),1e-12);
  const mode=$('reaction-mode').value, origin=window.DomeReactions.center(geometry);
  ctx.save(); ctx.setLineDash([]); ctx.lineWidth=2; ctx.font='11px sans-serif';
  for(const r of current.reactions){
    const p=projected.get(r.node_id); if(!p)continue;
    let vectors;
    if(mode==='cylindrical'){
      const c=window.DomeReactions.cylindrical(geometry.nodes.find(n=>n.id===r.node_id),r.values,origin);
      vectors=c?c.values.map((value,i)=>({v:c.vectors[i],value,label:['Rr','Rt','Rz'][i],color:['#15803D','#DC2626','#2563EB'][i]})):[{v:[0,0,r.values[2]],value:r.values[2],label:'Rz',color:'#2563EB'}];
    } else vectors=mode==='components'?r.values.slice(0,3).map((value,i)=>({v:[0,1,2].map(j=>i===j?value:0),value,label:['Rx','Ry','Rz'][i],color:['#15803D','#DC2626','#2563EB'][i]})):[{v:r.values.slice(0,3),value:Math.hypot(...r.values.slice(0,3)),label:'R',color:'#001B96'}];

    for(const [i,vector] of vectors.entries()){
      ctx.strokeStyle=vector.color; ctx.fillStyle=vector.color;
      const v=rotate(vector.v.map(x=>x/max*65)), dx=v[0], dy=-v[1], end=[p[0]+dx, p[1]+dy], length=Math.hypot(dx,dy);
      if(length>1){
        const a=Math.atan2(dy,dx); ctx.beginPath(); ctx.moveTo(p[0],p[1]); ctx.lineTo(...end); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(...end); ctx.lineTo(end[0]-7*Math.cos(a-.45), end[1]-7*Math.sin(a-.45)); ctx.lineTo(end[0]-7*Math.cos(a+.45), end[1]-7*Math.sin(a+.45)); ctx.closePath(); ctx.fill();
      }
      if(selected==='s'+r.node_id){
        const text=vector.label+' · Node '+r.node_id+' · '+fmt(vector.value/1000)+' kN', x=p[0]+12, y=p[1]-15-i*17;
        ctx.save(); ctx.fillStyle='rgba(255,255,255,.94)'; ctx.fillRect(x-3,y-12,ctx.measureText(text).width+6,16); ctx.restore(); ctx.fillText(text,x,y);
      }
    }
  }
  ctx.restore();
}

// 3D Canvas Rendering
function draw(){
  const w=canvas.clientWidth, h=canvas.clientHeight, dpr=window.devicePixelRatio||1;
  canvas.width=w*dpr; canvas.height=h*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle='#FFFFFF'; ctx.fillRect(0,0,w,h);
  deformedSegments=[]; if(!geometry)return;

  const min=[0,1,2].map(i=>Math.min(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),
        max=[0,1,2].map(i=>Math.max(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),
        center=min.map((v,i)=>(v+max[i])/2),
        diameter=Math.max(.01,Math.hypot(...max.map((v,i)=>v-min[i]))),
        scale=Math.min(w-35,h-65)/diameter*zoom;

  projected=new Map(geometry.nodes.map(n=>{
    const p=rotate([n.x-center[0],n.y-center[1],n.z-center[2]]);
    return [n.id,[w/2+p[0]*scale, h/2-p[1]*scale, p[2]]];
  }));

  const deformation=deformationView();
  const active=new Set(plan[currentStage]?.active_bar_ids||[]), fresh=new Set(plan[currentStage]?.new_bar_ids||[]);
  segments=geometry.bars.map(b=>({b, a:projected.get(b.i), z:projected.get(b.j)})).sort((a,b)=>(a.a[2]+a.z[2])-(b.a[2]+b.z[2]));

  // 1. Ghost & Installed Bars
  for(const s of segments){
    ctx.globalAlpha=deformation.enabled ? 0.35 : 1;
    const installed=active.has(s.b.id), f=current?.stable?current.forces[s.b.id]:null;
    ctx.beginPath(); ctx.moveTo(s.a[0],s.a[1]); ctx.lineTo(s.z[0],s.z[1]);
    ctx.setLineDash(installed?[]:[3,4]);
    ctx.strokeStyle=selected==='b'+s.b.id?'#000000':!installed?'#CACACA':fresh.has(s.b.id)?'#00C853':f===null||f===undefined?'#737373':f<0?'#EF4444':'#001B96';
    ctx.lineWidth=selected==='b'+s.b.id?4.5:installed?2.2:1.0;
    ctx.stroke();
  }
  ctx.globalAlpha=1;

  // 2. Amplified Deflection wireframe
  const deformedProjection=new Map();
  if(deformation.enabled){
    for(const [id,world] of deformation.points){
      const p=rotate(world.map((v,i)=>v-center[i]));
      deformedProjection.set(id,[w/2+p[0]*scale, h/2-p[1]*scale, p[2]]);
    }
    deformedSegments=geometry.bars.filter(b=>active.has(b.id)).map(b=>({b, a:deformedProjection.get(b.i), z:deformedProjection.get(b.j)})).sort((a,b)=>(a.a[2]+a.z[2])-(b.a[2]+b.z[2]));
    ctx.setLineDash([]); ctx.strokeStyle='#7C3AED';
    for(const s of deformedSegments){
      ctx.lineWidth=selected==='b'+s.b.id?4.5:2.5;
      ctx.beginPath(); ctx.moveTo(s.a[0],s.a[1]); ctx.lineTo(s.z[0],s.z[1]); ctx.stroke();
    }
  }

  // 3. Base Support nodes
  ctx.setLineDash([]);
  for(const id of geometry.support_nodes){
    const p=projected.get(id);
    ctx.beginPath(); ctx.arc(p[0],p[1],selected==='s'+id?7.5:4.5,0,2*Math.PI);
    ctx.fillStyle='#F59E0B'; ctx.fill();
  }

  // 4. Reactions vectors from PR 11
  drawReactions();
}

// Interaction Listeners
$('element-select').addEventListener('change',()=>{selected=$('element-select').value; selectionDetail(); draw();});
$('stage-slider').addEventListener('input',()=>{stop(); clearTimeout(sliderTimer); const stage=+$('stage-slider').value; pendingStage(stage); sliderTimer=setTimeout(()=>setStage(stage),130);});
$('btn-prev').onclick=()=>{stop(); setStage(currentStage-1);};
$('btn-next').onclick=()=>{stop(); setStage(currentStage+1);};
$('btn-play').onclick=async()=>{
  if(playing){stop(); return;}
  playing=true; $('btn-play').textContent='⏸ Pause';
  if(currentStage===plan.length-1)await setStage(0);
  while(playing&&currentStage<plan.length-1){
    const r=await setStage(currentStage+1);
    if(!r||!r.stable){stop(); break;}
    await new Promise(r=>setTimeout(r,250));
  }
  stop();
};

for(const id of ['sel-profile','sel-material','sel-connection','sel-support'])$(id).addEventListener('change',()=>replan());
$('sel-step').addEventListener('change',()=>replan(true));
$('show-deformation').addEventListener('change',()=>{updateDeformation(); draw();});
$('deformation-factor').addEventListener('input',()=>{updateDeformation(); draw();});
$('show-reactions').addEventListener('change',()=>{updateDeformation(); draw();});
$('reaction-mode').addEventListener('change',()=>{updateDeformation(); draw();});

// CSV Export & Import for Node Connection Conditions
$('btn-export-csv').onclick=()=>{
  if(!geometry)return;
  const defSupport = $('sel-support').value;
  let csv = 'node_id,x,y,z,support_type\n';
  for(const n of geometry.nodes){
    const isSup = geometry.support_nodes.includes(n.id);
    const cond = supportOverrides[n.id] || (isSup ? defSupport : 'free');
    csv += `${n.id},${n.x.toFixed(4)},${n.y.toFixed(4)},${n.z.toFixed(4)},${cond}\n`;
  }
  const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = 'node_connections.csv'; a.click();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
};

$('csv-import-input').addEventListener('change', function(e){
  const file = e.target.files[0];
  if(!file)return;
  const reader = new FileReader();
  reader.onload = function(evt){
    try {
      const lines = evt.target.result.split(/\r?\n/);
      const newSupports = [];
      supportOverrides = {};
      for(let i=1; i<lines.length; i++){
        const row = lines[i].split(',').map(s=>s.trim());
        if(row.length >= 5){
          const nid = parseInt(row[0]);
          const stype = row[4].toLowerCase();
          if(['articulado', 'pinned', 'pin'].includes(stype)){
            supportOverrides[nid] = 'articulado';
            newSupports.push(nid);
          } else if(['empotrado', 'fixed', 'fix'].includes(stype)){
            supportOverrides[nid] = 'empotrado';
            newSupports.push(nid);
          }
        }
      }
      if(newSupports.length > 0){
        geometry.support_nodes = [...new Set(newSupports)];
        populateSupports();
        replan();
        alert(`✓ Loaded connection overrides for ${newSupports.length} support nodes from CSV.`);
      }
    } catch(err){
      alert('Error parsing CSV: ' + err.message);
    }
  };
  reader.readAsText(file);
});

async function importDXF(){
  const file=$('dxf-file-input').files[0]; if(!file)return;
  const rev=++revision; stop(); calculated.clear(); clearCharts(); geometry=null; plan=[]; clearAnalysis();
  supportOverrides={}; $('message').textContent='Reading DXF wireframe connectivity…';
  try{
    const value=await api('/api/import?units='+encodeURIComponent($('dxf-units').value)+'&tolerance='+encodeURIComponent(+$('dxf-tolerance').value/1000),null,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:await file.arrayBuffer()});
    if(rev!==revision)return; geometry=value.geometry;
    populateSupports(); await replan(true);
  }catch(e){
    if(rev!==revision)return; badge('INVALID DXF','error'); $('message').textContent=e.message;
  }
}
for(const id of ['dxf-file-input','dxf-units','dxf-tolerance'])$(id).addEventListener('change',importDXF);

$('download-stage').onclick=()=>{
  if(!current)return;
  const blob=new Blob([JSON.stringify({geometry,config:config(),result:current},null,2)],{type:'application/json'}), url=URL.createObjectURL(blob), a=document.createElement('a');
  a.href=url; a.download='stage-'+currentStage+'-results.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
};

// Canvas Navigation Drag / Zoom
canvas.addEventListener('pointerdown',e=>{
  canvas.setPointerCapture(e.pointerId); pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,sx:e.clientX,sy:e.clientY});
  if(pointers.size===1)dragged=false;
  if(pointers.size===2){dragged=true; const a=[...pointers.values()]; pinch={d:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y),zoom};}
});
canvas.addEventListener('pointermove',e=>{
  const p=pointers.get(e.pointerId); if(!p)return;
  const dx=e.clientX-p.x, dy=e.clientY-p.y; p.x=e.clientX; p.y=e.clientY;
  if(Math.hypot(p.x-p.sx,p.y-p.sy)>4)dragged=true;
  if(pointers.size===2&&pinch){const a=[...pointers.values()]; zoom=Math.max(.25,Math.min(10,pinch.zoom*Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y)/Math.max(1,pinch.d)));}
  else{const n=Math.hypot(dx,dy); if(n){const t=n*.004; q=normalize(mul([Math.cos(t),dy/n*Math.sin(t),dx/n*Math.sin(t),0],q));}}
  draw();
});
canvas.addEventListener('pointerup',e=>{
  const click=!dragged&&pointers.size===1; pointers.delete(e.pointerId); pinch=null;
  if(!click||!geometry)return;
  const r=canvas.getBoundingClientRect(), x=e.clientX-r.left, y=e.clientY-r.top;
  let value='', best=12;
  for(const id of geometry.support_nodes){
    const p=projected.get(id), d=Math.hypot(p[0]-x,p[1]-y);
    if(d<best){best=d; value='s'+id;}
  }
  if(!value){
    best=10;
    for(const s of [...segments,...deformedSegments]){
      const dx=s.z[0]-s.a[0], dy=s.z[1]-s.a[1], t=Math.max(0,Math.min(1,((x-s.a[0])*dx+(y-s.a[1])*dy)/(dx*dx+dy*dy||1))), d=Math.hypot(x-s.a[0]-t*dx,y-s.a[1]-t*dy);
      if(d<best){best=d; value='b'+s.b.id;}
    }
  }
  selected=value; $('element-select').value=value; selectionDetail(); draw();
});
canvas.addEventListener('pointercancel',e=>{pointers.delete(e.pointerId);pinch=null;});
canvas.style.touchAction='none';
canvas.addEventListener('wheel',e=>{e.preventDefault(); zoom=Math.max(.25,Math.min(10,zoom*Math.exp(-e.deltaY*.001))); draw();},{passive:false});
new ResizeObserver(draw).observe(canvas);

const SVG='http://www.w3.org/2000/svg';
function el(tag,attrs={},text){const e=document.createElementNS(SVG,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
function niceMax(v){if(!(v>0))return 1;const p=10**Math.floor(Math.log10(v)),m=v/p;return (m<=1?1:m<=2?2:m<=5?5:10)*p;}
function clearCharts(){++seriesToken;series=null;$('btn-charts-csv').disabled=true;$('btn-charts').disabled=false;$('charts-message').textContent='Compute all stages to see how the maximum axial force and maximum deflection change as assembly progresses.';renderCharts();}
const OUTLIER_FACTOR=20;
function median(v){const a=[...v].sort((x,y)=>x-y),m=a.length>>1;return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function chart(svg,lines,unit,emptyText){
 svg.replaceChildren();const W=600,H=340,L=62,R=16,T=18,B=86,pw=W-L-R,ph=H-T-B;
 const useLog=$('chart-log').checked,useClip=$('chart-clip').checked;
 const x=p=>L+p/100*pw;
 const values=series?series.flatMap(s=>lines.map(l=>s[l.key])).filter(v=>v!==null&&v!==undefined&&Number.isFinite(v)):[];
 const positive=values.filter(v=>v>0);
 // Recorte: el eje se limita a OUTLIER_FACTOR × la mediana de los valores positivos.
 let cap=Infinity;
 if(useClip&&positive.length){const c=OUTLIER_FACTOR*median(positive);if(Math.max(...positive)>c)cap=c;}
 const inRange=values.filter(v=>v<=cap),dataMax=inRange.length?Math.max(...inRange):0;
 let edge=Infinity;
 let y,ticks;
 if(useLog&&positive.length){
  const pin=positive.filter(v=>v<=cap),lo=10**Math.floor(Math.log10(Math.min(...(pin.length?pin:positive)))),hi=10**Math.ceil(Math.log10(Math.max(dataMax,lo*10)));
  if(cap<Infinity)edge=hi;
  const span=Math.log10(hi)-Math.log10(lo);
  y=v=>T+ph-(Math.log10(Math.max(v,lo))-Math.log10(lo))/span*ph;
  ticks=[];for(let e=Math.log10(lo);e<=Math.log10(hi)+1e-9;e++)ticks.push(10**e);
 }else{
  const top=niceMax(dataMax*1.05);if(cap<Infinity)edge=top;
  y=v=>T+ph-Math.min(v,top)/top*ph;ticks=[0,1,2,3,4,5].map(i=>top*i/5);
 }
 for(const v of ticks)svg.append(el('line',{x1:L,x2:W-R,y1:y(v),y2:y(v),class:'chart-grid'}),el('text',{x:L-6,y:y(v)+4,'text-anchor':'end',class:'chart-label'},fmt(v,v<10?2:1)));
 if(edge<Infinity)svg.append(el('line',{x1:L,x2:W-R,y1:T,y2:T,stroke:'#F59E0B','stroke-width':1.5,'stroke-dasharray':'2 3'}));
 const yc=v=>v>cap?T:y(v);
 for(const p of [0,25,50,75,100])svg.append(el('line',{x1:x(p),x2:x(p),y1:T,y2:T+ph,class:'chart-grid'}),el('text',{x:x(p),y:T+ph+16,'text-anchor':'middle',class:'chart-label'},p+'%'));
 svg.append(el('line',{x1:L,x2:L,y1:T,y2:T+ph,class:'chart-axis'}),el('line',{x1:L,x2:W-R,y1:T+ph,y2:T+ph,class:'chart-axis'}));
 svg.append(el('text',{x:L+pw/2,y:T+ph+34,'text-anchor':'middle',class:'chart-title'},'Assembly progress (% of bars installed)'));
 svg.append(el('text',{x:14,y:T+ph/2,'text-anchor':'middle',class:'chart-title',transform:`rotate(-90 14 ${T+ph/2})`},unit+(useLog?' · log':'')));
 if(!series){svg.append(el('text',{x:L+pw/2,y:T+ph/2,'text-anchor':'middle',class:'chart-label'},emptyText));return 0;}
 let clipped=0;
 for(const l of lines){
  let d='';let pen=false;
  for(const s of series){const v=s[l.key];if(v===null||v===undefined){pen=false;continue;}d+=(pen?'L':'M')+x(s.progress_pct).toFixed(1)+' '+yc(v).toFixed(1)+' ';pen=true;}
  if(d)svg.append(el('path',{d,fill:'none',stroke:l.color,'stroke-width':l.width||2,'stroke-opacity':l.opacity||1,'stroke-linejoin':'round'}));
  for(const s of series){const v=s[l.key];if(v===null||v===undefined)continue;const px=x(s.progress_pct),label=`${l.label} · stage ${s.stage} · ${fmt(s.progress_pct,1)}% · ${fmt(v)} ${l.unit}`;
   if(v>cap){if(l.width>3)continue;clipped++;const m=el('path',{d:`M${px-5} ${T+7} L${px+5} ${T+7} L${px} ${T-3} Z`,fill:'#F59E0B',stroke:'#B45309','stroke-width':1});m.append(el('title',{},label+' (off scale, clipped)'));svg.append(m);continue;}
   const c=el('circle',{cx:px,cy:y(v),r:l.width>3?0:2.6,fill:l.color});c.append(el('title',{},label));svg.append(c);}
 }
 for(const s of series)if(s.status!=='stable'&&s.status!=='empty'){const m=el('path',{d:`M${x(s.progress_pct)-4} ${T+ph+1} L${x(s.progress_pct)+4} ${T+ph+1} L${x(s.progress_pct)} ${T+ph-7} Z`,fill:'#EF4444'});m.append(el('title',{},`Stage ${s.stage} · ${fmt(s.progress_pct,1)}% · ${s.status==='unstable'?'mechanism: no solution':'error'}`));svg.append(m);}
 // Marker (not data): where the stage chosen with the slider sits on the progress axis.
 const cur=plan[currentStage];if(cur){const cx=x(cur.progress_pct),right=cx<L+pw-80;
  svg.append(el('line',{x1:cx,x2:cx,y1:T,y2:T+ph,stroke:'#00C853','stroke-width':2,'stroke-dasharray':'5 4'}));
  svg.append(el('text',{x:right?cx+5:cx-5,y:T+12,'text-anchor':right?'start':'end','font-size':11,'font-weight':700,fill:'#00873A'},`Stage ${cur.stage} · ${fmt(cur.progress_pct,1)}%`));}
 const legend=[...lines.filter(l=>!l.hideLegend),{label:'Stage without solution',color:'#EF4444',marker:true},...(clipped?[{label:`Clipped (> ${fmt(cap,1)} ${lines[0].unit})`,color:'#F59E0B',marker:true}]:[]),{label:'Selected stage (slider)',color:'#00C853',dash:true}];
 // Leyenda en filas debajo del eje X: nunca tapa los datos.
 let gx=L,ly=T+ph+52;
 for(const l of legend){const w=30+l.label.length*6.2;if(gx+w>W-R){gx=L;ly+=17;}
  svg.append(l.marker?el('path',{d:`M${gx} ${ly+4} L${gx+10} ${ly+4} L${gx+5} ${ly-4} Z`,fill:l.color}):el('line',{x1:gx,x2:gx+16,y1:ly,y2:ly,stroke:l.color,'stroke-width':Math.min(l.width||2,6),'stroke-dasharray':l.dash?'5 4':'','stroke-opacity':l.opacity?Math.max(l.opacity,.35):1}));
  svg.append(el('text',{x:gx+22,y:ly+4,class:'chart-label'},l.label));gx+=w;}
 return clipped;
}
function renderCharts(){
 let clipped=chart($('chart-force'),[{key:'max_force_kn',label:'Max |F| (envelope)',color:'#0B2265',width:7,opacity:.18,unit:'kN'},{key:'max_tension_kn',label:'Max tension',color:'#001B96',unit:'kN'},{key:'max_compression_kn',label:'Max compression',color:'#EF4444',unit:'kN'}],'Axial force (kN)','No data yet');
 clipped+=chart($('chart-displacement'),[{key:'max_displacement_mm',label:'Max deflection',color:'#5A85D7',unit:'mm'}],'Max deflection (mm)','No data yet');
 const note=$('charts-clip-note');if(note)note.textContent=series&&clipped?`${clipped} point(s) off scale, shown in orange on the top edge.`:'';
}
for(const id of ['chart-log','chart-clip'])$(id).addEventListener('change',renderCharts);
$('btn-charts').onclick=async()=>{
 if(!geometry||!plan.length)return;const token=++seriesToken,rev=revision;$('btn-charts').disabled=true;
 $('charts-message').textContent=`Computing ${plan.length} stages…`;
 try{const value=await api('/api/progress',{geometry,config:config()});if(token!==seriesToken||rev!==revision)return;series=value;
  const solved=series.filter(s=>s.status==='stable').length,unstable=series.filter(s=>s.status==='unstable').length;
  $('charts-message').textContent=`${solved} of ${series.length} stages solved`+(unstable?` · ${unstable} with a mechanism (red triangles, no values)`:'')+'. Hover over a point to see its stage.';
  $('btn-charts-csv').disabled=false;renderCharts();
 }catch(e){if(token!==seriesToken)return;$('charts-message').textContent=e.message;}finally{if(token===seriesToken)$('btn-charts').disabled=false;}
};
$('btn-charts-csv').onclick=()=>{if(!series)return;const cols=['stage','progress_pct','active_count','status','max_tension_kn','max_compression_kn','max_force_kn','max_displacement_mm'];const csv=[cols.join(','),...series.map(s=>cols.map(c=>s[c]===null||s[c]===undefined?'':s[c]).join(','))].join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download='assembly-progress.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
renderCharts();

// Boot
(async()=>{
  try{
    const c=await api('/api/catalog');
    for(const item of c.profiles)$('sel-profile').append(new Option(item,item));
    $('sel-profile').selectedIndex=2;
    for(const item of c.materials)$('sel-material').append(new Option(item,item));
    geometry=await api('/api/demo');
    populateSupports(); await replan(true);
  }catch(e){
    badge('SERVER OFFLINE','error'); $('message').textContent=e.message+' · Run: PYTHONPATH=src python -m domestage.server';
  }
})();
})();
