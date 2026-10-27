/* Optional resistance view. Existing analysis data and physical configuration stay unchanged. */
window.AISCView=(()=>{
 const $=id=>document.getElementById(id),cache=new Map();
 let host,grades=[],family=null,baseKey='',activeKey='',report=null,error='',busy=false,allBusy=false,generation=0;
 const text=(en,es)=>host?.context().language==='es'?es:en;
 const fmt=(v,n=3)=>v===null||v===undefined?'—':host.format(v,n);
 function design(){const g=$('design-grade').value;return g==='custom'?{grade:g,Fy_MPa:$('design-fy').value,Fu_MPa:$('design-fu').value,source:$('design-source').value}:{grade:g};}
 function key(){const c=host.context();return JSON.stringify([c.geometry,c.config,design()]);}
 function selectedMaterial(){const d=design();return grades.find(g=>g.id===d.grade);}
 function fillGrades(){
   const material=host.context().config.material,old=$('design-grade').value;
   if(material===family&&$('design-grade').options.length>1)return;
   family=material;$('design-grade').replaceChildren(new Option(text('Select grade…','Seleccionar grado…'),''));
   for(const g of grades.filter(g=>g.material===material))$('design-grade').append(new Option(g.label,g.id));
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
 function color(id){if(!enabled())return null;const m=report?.members.find(m=>m.id===id);return m?.utilization===null||!m?'#737373':m.utilization<=1?'#15803D':'#DC2626';}
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
 function makeTable(headers,rows){const t=document.createElement('table'),head=t.insertRow();for(const name of headers){const th=document.createElement('th');th.scope='col';th.textContent=name;head.append(th);}for(const values of rows){const row=t.insertRow();for(const v of values)row.insertCell().textContent=v;}return t;}
 function stateLabel(value){const es={tension:'tensión',compression:'compresión',flexotension:'flexotensión',flexocompression:'flexocompresión','biaxial flexure (conservative sum)':'flexión biaxial (suma conservadora)'};return text(value,es[value]||value);}
 function summary(r){
   if(r.max_utilization===null)return r.message;
   return `${text('Stage','Etapa')} ${r.stage} · Umax = ${fmt(r.max_utilization)} · ${text('member','barra')} #${r.governing.member_id} · ${r.governing.equation} · x=${fmt(r.governing.x_m)} m${r.status==='incomplete'?text(' · INCOMPLETE',' · INCOMPLETO'):''}`;
 }
 function render(){
   if(!host)return;
   const c=host.context(),box=$('aisc-results'),note=$('aisc-summary');box.replaceChildren();
   $('aisc-basis').textContent=text('ANSI/AISC 360-22 LRFD · 1.4D · t=0.93t nominal · K=1 · L=node-to-node · An=Ag · U=1 · first-order only. Shear, torsion, connections and Chapter C stability are not checked. Green ≤1: within included checks; red >1: exceeds; gray: unavailable. This is not a complete design approval.','ANSI/AISC 360-22 LRFD · 1.4D · t=0.93t nominal · K=1 · L=entre nodos · An=Ag · U=1 · Solo primer orden. No se revisan cortante, torsión, conexiones ni estabilidad del capítulo C. Verde ≤1: dentro de revisiones incluidas; rojo >1: excede; gris: no disponible. No constituye una aprobación integral de diseño.');
   document.querySelector('.force-legend').hidden=enabled();
   $('aisc-canvas-legend').hidden=!enabled();
   $('aisc-canvas-legend').textContent=text('AISC preliminary · green ≤1 (included checks) · red >1 · gray unavailable','AISC preliminar · verde ≤1 (revisiones incluidas) · rojo >1 · gris no disponible');
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
 return Object.freeze({init,update,enabled,color,appendMember,appendHistory});
})();
