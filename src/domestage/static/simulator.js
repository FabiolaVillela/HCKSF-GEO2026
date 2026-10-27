'use strict';
(()=>{
const $=id=>document.getElementById(id),canvas=$('viewport'),ctx=canvas.getContext('2d');
let geometry=null,plan=[],currentStage=0,current=null,revision=0,requestId=0,playing=false,selected='',segments=[],projected=new Map();
const calculated=new Map();let q=normalize([.87,-.35,.12,.32]),zoom=1;const pointers=new Map();let dragged=false,pinch=null,sliderTimer;

let language='es';
try{language=localStorage.getItem('domestage-language')==='en'?'en':'es';}catch{}
const english={
 "🏗️ GEOMETRICA · Montaje de Domos": "🏗️ GEOMETRICA · Dome Assembly",
 "Motor estructural · peso propio y carga de instalador · equilibrio por etapa": "Structural solver · self-weight and installer load · equilibrium by stage",
 "Perfil HSS": "HSS section",
 "Material": "Material",
 "Conexiones": "Connections",
 "Articuladas · axial": "Pinned · axial",
 "Empotradas · pórtico": "Rigid · frame",
 "Apoyos": "Supports",
 "Articulados": "Pinned",
 "Empotrados": "Fixed",
 "Barras por etapa": "Bars per stage",
 "Instalador + herramientas (kg)": "Installer + tools (kg)",
 "Unidades DXF": "DXF units",
 "Del archivo": "From file",
 "pulgadas": "inches",
 "pies": "feet",
 "Tolerancia (mm)": "Tolerance (mm)",
 "Importar DXF": "Import DXF",
 "Conectando con el motor…": "Connecting to the solver…",
 "Revisar apoyos y secuencia": "Review supports and sequence",
 "Se proponen los nodos de cota mínima. Los cruces interiores no crean uniones. El orden de montaje se basa en la secuencia del modelo o en altura media para DXF.": "Nodes at the lowest elevation are suggested. Interior crossings do not create joints. Assembly order follows the model sequence or average height for DXF.",
 "Nodos de apoyo": "Support nodes",
 "Aplicar apoyos": "Apply supports",
 "Progreso:": "Progress:",
 "Barras:": "Bars:",
 "▶ Recorrer etapas": "▶ Play stages",
 "Etapa anterior": "Previous stage",
 "Etapa de montaje": "Assembly stage",
 "Etapa siguiente": "Next stage",
 "Etapa": "Stage",
 "Barras nuevas": "New bars",
 "Tracción máxima": "Maximum tension",
 "Compresión máxima": "Maximum compression",
 "Peso propio instalado": "Installed self-weight",
 "Carga del instalador": "Installer load",
 "Desplazamiento máximo": "Maximum displacement",
 "Estructura de la etapa. Arrastrar para girar, rueda para zoom y clic para seleccionar barra o apoyo.": "Stage structure. Drag to rotate, scroll to zoom, and click to select a bar or support.",
 "Arrastra para girar · rueda para zoom · clic para consultar": "Drag to rotate · scroll to zoom · click for details",
 "Seleccionar": "Select",
 "Seleccionar barra o apoyo": "Select bar or support",
 "Sin selección": "No selection",
 "Descargar etapa JSON": "Download stage JSON",
 "Selecciona una barra instalada o un apoyo.": "Select an installed bar or a support.",
 "Historial de etapas calculadas": "Calculated stage history",
 "Análisis elástico lineal independiente por etapa. Un solo instalador en el nodo j de la última barra nueva; etapa 0 sin instalador. No incluye deformaciones acumuladas de montaje, pandeo ni comprobación de resistencia.": "Independent linear elastic analysis per stage. One installer at node j of the last new bar; no installer at stage 0. Does not include accumulated assembly deformations, buckling, or strength checks.",
 "Idioma": "Language",
 "Compresión": "Compression",
 "Tracción": "Tension",
 "Cero": "Zero",
 "Axial al centro · kN · escala por etapa": "Midpoint axial force · kN · scale per stage",
 "Contorno magenta: nueva · gris: sin solución · punteado: pendiente · círculo naranja: apoyo": "Magenta outline: new · gray: unsolved · dashed: pending · orange dot: support",
 "Sin fuerzas calculadas": "No calculated forces",
 "PENDIENTE": "PENDING",
 "CALCULANDO": "CALCULATING",
 "EQUILIBRIO CALCULADO": "EQUILIBRIUM CALCULATED",
 "MECANISMO DETECTADO": "MECHANISM DETECTED",
 "SIN BARRAS": "NO BARS",
 "ERROR": "ERROR",
 "DXF NO VÁLIDO": "INVALID DXF",
 "MOTOR NO DISPONIBLE": "SOLVER UNAVAILABLE",
 "Pendiente de cálculo.": "Awaiting calculation.",
 "Carga una geometría válida.": "Load valid geometry.",
 "Preparando secuencia de montaje…": "Preparing assembly sequence…",
 "Sin barras nuevas": "No new bars",
 "Calculando equilibrio de la etapa {stage}…": "Calculating equilibrium for stage {stage}…",
 "Nodo": "Node",
 "nodo": "node",
 "Barra": "Bar",
 "Apoyo": "Support",
 "Apoyo · nodo ": "Support · node ",
 "Barra ": "Bar ",
 " · pendiente de instalar; sin peso ni rigidez en esta etapa.": " · not yet installed; no weight or stiffness in this stage.",
 " · sin resultados de fuerzas: ": " · no force results: ",
 "cálculo pendiente.": "calculation pending.",
 "Nodos": "Nodes",
 "Longitud": "Length",
 "Axial i / centro / j": "Axial i / midpoint / j",
 "Momentos My / Mz al centro": "Midpoint My / Mz moments",
 " · sin barras activas conectadas.": " · no connected active bars.",
 "Barras": "Bars",
 "Estado": "Status",
 "Tracción (kN)": "Tension (kN)",
 "Compresión (kN)": "Compression (kN)",
 "Equilibrio": "Equilibrium",
 "Mecanismo": "Mechanism",
 "Sin barras": "No bars",
 "Error": "Error",
 "Pendiente": "Pending",
 "⏸ Pausar": "⏸ Pause",
 "Revisando conectividad del DXF…": "Checking DXF connectivity…",
 "No se encontró el motor. Inicia PYTHONPATH=src python -m domestage.server y abre su dirección local.": "Solver not found. Run PYTHONPATH=src python -m domestage.server and open its local address.",
 "El motor rechazó la solicitud.": "The solver rejected the request.",
 " · Inicia PYTHONPATH=src python -m domestage.server": " · Run PYTHONPATH=src python -m domestage.server",
 "No hay barras instaladas en esta etapa.": "No bars are installed in this stage.",
 "Equilibrio elástico lineal calculado.": "Linear elastic equilibrium calculated.",
 "Modelo articulado inestable: traslaciones sin rigidez.": "Unstable pinned model: translations without stiffness.",
 "Modelo articulado inestable: mecanismo o matriz mal condicionada.": "Unstable pinned model: mechanism or ill-conditioned matrix.",
 "Modelo inestable: GDL sin rigidez": "Unstable model: degrees of freedom without stiffness",
 "Modelo inestable o excesivamente mal condicionado": "Unstable or severely ill-conditioned model",
 "Se requiere al menos un nodo de apoyo.": "At least one support node is required.",
 "Masa de instalador fuera de rango (0–10000 kg).": "Installer mass is out of range (0–10000 kg).",
 "Acero": "Steel",
 "Aluminio": "Aluminum",
 "Acero A36": "A36 steel",
 "Acero A500 Gr C": "A500 Grade C steel",
 "Aluminio 6061-T6": "6061-T6 aluminum"
};
function translate(key,values={}){let text=language==='en'?(english[key]||key):key;for(const [name,value] of Object.entries(values))text=text.replaceAll('{'+name+'}',value);return text;}
let messageSource='Conectando con el motor…',messageValues={},badgeSource='PENDIENTE',badgeStatus='pending';
function message(text,values={}){messageSource=text;messageValues=values;$('message').textContent=translate(messageSource,values);}
function translateStatic(){
 document.documentElement.lang=language;document.title=language==='en'?'Dome Assembly Simulator · GEOMETRICA':'Simulador de Montaje de Domo · GEOMETRICA';
 document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=translate(el.dataset.i18n));
 document.querySelectorAll('[data-i18n-aria]').forEach(el=>el.setAttribute('aria-label',translate(el.dataset.i18nAria)));
 $('language-select').value=language;
}
// Axial forces are in N; negative is compression. Normalize each side to
// 80% of its own stage extremum; larger magnitudes saturate at red or blue.
function forceLimits(result){
 const forces=result?.stable?Object.values(result.forces).filter(Number.isFinite):[];
 return {compression:0.8*Math.max(0,...forces.map(f=>-f)),tension:0.8*Math.max(0,...forces)};
}
function forceColor(force,limits){
 if(!Number.isFinite(force))return '#737373';
 const yellow=[250,204,21],red=[239,68,68],green=[34,197,94],blue=[0,27,150];
 let ratio=force<0?(limits.compression?-force/limits.compression:0):(limits.tension?force/limits.tension:0);
 ratio=Math.max(0,Math.min(1,ratio));
 let from=yellow,to=red;
 if(force>=0){from=ratio<=.5?yellow:green;to=ratio<=.5?green:blue;ratio=ratio<=.5?ratio*2:(ratio-.5)*2;}
 return '#'+from.map((v,i)=>Math.round(v+(to[i]-v)*ratio).toString(16).padStart(2,'0')).join('');
}
function updateLegend(limits){
 $('force-scale').hidden=!current?.stable;$('force-unavailable').hidden=!!current?.stable;
 $('force-min').textContent=(limits.compression?'≤ −':'')+fmt(limits.compression/1000);
 $('force-max').textContent=(limits.tension?'≥ +':'')+fmt(limits.tension/1000);
 // A side with no forces stays yellow rather than implying nonexistent loads.
 document.querySelector('.force-gradient').style.background=`linear-gradient(90deg,${forceColor(-limits.compression,limits)} 0%,#facc15 50%,${forceColor(limits.tension/2,limits)} 75%,${forceColor(limits.tension,limits)} 100%)`;
}

const fmt=(x,n=3)=>Number(x).toLocaleString(language==='en'?'en-US':'es-MX',{maximumFractionDigits:n});
function normalize(a){const n=Math.hypot(...a);return a.map(v=>v/n);}
function mul(a,b){return [a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]];}
function rotate(p){return mul(mul(q,[0,...p]),[q[0],-q[1],-q[2],-q[3]]).slice(1);}
async function api(path,data,options={}){
 const response=await fetch(path,{...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{}),...options});
 let value;try{value=await response.json();}catch{throw Error('No se encontró el motor. Inicia PYTHONPATH=src python -m domestage.server y abre su dirección local.');}
 if(!response.ok)throw Error(value.message||'El motor rechazó la solicitud.');return value;
}
function config(){return {material:$('sel-material').value,profile:$('sel-profile').value,connection:$('sel-connection').value,support:$('sel-support').value,bars_per_step:+$('sel-step').value,worker_kg:+$('worker-kg').value};}
function stop(){clearTimeout(sliderTimer);playing=false;$('btn-play').textContent=translate('▶ Recorrer etapas');}
function clearAnalysis(){++requestId;current=null;$('download-stage').disabled=true;$('max-tension').textContent='—';$('max-compression').textContent='—';$('max-displacement').textContent='—';$('installed-weight').textContent='—';$('worker-load').textContent='—';badge('PENDIENTE','pending');selectionDetail();draw();}
function badge(label,status){badgeSource=label;badgeStatus=status;label=translate(badgeSource);$('status-badge').textContent=label;$('status-badge').className='badge badge-'+(status==='stable'?'stable':status==='unstable'||status==='error'?'unstable':'pending');}
function populateSupports(preserve=false){
 const oldSelection=selected,chosen=preserve?new Set(Array.from($('support-nodes').selectedOptions,o=>+o.value)):null;
 $('support-nodes').replaceChildren();const supports=new Set(geometry.support_nodes);
 for(const n of geometry.nodes){const o=document.createElement('option');o.value=n.id;o.textContent=`${translate("Nodo")} ${n.id} · Z ${fmt(n.z)} m`;o.selected=(chosen||supports).has(n.id);$('support-nodes').append(o);}
 $('element-select').replaceChildren(new Option(translate('Sin selección'),''));
 for(const b of geometry.bars)$('element-select').append(new Option(translate('Barra ')+b.id,'b'+b.id));
 for(const n of geometry.support_nodes)$('element-select').append(new Option(translate('Apoyo')+' '+n,'s'+n));
 selected=preserve?oldSelection:'';$('element-select').value=selected;
}
async function replan(reset=false){
 const rev=++revision;stop();calculated.clear();$('stage-history').textContent=translate('Pendiente de cálculo.');clearAnalysis();if(!geometry){message('Carga una geometría válida.');return;}
 message('Preparando secuencia de montaje…');
 try{const p=await api('/api/plan',{geometry,bars_per_step:config().bars_per_step});if(rev!==revision)return;plan=p;
 $('stage-slider').max=plan.length-1;$('last-stage').textContent=plan.length-1;
 await setStage(reset?0:Math.min(currentStage,plan.length-1));
 }catch(error){if(rev!==revision)return;badge('ERROR','error');message(error.message);}
}
function pendingStage(stage){
 currentStage=stage;clearAnalysis();const s=plan[stage];if(!s)return;
 $('stage-slider').value=stage;$('stage-num').textContent=stage;
 $('active-bars-count').textContent=s.active_count;$('total-bars-count').textContent=s.total_bars;
 $('progress-text').textContent=fmt(s.progress_pct,1)+'%';$('progress-fill').style.width=s.progress_pct+'%';
 $('newest-bar-text').textContent=s.new_bar_ids.length?s.new_bar_ids.map(i=>'#'+i).join(', '):translate('Sin barras nuevas');draw();
}
async function setStage(stage){
 if(!plan.length)return;stage=Math.max(0,Math.min(stage,plan.length-1));pendingStage(stage);
 const token=++requestId,rev=revision;message('Calculando equilibrio de la etapa {stage}…',{stage});badge('CALCULANDO','pending');
 try{const value=calculated.get(stage)||await api('/api/stage',{geometry,config:config(),stage});
 if(token!==requestId||rev!==revision)return null;calculated.set(stage,value);current=value;
 renderResult(value);return value;
 }catch(error){if(token!==requestId||rev!==revision)return null;current=null;badge('ERROR','error');message(error.message);selectionDetail();draw();return null;}
}
function renderResult(value){ badge(value.status==='stable'?'EQUILIBRIO CALCULADO':value.status==='unstable'?'MECANISMO DETECTADO':value.status==='empty'?'SIN BARRAS':'ERROR',value.status);
 message(value.message);
 $('installed-weight').textContent=fmt(value.mass_kg*9.80665/1000)+' kN ('+fmt(value.mass_kg,1)+' kg)';
 $('worker-load').textContent=fmt(value.worker_load_N/1000)+' kN'+(value.worker_node===null?'':` · ${translate("nodo")} ${value.worker_node}`);
 if(value.stable){$('max-tension').textContent=fmt(value.max_tension_kn)+' kN';$('max-compression').textContent='−'+fmt(value.max_compression_kn)+' kN';$('max-displacement').textContent=fmt(value.max_displacement_mm)+' mm';}
 $('download-stage').disabled=false;selectionDetail();history();draw();}
function table(rows){const t=document.createElement('table');for(const [a,b] of rows){const r=t.insertRow(),th=document.createElement('th');th.scope='row';th.textContent=a;r.append(th);r.insertCell().textContent=b;}return t;}
function selectionDetail(){
 const box=$('selection-detail');box.replaceChildren();if(!selected||!geometry){box.textContent=translate('Selecciona una barra instalada o un apoyo.');return;}
 const id=+selected.slice(1),isBar=selected[0]==='b',title=document.createElement('strong');title.textContent=(isBar?translate('Barra '):translate('Apoyo · nodo '))+id;box.append(title);
 const active=new Set(plan[currentStage]?.active_bar_ids||[]);
 if(isBar&&!active.has(id)){box.append(document.createTextNode(translate(' · pendiente de instalar; sin peso ni rigidez en esta etapa.')));return;}
 if(!current?.stable){box.append(document.createTextNode(translate(' · sin resultados de fuerzas: ')+(translate(current?.message)||translate('cálculo pendiente.'))));return;}
 if(isBar){const e=current.elements.find(e=>e.id===id);if(!e)return;const s=e.stations;box.append(table([[translate('Nodos'),e.i+' → '+e.j],[translate('Longitud'),fmt(e.length_m)+' m'],[translate('Axial i / centro / j'),[s[0],s[Math.floor(s.length/2)],s[s.length-1]].map(v=>fmt(v.N_Vy_Vz_T_My_Mz[0]/1000)).join(' / ')+' kN'],[translate('Momentos My / Mz al centro'),s[Math.floor(s.length/2)].N_Vy_Vz_T_My_Mz.slice(4).map(v=>fmt(v/1000)).join(' / ')+' kN·m']]));}
 else{const r=current.reactions.find(r=>r.node_id===id);if(!r){box.append(document.createTextNode(translate(' · sin barras activas conectadas.')));return;}box.append(table([['Rx / Ry / Rz',r.values.slice(0,3).map(v=>fmt(v/1000)).join(' / ')+' kN'],['Mx / My / Mz',r.values.slice(3).map(v=>fmt(v/1000)).join(' / ')+' kN·m']]));}
}
function history(){const div=$('stage-history');div.replaceChildren();const t=document.createElement('table'),head=t.insertRow();for(const label of [translate('Etapa'),translate('Barras'),translate('Estado'),translate('Tracción (kN)'),translate('Compresión (kN)')]){const th=document.createElement('th');th.textContent=label;head.append(th);}for(const s of plan){const r=calculated.get(s.stage),tr=t.insertRow();for(const value of [s.stage,s.active_count,r?({stable:translate('Equilibrio'),unstable:translate('Mecanismo'),empty:translate('Sin barras'),error:translate('Error')}[r.status]):translate('Pendiente'),r?.stable?fmt(r.max_tension_kn):'—',r?.stable?fmt(r.max_compression_kn):'—'])tr.insertCell().textContent=value;}div.append(t);}
function draw(){
 const limits=forceLimits(current);updateLegend(limits);
 const w=canvas.clientWidth,h=canvas.clientHeight,dpr=window.devicePixelRatio||1;canvas.width=w*dpr;canvas.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!geometry)return;
 const min=[0,1,2].map(i=>Math.min(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),max=[0,1,2].map(i=>Math.max(...geometry.nodes.map(n=>[n.x,n.y,n.z][i]))),center=min.map((v,i)=>(v+max[i])/2),diameter=Math.max(.01,Math.hypot(...max.map((v,i)=>v-min[i]))),scale=Math.min(w-35,h-65)/diameter*zoom;
 projected=new Map(geometry.nodes.map(n=>{const p=rotate([n.x-center[0],n.y-center[1],n.z-center[2]]);return [n.id,[w/2+p[0]*scale,h/2-p[1]*scale,p[2]]];}));
 const active=new Set(plan[currentStage]?.active_bar_ids||[]),fresh=new Set(plan[currentStage]?.new_bar_ids||[]);
 segments=geometry.bars.map(b=>({b,a:projected.get(b.i),z:projected.get(b.j)})).sort((a,b)=>(a.a[2]+a.z[2])-(b.a[2]+b.z[2]));
 for(const s of segments){
 const installed=active.has(s.b.id),f=current?.stable?current.forces[s.b.id]:null,isSelected=selected==='b'+s.b.id;
 ctx.beginPath();ctx.moveTo(s.a[0],s.a[1]);ctx.lineTo(s.z[0],s.z[1]);ctx.setLineDash(installed?[]:[3,4]);
 // Outlines retain new/selected state without hiding the force color.
 if(isSelected||(installed&&fresh.has(s.b.id))){ctx.strokeStyle=isSelected?'#000000':'#FF00FF';ctx.lineWidth=isSelected?7:6;ctx.stroke();}
 ctx.strokeStyle=!installed?'#CACACA':forceColor(f,limits);ctx.lineWidth=installed?3:1;ctx.stroke();
 }
 ctx.setLineDash([]);for(const id of geometry.support_nodes){const p=projected.get(id);ctx.beginPath();ctx.arc(p[0],p[1],selected==='s'+id?7:4,0,2*Math.PI);ctx.fillStyle='#F59E0B';ctx.fill();}
 if(current?.worker_node!==null&&current?.worker_node!==undefined){const p=projected.get(current.worker_node);ctx.fillStyle='#000000';ctx.font='12px sans-serif';ctx.fillText('↓ '+fmt(current.worker_load_N/1000)+' kN',p[0]+8,p[1]-8);}
}
$('language-select').addEventListener('change',()=>{
 language=$('language-select').value;try{localStorage.setItem('domestage-language',language);}catch{}
 translateStatic();if(geometry)populateSupports(true);
 for(const option of $('sel-material').options)option.textContent=translate(option.value);
 $('btn-play').textContent=translate(playing?'⏸ Pausar':'▶ Recorrer etapas');
 if(current)renderResult(current);else{message(messageSource,messageValues);badge(badgeSource,badgeStatus);selectionDetail();history();draw();}
 if(plan[currentStage])$('newest-bar-text').textContent=plan[currentStage].new_bar_ids.length?plan[currentStage].new_bar_ids.map(i=>'#'+i).join(', '):translate('Sin barras nuevas');
});
translateStatic();
$('element-select').addEventListener('change',()=>{selected=$('element-select').value;selectionDetail();draw();});
$('stage-slider').addEventListener('input',()=>{stop();clearTimeout(sliderTimer);const stage=+$('stage-slider').value;pendingStage(stage);sliderTimer=setTimeout(()=>setStage(stage),130);});
$('btn-prev').onclick=()=>{stop();setStage(currentStage-1);};$('btn-next').onclick=()=>{stop();setStage(currentStage+1);};
$('btn-play').onclick=async()=>{if(playing){stop();return;}playing=true;$('btn-play').textContent=translate('⏸ Pausar');if(currentStage===plan.length-1)await setStage(0);while(playing&&currentStage<plan.length-1){const r=await setStage(currentStage+1);if(!r||!r.stable){stop();break;}await new Promise(r=>setTimeout(r,250));}stop();};
for(const id of ['sel-profile','sel-material','sel-connection','sel-support','worker-kg'])$(id).addEventListener('change',()=>replan());$('sel-step').addEventListener('change',()=>replan(true));
$('apply-supports').onclick=()=>{if(!geometry)return;geometry.support_nodes=Array.from($('support-nodes').selectedOptions,o=>+o.value);populateSupports();replan();};
async function importDXF(){const file=$('dxf-file-input').files[0];if(!file)return;const rev=++revision;stop();calculated.clear();geometry=null;plan=[];clearAnalysis();message('Revisando conectividad del DXF…');try{const value=await api('/api/import?units='+encodeURIComponent($('dxf-units').value)+'&tolerance='+encodeURIComponent(+$('dxf-tolerance').value/1000),null,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:await file.arrayBuffer()});if(rev!==revision)return;geometry=value.geometry;$('import-report').textContent=JSON.stringify(value.report,null,2);populateSupports();await replan(true);}catch(e){if(rev!==revision)return;badge('DXF NO VÁLIDO','error');message(e.message);}}
for(const id of ['dxf-file-input','dxf-units','dxf-tolerance'])$(id).addEventListener('change',importDXF);
$('download-stage').onclick=()=>{if(!current)return;const blob=new Blob([JSON.stringify({geometry,config:config(),result:current},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='etapa-'+currentStage+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,sx:e.clientX,sy:e.clientY});if(pointers.size===1)dragged=false;if(pointers.size===2){dragged=true;const a=[...pointers.values()];pinch={d:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y),zoom};}});
canvas.addEventListener('pointermove',e=>{const p=pointers.get(e.pointerId);if(!p)return;const dx=e.clientX-p.x,dy=e.clientY-p.y;p.x=e.clientX;p.y=e.clientY;if(Math.hypot(p.x-p.sx,p.y-p.sy)>4)dragged=true;if(pointers.size===2&&pinch){const a=[...pointers.values()];zoom=Math.max(.25,Math.min(10,pinch.zoom*Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y)/Math.max(1,pinch.d)));}else{const n=Math.hypot(dx,dy);if(n){const t=n*.004;q=normalize(mul([Math.cos(t),dy/n*Math.sin(t),dx/n*Math.sin(t),0],q));}}draw();});
canvas.addEventListener('pointerup',e=>{const click=!dragged&&pointers.size===1;pointers.delete(e.pointerId);pinch=null;if(!click||!geometry)return;const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;let value='',best=12;for(const id of geometry.support_nodes){const p=projected.get(id),d=Math.hypot(p[0]-x,p[1]-y);if(d<best){best=d;value='s'+id;}}if(!value){best=10;for(const s of segments){const dx=s.z[0]-s.a[0],dy=s.z[1]-s.a[1],t=Math.max(0,Math.min(1,((x-s.a[0])*dx+(y-s.a[1])*dy)/(dx*dx+dy*dy||1))),d=Math.hypot(x-s.a[0]-t*dx,y-s.a[1]-t*dy);if(d<best){best=d;value='b'+s.b.id;}}}selected=value;$('element-select').value=value;selectionDetail();draw();});
canvas.addEventListener('pointercancel',e=>{pointers.delete(e.pointerId);pinch=null;});canvas.style.touchAction='none';canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.25,Math.min(10,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});new ResizeObserver(draw).observe(canvas);
(async()=>{try{const c=await api('/api/catalog');for(const item of c.profiles)$('sel-profile').append(new Option(item,item));$('sel-profile').selectedIndex=2;for(const item of c.materials)$('sel-material').append(new Option(translate(item),item));geometry=await api('/api/demo');populateSupports();await replan(true);}catch(e){badge('MOTOR NO DISPONIBLE','error');message(e.message+translate(' · Inicia PYTHONPATH=src python -m domestage.server'));}})();
})();
