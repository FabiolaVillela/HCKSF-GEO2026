/* Optional resistance view. Existing analysis data and physical configuration stay unchanged. */
window.AISCView=(()=>{
 const $=id=>document.getElementById(id),cache=new Map();
 let host,grades=[],family=null,baseKey='',activeKey='',report=null,error='',busy=false,allBusy=false,generation=0;
 const text=(en,es)=>host?.context().language==='es'?es:en;
 const fmt=(v,n=3)=>v===null||v===undefined?'—':host.format(v,n);
 function design(){const g=$('design-grade').value;return g==='custom'?{grade:g,Fy_MPa:$('design-fy').value,Fu_MPa:$('design-fu').value,source:$('design-source').value}:{grade:g};}
 function key(){const c=host.context();return JSON.stringify([c.geometry,c.config,design()]);}
 const gradeLabel=g=>text(g.label,g.label.replace(' Grade ',' Grado '));
 function selectedMaterial(){const d=design();return grades.find(g=>g.id===d.grade);}
 function fillGrades(){
   const material=host.context().config.material,old=$('design-grade').value;
   if(material===family&&$('design-grade').options.length>1){
     // Same material: only refresh the two translatable options when the language changes.
     const o=$('design-grade').options;o[0].textContent=text('Select grade…','Seleccionar grado…');
     const custom=[...o].find(x=>x.value==='custom');if(custom)custom.textContent=text('Custom (certificate)','Personalizado (certificado)');
     for(const x of o){const g=grades.find(g=>g.id===x.value);if(g)x.textContent=gradeLabel(g);}
     return;
   }
   family=material;$('design-grade').replaceChildren(new Option(text('Select grade…','Seleccionar grado…'),''));
   for(const g of grades.filter(g=>g.material===material))$('design-grade').append(new Option(gradeLabel(g),g.id));
   $('design-grade').append(new Option(text('Custom (certificate)','Personalizado (certificado)'),'custom'));
   if(grades.some(g=>g.id===old&&g.material===material))$('design-grade').value=old;
 }
 function properties(){
   $('design-custom').hidden=$('design-grade').value!=='custom';
   const box=$('design-properties');box.replaceChildren();const g=selectedMaterial();
   if(g){box.append(document.createTextNode(`Fy = ${fmt(g.Fy_MPa)} MPa · Fu = ${fmt(g.Fu_MPa)} MPa · `));const a=document.createElement('a');a.textContent=text('Source','Fuente');a.href=g.source;a.target='_blank';a.rel='noopener';box.append(a);}
   else box.textContent=$('design-grade').value==='custom'?text('Enter certified strengths in MPa.','Introduce resistencias certificadas en MPa.'):text('Select the actual product grade; no grade is assumed.','Selecciona el grado real del producto; no se asume un grado.');
   if(family==='Aluminio')box.append(document.createTextNode(text(' Aluminum catalog strengths describe extruded, unwelded material only. AISC does not apply.',' Las resistencias de aluminio corresponden a material extruido sin afectación por soldadura. AISC no aplica.')));
 }
 function enabled(){return $('show-aisc').checked;}
 // Absolute utilization scale: the deliberate break above 1 distinguishes exceedance.
 const utilizationStops=[[0,'#00ffff'],[.5,'#00aaff'],[.75,'#0000ff'],[1,'#000000']];
 const exceedanceStops=[[1,'#ffff00'],[1.1,'#ff9900'],[1.25,'#ff0000']];
 function utilizationColor(value){
   if(!Number.isFinite(value)||value<0)return '#737373';
   const stops=value<=1?utilizationStops:exceedanceStops;
   if(value>=stops[stops.length-1][0])return stops[stops.length-1][1];
   for(let i=1;i<stops.length;i++){
     if(value<=stops[i][0]){
       const [a,ca]=stops[i-1],[b,cb]=stops[i],t=(value-a)/(b-a);
       return '#'+[1,3,5].map(j=>Math.round(parseInt(ca.slice(j,j+2),16)*(1-t)+parseInt(cb.slice(j,j+2),16)*t).toString(16).padStart(2,'0')).join('');
     }
   }
   return stops[0][1];
 }
 function color(id){if(!enabled())return null;return utilizationColor(report?.members.find(m=>m.id===id)?.utilization);}
 function renderColorLegend(){
   const box=$('aisc-canvas-legend');box.replaceChildren();
   box.style.cssText='width:100%;max-width:480px;';
   const title=document.createElement('div');title.textContent=text('AISC utilization · preliminary','Utilización AISC · preliminar');box.append(title);
   const ramp=document.createElement('div');
   ramp.style.cssText='height:14px;border:1px solid #94a3b8;border-radius:3px;margin-top:6px;';
   ramp.style.background='linear-gradient(90deg,'+[...utilizationStops,...exceedanceStops].map(([u,c])=>c+' '+(u/1.25*100)+'%').join(',')+')';box.append(ramp);
   const ticks=document.createElement('div');ticks.style.cssText='position:relative;height:20px;font-variant-numeric:tabular-nums;';
   for(const [value,label] of [[0,'0'],[.75,'0.75'],[1,'1.0'],[1.25,'≥1.25']]){
     const tick=document.createElement('span');tick.textContent=label;
     tick.style.cssText='position:absolute;left:'+(value/1.25*100)+'%;transform:translateX('+(value===0?'0':value===1.25?'-100%':'-50%')+');';ticks.append(tick);
   }
   box.append(ticks);
   const note=document.createElement('div');note.style.fontSize='.72rem';note.textContent=text('1.0: black · >1.0: yellow → orange → red · Gray: no results','1.0: negro · >1.0: amarillo → naranja → rojo · Gris: sin resultados');box.append(note);
 }

 async function api(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const v=await r.json();if(!r.ok)throw Error(v.message||'Check failed');return v;}
 function payload(){const c=host.context();return{geometry:c.geometry,config:c.config,stage:c.stage,design:design()};}
 function update(){
   if(!host)return;
   fillGrades();properties();const c=host.context(),next=key();
   if(next!==baseKey){baseKey=next;cache.clear();report=null;error='';busy=false;allBusy=false;activeKey='';++generation;}
   const k=next+'/'+c.stage;
   report=c.current?.stable?cache.get(k)||null:null;
   const ready=!!c.geometry&&!!design().grade&&family==='Acero';
   $('aisc-all').disabled=!ready||allBusy;
   render();
   if(!enabled()||!ready||!c.current?.stable||report||activeKey===k)return;
   activeKey=k;busy=true;const token=generation;
   api('/api/aisc',payload()).then(value=>{
     if(token!==generation)return;cache.set(k,value);
     if(k===key()+'/'+host.context().stage){report=value;busy=false;error='';render();host.redraw();}
   }).catch(e=>{if(token!==generation)return;if(k===key()+'/'+host.context().stage){busy=false;activeKey='';error=e.message;render();host.redraw();}});
 }
 async function precompute(stage){
   if(!host)return;
   const c=host.context();
   if(!design().grade||c.config.material!=='Acero')return;
   const k=key(),cacheKey=k+'/'+stage;
   if(cache.has(cacheKey))return;
   const value=await api('/api/aisc',{...payload(),stage});
   if(k!==key())return;
   cache.set(cacheKey,value);
 }
 function makeTable(headers,rows){const t=document.createElement('table'),head=t.insertRow();for(const name of headers){const th=document.createElement('th');th.scope='col';th.textContent=name;head.append(th);}for(const values of rows){const row=t.insertRow();for(const v of values)row.insertCell().textContent=v;}return t;}
 function stateLabel(value){const es={tension:'tensión',compression:'compresión',flexotension:'flexotensión',flexocompression:'flexocompresión','biaxial flexure (conservative sum)':'flexión biaxial (suma conservadora)'};return text(value,es[value]||value);}
 function summary(r){
   if(r.max_utilization===null)return r.message;
   return `${text('Stage','Etapa')} ${r.stage} · Umax = ${fmt(r.max_utilization)} · ${text('member','barra')} #${r.governing.member_id} · ${r.governing.equation} · x=${fmt(r.governing.x_m)} m${r.status==='incomplete'?text(' · INCOMPLETE',' · INCOMPLETO'):''}`;
 }
 function render(){
   if(!host)return;
   const c=host.context(),box=$('aisc-results'),note=$('aisc-summary');box.replaceChildren();
   $('aisc-basis').textContent=text('ANSI/AISC 360-22 LRFD · 1.4D · t=0.93t nominal · K=1 · L=node-to-node · An=Ag · U=1 · first-order only. Shear, torsion, connections and Chapter C stability are not checked. Utilization ≤1: within included checks; >1: exceeds; gray: unavailable. This is not a complete design approval.','ANSI/AISC 360-22 LRFD · 1.4D · t=0.93t nominal · K=1 · L=entre nodos · An=Ag · U=1 · Solo primer orden. No se revisan cortante, torsión, conexiones ni estabilidad del capítulo C. Utilización ≤1: dentro de revisiones incluidas; >1: excede; gris: no disponible. No constituye una aprobación integral de diseño.');
   document.querySelector('.force-legend').hidden=enabled();
   $('aisc-canvas-legend').hidden=!enabled();
   if(enabled())renderColorLegend();
   $('aisc-panel').hidden=!enabled();$('aisc-download').disabled=!report;
   note.textContent=!enabled()?text('AISC view off.','Vista AISC apagada.'):family!=='Acero'?text('AISC 360 is not applicable to aluminum.','AISC 360 no aplica al aluminio.'):!design().grade?text('Select a grade to check resistance.','Selecciona un grado para revisar resistencia.'):!c.current?.stable?text('Unavailable without stage equilibrium.','No disponible sin equilibrio de la etapa.'):error?error:report?summary(report):text('Checking selected stage…','Verificando etapa seleccionada…');
   if(!enabled()||!report)return;
   box.append(makeTable([text('Member','Barra'),text('Utilization','Utilización'),text('Included checks','Revisiones incluidas'),'AISC',text('State','Estado'),'x (m)'],report.members.map(m=>[m.id,fmt(m.utilization),m.utilization===null?text('Unavailable','No disponible'):m.utilization<=1?'≤1.00':'>1.00',m.equation||'—',stateLabel(m.limit_state)||m.message,fmt(m.x_m)])));
 }
 function appendMember(box,id){
   if(!enabled()||!report)return;const m=report.members.find(m=>m.id===id);if(!m)return;
   box.append(makeTable(['AISC 360-22 · LRFD',text('Preliminary','Preliminar')],[
     [text('Utilization / equation','Utilización / ecuación'),fmt(m.utilization)+' · '+(m.equation||m.message)],
     [text('Limit state / position','Estado límite / posición'),(stateLabel(m.limit_state)||'—')+' · '+fmt(m.x_m)+' m'],
     ['φPn,t / φPn,c (kN)',m.capacities?fmt(m.capacities.phiPn_tension_N/1000)+' / '+fmt(m.capacities.phiPn_compression_N/1000):'—'],
     ['φMn (kN·m)',m.capacities?fmt(m.capacities.phiMn_Nm/1000):'—'],
     ['1.4N / 1.4My / 1.4Mz (kN; kN·m)',m.factored_actions?[m.factored_actions[0],m.factored_actions[4],m.factored_actions[5]].map(x=>fmt(x/1000)).join(' / '):'—'],
     ['t design (mm) / KL/r',m.capacities?fmt(m.capacities.t_design_m*1000)+' / '+fmt(m.capacities.KL_over_r):'—'],
     [text('Section class (compression / flexure)','Clasificación (compresión / flexión)'),m.capacities?m.capacities.compression_class+' / '+m.capacities.flexure_class:'—'],
     [text('Scope','Alcance'),text('First-order, N/My/Mz only. No full design approval.','Primer orden, solo N/My/Mz. No es aprobación integral de diseño.')],
     ...(m.warning?[[text('Warning','Advertencia'),m.warning]]:[])
   ]));
 }
 function appendHistory(box,plan){
   if(!enabled())return;
   box.append(makeTable([text('Stage','Etapa'),'AISC Umax',text('Governing equation','Ecuación gobernante')],plan.map(s=>{const r=cache.get(baseKey+'/'+s.stage);return[s.stage,r?fmt(r.max_utilization):'—',r?.governing?.equation||text('Not checked / unavailable','No revisada / no disponible')];})));
 }
 function init(h){
   host=h;
   for(const id of ['show-aisc','design-grade','design-fy','design-fu','design-source'])$(id).addEventListener('input',()=>{update();host.redraw();});
   $('aisc-all').onclick=async()=>{
     update();if($('aisc-all').disabled)return;const token=generation,k=key();allBusy=true;$('aisc-all').disabled=true;$('aisc-summary').textContent=text('Checking all stages…','Verificando todas las etapas…');
     try{const values=await api('/api/aisc/progress',payload());if(token!==generation)return;for(const r of values)cache.set(k+'/'+r.stage,r);report=cache.get(k+'/'+host.context().stage)||null;error='';}
     catch(e){if(token===generation)error=e.message;}
     finally{if(token===generation){allBusy=false;update();host.redraw();}}
   };
   $('aisc-download').onclick=()=>{if(!report)return;const data={selected_stage:report,checked_stages:[...cache.values()],original_stage:host.context().current};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='aisc-stage-'+report.stage+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
   fetch('/api/design-materials').then(r=>{if(!r.ok)throw Error('Material catalog unavailable');return r.json();}).then(g=>{grades=g;family=null;update();host.redraw();}).catch(e=>{$('design-properties').textContent=e.message;});
 }
 return Object.freeze({init,update,precompute,enabled,color,appendMember,appendHistory});
})();
