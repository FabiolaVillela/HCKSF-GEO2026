'use strict';
(()=>{
const $=id=>document.getElementById(id), canvas=$('viewport'), ctx=canvas.getContext('2d');
let geometry=null, plan=[], currentStage=0, current=null, revision=0, requestId=0, playing=false, selected='', segments=[], projected=new Map();
const calculated=new Map(); let q=normalize([.87,-.35,.12,.32]), zoom=1; const pointers=new Map(); let dragged=false, pinch=null, sliderTimer;
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
  badge('CALCULATING','pending'); selectionDetail(); draw();
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
  const rev=++revision; stop(); calculated.clear();
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
    $('download-stage').disabled=false; selectionDetail(); history(); draw(); return value;
  }catch(error){
    if(token!==requestId||rev!==revision)return null; current=null;
    badge('ERROR','error'); $('message').textContent=error.message; selectionDetail(); draw(); return null;
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
    box.append(table([
      ['Boundary Condition', cond==='empotrado'?'Fixed (6 DOFs)':'Pinned (3 DOFs)'],
      ['Reactions Rx / Ry / Rz', r.values.slice(0,3).map(v=>fmt(v/1000)).join(' / ')+' kN'],
      ['Moments Mx / My / Mz', r.values.slice(3).map(v=>fmt(v/1000)).join(' / ')+' kN·m']
    ]));
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

// 3D Canvas Rendering
function draw(){
  const w=canvas.clientWidth, h=canvas.clientHeight, dpr=window.devicePixelRatio||1;
  canvas.width=w*dpr; canvas.height=h*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle='#FFFFFF'; ctx.fillRect(0,0,w,h);
  if(!geometry)return;

  const min=[0,1,2].map(i=>Math.min(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),
        max=[0,1,2].map(i=>Math.max(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),
        center=min.map((v,i)=>(v+max[i])/2),
        diameter=Math.max(.01,Math.hypot(...max.map((v,i)=>v-min[i]))),
        scale=Math.min(w-35,h-65)/diameter*zoom;

  projected=new Map(geometry.nodes.map(n=>{
    const p=rotate([n.x-center[0],n.y-center[1],n.z-center[2]]);
    return [n.id,[w/2+p[0]*scale, h/2-p[1]*scale, p[2]]];
  }));

  const active=new Set(plan[currentStage]?.active_bar_ids||[]), fresh=new Set(plan[currentStage]?.new_bar_ids||[]);
  segments=geometry.bars.map(b=>({b, a:projected.get(b.i), z:projected.get(b.j)})).sort((a,b)=>(a.a[2]+a.z[2])-(b.a[2]+b.z[2]));

  // Ghost & Installed Bars
  for(const s of segments){
    const installed=active.has(s.b.id), f=current?.stable?current.forces[s.b.id]:null;
    ctx.beginPath(); ctx.moveTo(s.a[0],s.a[1]); ctx.lineTo(s.z[0],s.z[1]);
    ctx.setLineDash(installed?[]:[3,4]);
    ctx.strokeStyle=selected==='b'+s.b.id?'#000000':!installed?'#CACACA':fresh.has(s.b.id)?'#00C853':f===null||f===undefined?'#737373':f<0?'#EF4444':'#001B96';
    ctx.lineWidth=selected==='b'+s.b.id?4.5:installed?2.2:1.0;
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Base Support nodes
  for(const id of geometry.support_nodes){
    const p=projected.get(id);
    ctx.beginPath(); ctx.arc(p[0],p[1],selected==='s'+id?7.5:4.5,0,2*Math.PI);
    ctx.fillStyle='#F59E0B'; ctx.fill();
  }
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
  const rev=++revision; stop(); calculated.clear(); geometry=null; plan=[]; clearAnalysis();
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
    for(const s of segments){
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
