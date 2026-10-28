'use strict';
(()=>{
const $=id=>document.getElementById(id), canvas=$('viewport'), ctx=canvas.getContext('2d');
let geometry=null, plan=[], currentStage=0, current=null, revision=0, requestId=0, playing=false, selected='', segments=[], projected=new Map(), deformedSegments=[];
const calculated=new Map(); let series=null, seriesToken=0; let q=normalize([.87,-.35,.12,.32]), zoom=1; const pointers=new Map(); let dragged=false, pinch=null, sliderTimer;
let analysisToken=0, analyzing=false, playbackToken=0;
let supportOverrides = {}; // {node_id: 'articulado' | 'empotrado'}


let language='en';
try{language=localStorage.getItem('domestage-language')==='es'?'es':'en';}catch{}
const spanish={
  "Analyze all stages": "Analizar todas las etapas",
  "Show Dimensions": "Mostrar dimensiones",
  "Overall undeformed model: maximum horizontal span and total vertical height.": "Modelo completo sin deformar: extensión horizontal máxima y altura vertical total.",
  "Material grade:":"Grado de material:",
  "Source / certificate:":"Fuente / certificado:",
  "Show AISC utilization (preliminary)":"Mostrar utilización AISC (preliminar)",
  "Check all stages":"Verificar todas las etapas",
  "Export AISC report":"Exportar reporte AISC",
  "AISC stage and member results":"Resultados AISC por etapa y barra",
  "AISC basis":"ANSI/AISC 360-22 LRFD · 1.4D · t=0.93t nominal · K=1 · L=entre nodos · An=Ag · U=1 · Solo primer orden. No se revisan cortante, torsión, conexiones ni estabilidad del capítulo C. Utilización ≤1: dentro de las revisiones incluidas; >1: excede; gris: no disponible. No constituye una aprobación integral de diseño.",
  "Language": "Idioma",
  "🏗️ DomeStage+ · Steel Dome Construction Analysis": "🏗️ DomeStage+ · Análisis de construcción de domos de acero",
  "Stage-by-stage structural simulation · Self-weight + 25 kg dead load per installed node": "Simulación estructural por etapas · Peso propio + 25 kg de carga muerta por nodo instalado",
  "INITIALIZING": "INICIALIZANDO",
  "📁 1. CAD Geometry & DXF": "📁 1. Geometría CAD y DXF",
  "Upload DXF Wireframe:": "Importar estructura DXF:",
  "Current model:": "Modelo actual:",
  "↺ Use default model": "↺ Usar modelo por defecto",
  "(default)": "(por defecto)",
  "Loading default model…": "Cargando modelo por defecto…",
  "Drawing Units:": "Unidades del dibujo:",
  "Auto-detect": "Detectar automáticamente",
  "Millimeters (mm)": "Milímetros (mm)",
  "Meters (m)": "Metros (m)",
  "Inches (in)": "Pulgadas (in)",
  "Feet (ft)": "Pies (ft)",
  "Merge Tolerance (mm):": "Tolerancia de unión (mm):",
  "⚙️ 2. Structural Properties": "⚙️ 2. Propiedades estructurales",
  "Steel Material:": "Material:",
  "HSS Pipe Section:": "Perfil tubular HSS:",
  "Bars Per Stage Step:": "Barras por etapa:",
  "1 bar per stage": "1 barra por etapa",
  "2 bars per stage": "2 barras por etapa",
  "3 bars per stage": "3 barras por etapa",
  "4 bars per stage": "4 barras por etapa",
  "🔗 3. Connections & Supports": "🔗 3. Conexiones y apoyos",
  "Bar Connections:": "Conexiones de barras:",
  "Pinned · Axial Truss (3 DOF)": "Articuladas · Armadura axial (3 GDL)",
  "Rigid · Frame with Moments (6 DOF)": "Rígidas · Pórtico con momentos (6 GDL)",
  "Base Supports Default:": "Apoyos de base por defecto:",
  "Pinned (Restrain Ux, Uy, Uz)": "Articulados (restringir Ux, Uy, Uz)",
  "Fixed (Restrain All 6 DOFs)": "Empotrados (restringir los 6 GDL)",
  "Node Connection Schedule:": "Tabla de conexiones de nodos:",
  "⬇ Export CSV": "⬇ Exportar CSV",
  "⬆ Import CSV": "⬆ Importar CSV",
  "Export CSV table with support types per node": "Exportar tabla CSV con tipos de apoyo por nodo",
  "Import edited CSV": "Importar CSV editado",
  "Current Installation Step · Elements Added": "Etapa de montaje actual · Elementos añadidos",
  "Active members contributing new stiffness and weight in this stage": "Barras activas que aportan nueva rigidez y peso en esta etapa",
  "Stage 0 · Base Installed": "Etapa 0 · Base instalada",
  "Dome Assembly Progress:": "Progreso del montaje:",
  "Active Bars:": "Barras activas:",
  "▶ Play Assembly": "▶ Reproducir montaje",
  "Previous stage": "Etapa anterior",
  "Next stage": "Etapa siguiente",
  "Stage": "Etapa",
  "Assembly stage": "Etapa de montaje",
  "Connecting to calculation engine…": "Conectando con el motor de cálculo…",
  "Max Tension (+T)": "Tracción máxima (+T)",
  "Max Compression (−C)": "Compresión máxima (−C)",
  "Installed Structure Weight": "Peso de la estructura instalada",
  "Max Deflection": "Desplazamiento máximo",
  "Show Amplified Nodal Deflection": "Mostrar desplazamiento nodal amplificado",
  "Scale factor ×": "Factor de escala ×",
  "Show Support Reaction Vectors": "Mostrar vectores de reacción de apoyos",
  "Reactions:": "Reacciones:",
  "Resultant Total": "Resultante total",
  "XYZ Components": "Componentes XYZ",
  "Radial / Tangential / Vertical": "Radial / Tangencial / Vertical",
  "Deflection view off (values are true scale).": "Vista deformada desactivada (valores a escala real).",
  "3D structure viewport. Drag to orbit, wheel to zoom, click to inspect.": "Vista de estructura 3D. Arrastrar para girar, rueda para zoom, clic para consultar.",
  "Magenta outline: new": "Contorno magenta: nueva",
  "Compression (−)": "Compresión (−)",
  "Tension (+)": "Tracción (+)",
  "Base supports": "Apoyos de base",
  "Deflection view": "Vista deformada",
  "🖱️ Drag to rotate · Wheel to zoom · Click member or support to inspect": "🖱️ Arrastra para girar · Rueda para zoom · Clic en barra o apoyo para consultar",
  "Support Reactions Table · Forces (kN) & Moments (kN·m)": "Tabla de reacciones · Fuerzas (kN) y momentos (kN·m)",
  "Member & Node Detail Inspector": "Inspector de barras y nodos",
  "Click member or select here…": "Haz clic en una barra o selecciona aquí…",
  "Export Stage JSON": "Exportar etapa JSON",
  "Utilization figures for the calculation report": "Figuras de utilización para la memoria de cálculo",
  "Progress (%):": "Avance (%):",
  "Progress milestones (%)": "Avances (%)",
  "🖼️ Export utilization figures (HTML)": "🖼️ Exportar figuras de utilización (HTML)",
  "Plan and elevation coloured by AISC utilization at each progress (needs a steel material grade)": "Planta y elevación coloreadas por utilización AISC en cada avance (requiere un grado de material de acero)",
  "Building utilization figures…": "Generando figuras de utilización…",
  "Utilization figures exported.": "Figuras de utilización exportadas.",
  "The engine could not build the figures.": "El motor no pudo generar las figuras.",
  "📄 Export results report (Excel)": "📄 Exportar reporte de resultados (Excel)",
  "Per-bar tension, compression and AISC 360-22 utilization (needs a material grade) and per-node deflection and support type, over all stages": "Tracción, compresión y utilización AISC 360-22 por barra (requiere un grado de material) y desplazamiento y tipo de apoyo por nodo, en todas las etapas",
  "Building report ({n} stages)…": "Generando reporte ({n} etapas)…",
  "The engine could not build the report.": "El motor no pudo generar el reporte.",
  "Results report exported with preliminary AISC member checks.": "Reporte de resultados exportado con revisiones AISC preliminares.",
  "Results report exported. Member checks: not checked (select a material grade).": "Reporte de resultados exportado. Revisiones de elementos: sin revisar (selecciona un grado de material).",
  "Results report exported. Member checks: not applicable to aluminum.": "Reporte de resultados exportado. Revisiones de elementos: no aplican al aluminio.",
  "Click any installed bar in the 3D model to inspect its Axial forces and My/Mz Bending Moments.": "Haz clic en una barra instalada para consultar sus fuerzas axiales y momentos flectores My/Mz.",
  "Detailed Stage Calculation History Table": "Historial detallado de cálculo por etapas",
  "Midpoint axial force · kN · 80% saturation per stage": "Fuerza axial al centro · kN · saturación al 80% por etapa",
  "Compression": "Compresión",
  "Zero": "Cero",
  "Tension": "Tracción",
  "No calculated forces": "Sin fuerzas calculadas",
  "Gray: unsolved": "Gris: sin solución",
  "Calculation server not found. Ensure server is running.": "No se encontró el servidor de cálculo. Comprueba que esté ejecutándose.",
  "Calculation engine error.": "Error del motor de cálculo.",
  "Precalculating all stages for instant 60 FPS motion…": "Precalculando todas las etapas para movimiento fluido a 60 FPS…",
  "All {total} stages precalculated in memory · Fluid 60 FPS motion active": "Todas las {total} etapas calculadas en memoria · Movimiento 60 FPS fluido activo",
  "Precalculating stage {current} of {total}…": "Calculando etapa {current} de {total}…",
  "READY / 60 FPS": "LISTO / 60 FPS",
  "STAGE PRELOAD FAILED": "FALLÓ PRECARGA",
  "CALCULATING": "CALCULANDO",
  "Bar #": "Barra #",
  "Support node ": "Nodo de apoyo ",
  "Pending calculation.": "Pendiente de cálculo.",
  "Load a valid geometry model.": "Carga un modelo geométrico válido.",
  "Planning stage assembly sequence…": "Preparando secuencia de montaje…",
  "ERROR": "ERROR",
  "Base Ring Installed": "Anillo base instalado",
  "Solving equilibrium for Stage {stage}…": "Calculando equilibrio de la etapa {stage}…",
  "SOLVING…": "CALCULANDO…",
  "STABLE EQUILIBRIUM": "EQUILIBRIO ESTABLE",
  "MECHANISM / UNSTABLE": "MECANISMO / INESTABLE",
  "NO BARS": "SIN BARRAS",
  "Click any installed member or support node in the 3D model to inspect its forces.": "Haz clic en una barra instalada o nodo de apoyo del modelo 3D para consultar sus fuerzas.",
  "Member #": "Barra #",
  "Support Node #": "Nodo de apoyo #",
  " · Pending installation (inactive in this stage).": " · Pendiente de instalar (inactiva en esta etapa).",
  " · No force solution available: ": " · Sin solución de fuerzas: ",
  "Pending.": "Pendiente.",
  "End Nodes": "Nodos extremos",
  "Bar Length": "Longitud de barra",
  "Axial Force (i / mid / j)": "Fuerza axial (i / centro / j)",
  "Bending Moment My / Mz (mid)": "Momento flector My / Mz (centro)",
  " · No active connected members yet.": " · Aún no hay barras activas conectadas.",
  "Boundary Condition": "Condición de apoyo",
  "Fixed (6 DOFs)": "Empotrado (6 GDL)",
  "Pinned (3 DOFs)": "Articulado (3 GDL)",
  "Reactions Rx / Ry / Rz": "Reacciones Rx / Ry / Rz",
  "Moments Mx / My / Mz": "Momentos Mx / My / Mz",
  "Radial / Tangential / Z": "Radial / Tangencial / Z",
  "Active Bars": "Barras activas",
  "Status": "Estado",
  "Max Tension (kN)": "Tracción máxima (kN)",
  "Max Compression (kN)": "Compresión máxima (kN)",
  "Equilibrium": "Equilibrio",
  "Mechanism": "Mecanismo",
  "No bars": "Sin barras",
  "Error": "Error",
  "Pending": "Pendiente",
  "Green": "Verde",
  "Red": "Rojo",
  "Blue": "Azul",
  "Reactions unavailable without stable solution.": "Reacciones no disponibles sin solución estable.",
  "Reaction vectors in global axes. Select a support to view values.": "Vectores de reacción en ejes globales. Selecciona un apoyo para ver los valores.",
  "Support reaction vectors hidden.": "Vectores de reacción ocultos.",
  "Support center in XY: ({x}, {y}) m · Rr: radial outwards, Rt: tangential CCW.": "Centro de apoyos en XY: ({x}, {y}) m · Rr: radial hacia fuera, Rt: tangencial antihoraria.",
  "Node": "Nodo",
  "Deflection view unavailable without stage equilibrium and displacements.": "Vista deformada no disponible sin equilibrio y desplazamientos de la etapa.",
  "Enter a visual scale factor between 0 and 100000.": "Introduce un factor visual entre 0 y 100000.",
  "Deflection view off · Max true displacement: ": "Vista deformada desactivada · Desplazamiento real máximo: ",
  "Amplified ×": "Amplificado ×",
  " · Real max ": " · Máximo real ",
  " mm → Visual ": " mm → Visual ",
  " · Node ": " · Nodo ",
  "⏸ Pause": "⏸ Pausar",
  "✓ Loaded connection overrides for {count} support nodes from CSV.": "✓ Se cargaron condiciones de conexión para {count} nodos de apoyo desde CSV.",
  "Error parsing CSV: ": "Error al leer CSV: ",
  "Reading DXF wireframe connectivity…": "Leyendo conectividad del DXF…",
  "INVALID DXF": "DXF NO VÁLIDO",
  "SERVER OFFLINE": "SERVIDOR DESCONECTADO",
  " · Run: PYTHONPATH=src python -m domestage.server": " · Ejecuta: PYTHONPATH=src python -m domestage.server",
  "Acero": "Acero",
  "Aluminio": "Aluminio",
  "Progress charts": "Gráficas de progreso",
  "📈 Compute all stages": "📈 Calcular todas las etapas",
  "Download data (CSV)": "Descargar datos (CSV)",
  "Log scale": "Escala logarítmica",
  "Clip outliers": "Recortar atípicos",
  "Maximum axial force vs % progress": "Fuerza axial máxima vs % de avance",
  "Maximum deflection vs % progress": "Desplazamiento máximo vs % de avance",
  "Compute all stages to see how the maximum axial force and maximum deflection change as assembly progresses.": "Calcula todas las etapas para observar la evolución de la fuerza axial máxima y el desplazamiento máximo.",
  "Axial force (kN)": "Fuerza axial (kN)",
  "Max deflection (mm)": "Desplazamiento máximo (mm)",
  "Max deflection": "Desplazamiento máx",
  "Maximum utilization vs % progress": "Utilización máxima vs % de avance",
  "Max utilization": "Utilización máx",
  "Maximum AISC utilization versus assembly progress": "Utilización máxima AISC frente al avance del montaje",
  "Utilization (AISC 360-22, preliminary)": "Utilización (AISC 360-22, preliminar)",
  "Limit U = 1.0": "Límite U = 1.0",
  "Select a material grade (Structural Properties) to compute the utilization.": "Selecciona un grado de material (Propiedades estructurales) para calcular la utilización.",
  "AISC 360 does not apply to aluminum.": "AISC 360 no aplica al aluminio.",
  "Utilization needs the installer load set to 0 (1.4D, dead load only).": "La utilización requiere la carga del instalador en 0 (1.4D, solo carga muerta).",
  " (off scale, clipped)": " (fuera de escala, recortado)",
  "Maximum axial force versus assembly progress": "Fuerza axial máxima frente al avance del montaje",
  "Maximum deflection versus assembly progress": "Desplazamiento máximo frente al avance del montaje",
  "No data yet": "Aún sin datos",
  "Assembly progress (% of bars installed)": "Progreso del montaje (% de barras instaladas)",
  "Max |F| (envelope)": "|F| máx (envolvente)",
  "Max tension": "Tracción máx",
  "Max compression": "Compresión máx",
  "Stage without solution": "Etapa sin solución",
  "Clipped (> {cap} {unit})": "Recortado (> {cap} {unit})",
  "Selected stage (slider)": "Etapa seleccionada (control)",
  "Computing {count} stages…": "Calculando {count} etapas…",
  "{solved} of {total} stages solved": "{solved} de {total} etapas calculadas",
  " · {unstable} with a mechanism (red triangles, no values)": " · {unstable} con mecanismo (triángulos rojos, sin valores)",
  ". Hover over a point to see its stage.": ". Pasa el cursor sobre un punto para ver su etapa.",
  "{count} point(s) off scale, shown in orange on the top edge.": "{count} punto(s) fuera de escala, mostrados en naranja en el borde superior.",
  "mechanism: no solution": "mecanismo: sin solución",
  "error": "error"
};
const backendEnglish={
  "No hay barras instaladas en esta etapa.": "No bars are installed in this stage.",
  "Equilibrio elástico lineal calculado.": "Linear elastic equilibrium calculated.",
  "Modelo articulado inestable: traslaciones sin rigidez.": "Unstable pinned model: translations without stiffness.",
  "Modelo articulado inestable: mecanismo o matriz mal condicionada.": "Unstable pinned model: mechanism or ill-conditioned matrix.",
  "Modelo inestable: GDL sin rigidez": "Unstable model: degrees of freedom without stiffness",
  "Modelo inestable o excesivamente mal condicionado": "Unstable or severely ill-conditioned model",
  "Se requiere al menos un nodo de apoyo.": "At least one support node is required.",
  "Acero": "Steel",
  "Aluminio": "Aluminum"
};
for(const [es,en] of Object.entries(backendEnglish))if(!spanish[en])spanish[en]=es;
function translate(key,values={}){
 const english=backendEnglish[key]||key;
 let text=language==='es'?(spanish[english]||key):english;
 for(const [name,value] of Object.entries(values))text=text.replaceAll('{'+name+'}',value);
 return text;
}
function translateStatic(){
 document.documentElement.lang=language;
 document.title=language==='es'?'DomeStage+ · Análisis de construcción de domos de acero':'DomeStage+ · Steel Dome Construction Analysis';
 document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=translate(el.dataset.i18n));
 for(const attr of ['aria-label','title'])document.querySelectorAll('[data-i18n-'+attr+']').forEach(el=>el.setAttribute(attr,translate(el.getAttribute('data-i18n-'+attr))));
 $('language-select').value=language;
}

const fmt=(x,n=3)=>Number(x).toLocaleString(language==='es'?'es-MX':'en-US',{maximumFractionDigits:n});
function normalize(a){const n=Math.hypot(...a);return a.map(v=>v/n);}
function mul(a,b){return [a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]];}
function rotate(p){return mul(mul(q,[0,...p]),[q[0],-q[1],-q[2],-q[3]]).slice(1);}

async function api(path,data,options={}){
 const response=await fetch(path,{...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{}),...options});
 let value;try{value=await response.json();}catch{throw Error(translate("Calculation server not found. Ensure server is running."));}
 if(!response.ok)throw Error(value.message||translate("Calculation engine error."));return value;
}

function config(){
  return {
    material: $('sel-material').value,
    profile: $('sel-profile').value,
    connection: $('sel-connection').value,
    support: $('sel-support').value,
    bars_per_step: +$('sel-step').value,
    node_dead_load_kg: 25,
    support_overrides: supportOverrides
  };
}

function stop(){++playbackToken;clearTimeout(sliderTimer);playing=false;$('btn-play').textContent=translate("▶ Play Assembly");}

function clearAnalysis(){
  ++requestId; current=null;
  $('download-stage').disabled=true;
  $('max-tension').textContent='—'; $('max-compression').textContent='—';
  $('max-displacement').textContent='—'; $('installed-weight').textContent='—';
  badge("CALCULATING",'pending'); updateDeformation(); selectionDetail(); draw();
}

let statusKey='INITIALIZING',statusType='pending',messageKey='Connecting to calculation engine…',messageValues={};
function setMessage(key,values={}){messageKey=key;messageValues=values;$('message').textContent=translate(key,values);}
function badge(label,status){
  statusKey=label;statusType=status;
  $('status-badge').textContent=translate(label);
  $('status-badge').className='badge badge-'+(status==='stable'?'stable':status==='unstable'||status==='error'?'unstable':'pending');
}

function populateSupports(preserve=false){
  const previous=selected;
  $('element-select').replaceChildren(new Option(translate("Click member or select here…"),''));
  for(const b of geometry.bars)$('element-select').append(new Option(translate("Bar #")+b.id,'b'+b.id));
  for(const n of geometry.support_nodes)$('element-select').append(new Option(translate("Support node ")+n,'s'+n));
  selected=preserve?previous:''; $('element-select').value=selected;
}

async function replan(reset=false){
  const rev=++revision; stop(); calculated.clear(); clearCharts();
  $('stage-history').textContent=translate("Pending calculation."); clearAnalysis();
  if(!geometry){setMessage("Load a valid geometry model."); return;}
  setMessage("Planning stage assembly sequence…");
  try{
    const p=await api('/api/plan',{geometry,bars_per_step:config().bars_per_step});
    if(rev!==revision)return; plan=p;
    $('stage-slider').max=plan.length-1; $('last-stage').textContent=plan.length-1;
    await setStage(reset?0:Math.min(currentStage,plan.length-1));

  }catch(error){
    if(rev!==revision)return; badge("ERROR",'error'); setMessage(error.message);
  }
}

function applyStage(stage, value){
  currentStage=stage; current=value; const s=plan[stage];
  if(s){
    $('stage-slider').value=stage; $('stage-num').textContent=stage;
    $('active-bars-count').textContent=s.active_count; $('total-bars-count').textContent=s.total_bars;
    $('progress-text').textContent=fmt(s.progress_pct,1)+'%'; $('progress-fill').style.width=s.progress_pct+'%';
    $('newest-bar-text').textContent=s.new_bar_ids.length ? s.new_bar_ids.map(i=>translate("Bar #")+i).join(', ') : translate("Base Ring Installed");
  }
  renderResult(value);
}

function pendingStage(stage){
  currentStage=stage; clearAnalysis(); const s=plan[stage]; if(!s)return;
  $('stage-slider').value=stage; $('stage-num').textContent=stage;
  $('active-bars-count').textContent=s.active_count; $('total-bars-count').textContent=s.total_bars;
  $('progress-text').textContent=fmt(s.progress_pct,1)+'%'; $('progress-fill').style.width=s.progress_pct+'%';
  $('newest-bar-text').textContent=s.new_bar_ids.length ? s.new_bar_ids.map(i=>translate("Bar #")+i).join(', ') : translate("Base Ring Installed");
  draw(); renderCharts();
}

async function setStage(stage){
  if(!plan.length)return; stage=Math.max(0,Math.min(stage,plan.length-1));
  if(calculated.has(stage)){
    const value=calculated.get(stage); applyStage(stage, value); return value;
  }
  pendingStage(stage);
  const token=++requestId, rev=revision;
  setMessage('Solving equilibrium for Stage {stage}…',{stage}); badge("SOLVING…",'pending');
  try{
    const value=await api('/api/stage',{geometry,config:config(),stage});
    if(token!==requestId||rev!==revision)return null;
    calculated.set(stage,value); applyStage(stage, value); return value;
  }catch(error){
    if(token!==requestId||rev!==revision)return null; current=null;
    badge("ERROR",'error'); setMessage(error.message); updateDeformation(); selectionDetail(); draw(); return null;
  }
}

function renderResult(value){
    badge(value.status==='stable'?"STABLE EQUILIBRIUM":value.status==='unstable'?"MECHANISM / UNSTABLE":value.status==='empty'?"NO BARS":"ERROR",value.status);
    setMessage(value.message);
    $('installed-weight').textContent=fmt(value.mass_kg*9.80665/1000)+' kN ('+fmt(value.mass_kg,1)+' kg)';
    if(value.stable){
      $('max-tension').textContent='+'+fmt(value.max_tension_kn)+' kN';
      $('max-compression').textContent='−'+fmt(value.max_compression_kn)+' kN';
      $('max-displacement').textContent=fmt(value.max_displacement_mm)+' mm';
    }
    $('download-stage').disabled=false; updateDeformation(); selectionDetail(); history(); draw(); renderCharts();
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
  if(!selected||!geometry){box.textContent=translate("Click any installed member or support node in the 3D model to inspect its forces."); return;}
  const id=+selected.slice(1), isBar=selected[0]==='b', title=document.createElement('strong');
  title.textContent=(isBar?translate("Member #"):translate("Support Node #"))+id; box.append(title);
  const active=new Set(plan[currentStage]?.active_bar_ids||[]);
  if(isBar&&!active.has(id)){box.append(document.createTextNode(translate(" · Pending installation (inactive in this stage)."))); return;}
  if(!current?.stable){box.append(document.createTextNode(translate(" · No force solution available: ")+(translate(current?.message)||translate("Pending.")))); return;}
  if(isBar){
    const e=current.elements.find(e=>e.id===id); if(!e)return; const s=e.stations;
    box.append(table([
      [translate("End Nodes"), e.i+' → '+e.j],
      [translate("Bar Length"), fmt(e.length_m)+' m'],
      [translate("Axial Force (i / mid / j)"), [s[0], s[Math.floor(s.length/2)], s[s.length-1]].map(v=>fmt(v.N_Vy_Vz_T_My_Mz[0]/1000)).join(' / ')+' kN'],
      [translate("Bending Moment My / Mz (mid)"), s[Math.floor(s.length/2)].N_Vy_Vz_T_My_Mz.slice(4).map(v=>fmt(v/1000)).join(' / ')+' kN·m']
    ]));
    window.AISCView?.appendMember(box,id);
  }else{
    const r=current.reactions.find(r=>r.node_id===id);
    const cond = supportOverrides[id] || config().support;
    if(!r){box.append(document.createTextNode(translate(" · No active connected members yet."))); return;}
    const rows=[
      [translate("Boundary Condition"), cond==='empotrado'?translate("Fixed (6 DOFs)"):translate("Pinned (3 DOFs)")],
      [translate("Reactions Rx / Ry / Rz"), r.values.slice(0,3).map(v=>fmt(v/1000)).join(' / ')+' kN'],
      [translate("Moments Mx / My / Mz"), r.values.slice(3).map(v=>fmt(v/1000)).join(' / ')+' kN·m']
    ];
    if(window.DomeReactions){
      const center=window.DomeReactions.center(geometry);
      const cyl=window.DomeReactions.cylindrical(geometry.nodes.find(n=>n.id===id),r.values,center);
      if(cyl)rows.push([translate("Radial / Tangential / Z"),[cyl.values[0],cyl.values[1],cyl.values[2]].map(v=>fmt(v/1000)).join(' / ')+' kN']);
    }
    box.append(table(rows));
  }
}

function history(){
  const div=$('stage-history'); div.replaceChildren();
  const t=document.createElement('table'), head=t.insertRow();
  for(const label of [translate("Stage"),translate("Active Bars"),translate("Status"),translate("Max Tension (kN)"),translate("Max Compression (kN)")]){
    const th=document.createElement('th'); th.textContent=label; head.append(th);
  }
  for(const s of plan){
    const r=calculated.get(s.stage), tr=t.insertRow();
    for(const value of [s.stage, s.active_count, r?({stable:translate("Equilibrium"),unstable:translate("Mechanism"),empty:translate("No bars"),error:translate("Error")}[r.status]):translate("Pending"), r?.stable?fmt(r.max_tension_kn):'—', r?.stable?fmt(r.max_compression_kn):'—']){
      tr.insertCell().textContent=value;
    }
  }
  div.append(t);
  window.AISCView?.appendHistory(div,plan);
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
      legend[i].textContent=(radial?['Rr','Rt','Rz']:['X','Y','Z'])[i]+' · '+[translate("Green"),translate("Red"),translate("Blue")][i];
    });
  }
  $('reaction-note').textContent=!available?translate("Reactions unavailable without stable solution."):
    show?translate("Reaction vectors in global axes. Select a support to view values."):translate("Support reaction vectors hidden.");
  if(show&&radial&&window.DomeReactions){
    const c=window.DomeReactions.center(geometry);
    if(c)$('reaction-note').textContent=translate('Support center in XY: ({x}, {y}) m · Rr: radial outwards, Rt: tangential CCW.',{x:fmt(c[0]),y:fmt(c[1])});
  }
  reactionTable(show, radial);
}

function reactionTable(show, radial){
  const panel=$('reaction-panel'), div=$('reaction-table'); div.replaceChildren();
  if(!show||!current?.reactions?.length){panel.hidden=true; return;}
  panel.hidden=false;
  const t=document.createElement('table'), head=t.insertRow();
  for(const label of [translate("Node"),...(radial?['Rr','Rt','Rz']:['Rx','Ry','Rz']),'Mx (kN·m)','My (kN·m)','Mz (kN·m)']){
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
  window.AISCView?.update();
  updateReactions();
  const state=deformationView(), factor=$('deformation-factor');
  $('show-deformation').disabled=!state.available;
  factor.disabled=!state.available||!$('show-deformation').checked;
  if(!state.available)$('deformation-note').textContent=translate("Deflection view unavailable without stage equilibrium and displacements.");
  else if(!state.factor_valid)$('deformation-note').textContent=translate("Enter a visual scale factor between 0 and 100000.");
  else if(!state.enabled)$('deformation-note').textContent=translate("Deflection view off · Max true displacement: ")+fmt(state.max_real_mm)+' mm.';
  else $('deformation-note').textContent=translate("Amplified ×")+fmt(state.factor)+translate(" · Real max ")+fmt(state.max_real_mm)+translate(" mm → Visual ")+fmt(state.max_drawn_mm)+' mm.';
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
        const text=vector.label+translate(" · Node ")+r.node_id+' · '+fmt(vector.value/1000)+' kN', x=p[0]+12, y=p[1]-15-i*17;
        ctx.save(); ctx.fillStyle='rgba(255,255,255,.94)'; ctx.fillRect(x-3,y-12,ctx.measureText(text).width+6,16); ctx.restore(); ctx.fillText(text,x,y);
      }
    }
  }
  ctx.restore();
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
 $('force-scale').hidden=!current?.stable||!!window.AISCView?.enabled();$('force-unavailable').hidden=!!current?.stable;
 $('force-min').textContent=(limits.compression?'≤ −':'')+fmt(limits.compression/1000);
 $('force-max').textContent=(limits.tension?'≥ +':'')+fmt(limits.tension/1000);
 // A side with no forces stays yellow rather than implying nonexistent loads.
 document.querySelector('.force-gradient').style.background=`linear-gradient(90deg,${forceColor(-limits.compression,limits)} 0%,#facc15 50%,${forceColor(limits.tension/2,limits)} 75%,${forceColor(limits.tension,limits)} 100%)`;
}

// Overall dimensions use original geometry, independent of stage and visual deformation.
const dimensionCache=new WeakMap();
function modelDimensions(nodes){
 if(!nodes.length)return null;
 let low=nodes[0].z,high=low,span2=0,pair=[nodes[0],nodes[0]];
 for(let i=0;i<nodes.length;i++){
   low=Math.min(low,nodes[i].z);high=Math.max(high,nodes[i].z);
   for(let j=i+1;j<nodes.length;j++){
     const d=(nodes[i].x-nodes[j].x)**2+(nodes[i].y-nodes[j].y)**2;
     if(d>span2){span2=d;pair=[nodes[i],nodes[j]];}
   }
 }
 const apex=nodes.find(n=>n.z===high);
 const diameter=Math.sqrt(span2),margin=Math.max(diameter,high-low,.01)*.12;
 // Fixed world-space offsets: diameter lies in XY at the base elevation.
 const normal=diameter?[-(pair[1].y-pair[0].y)/diameter,(pair[1].x-pair[0].x)/diameter]:[0,-1];
 const edge=Math.max(...nodes.map(n=>n.x*normal[0]+n.y*normal[1]));
 const offset=edge-pair[0].x*normal[0]-pair[0].y*normal[1]+margin;
 const diameterLine=pair.map(n=>[n.x+normal[0]*offset,n.y+normal[1]*offset,low]);
 // Place height one quarter-turn from the diameter's outward offset in plan.
 const heightDirection=[-normal[1],normal[0]];
 const centerXY=[(pair[0].x+pair[1].x)/2,(pair[0].y+pair[1].y)/2];
 const reach=Math.max(...nodes.map(n=>(n.x-centerXY[0])*heightDirection[0]+(n.y-centerXY[1])*heightDirection[1]))+margin;
 const x=centerXY[0]+reach*heightDirection[0],y=centerXY[1]+reach*heightDirection[1];
 // Rotate both annotations +90 degrees about Z (counterclockwise from above).
 const quarterTurn=([px,py,pz])=>[centerXY[0]-(py-centerXY[1]),centerXY[1]+(px-centerXY[0]),pz];
 // Move only the diameter another half-turn around the dome's vertical axis.
 const halfTurn=([px,py,pz])=>[2*centerXY[0]-px,2*centerXY[1]-py,pz];
 const diameterAnchors=pair.map(n=>halfTurn(quarterTurn([n.x,n.y,low])));
 const rotatedDiameterLine=diameterLine.map(p=>halfTurn(quarterTurn(p)));
 const heightLine=[[x,y,low],[x,y,high]].map(quarterTurn);
 const base=nodes.filter(n=>n.z===low).reduce((a,b)=>Math.hypot(a.x-heightLine[0][0],a.y-heightLine[0][1])<=Math.hypot(b.x-heightLine[0][0],b.y-heightLine[0][1])?a:b);
 return {diameter,height:high-low,low,high,pair,apex,base,diameterAnchors,diameterLine:rotatedDiameterLine,heightLine};
}
function drawDimensions(center,scale,w,h){
 if(!$('show-dimensions').checked||!geometry?.nodes.length)return;
 if(!dimensionCache.has(geometry))dimensionCache.set(geometry,modelDimensions(geometry.nodes));
 const d=dimensionCache.get(geometry);
 const project=point=>{const p=rotate(point.map((v,i)=>v-center[i]));return [w/2+p[0]*scale,h/2-p[1]*scale];};
 function dimension(start,end,line,text){
   const a=project(start),b=project(end),A=project(line[0]),B=project(line[1]);
   const dx=B[0]-A[0],dy=B[1]-A[1],length=Math.hypot(dx,dy);
   ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...A);ctx.moveTo(...b);ctx.lineTo(...B);ctx.stroke();
   ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(...A);ctx.lineTo(...B);ctx.stroke();
   if(length>12){
     const angle=Math.atan2(dy,dx);
     for(const [point,t] of [[A,angle],[B,angle+Math.PI]]){
       ctx.beginPath();ctx.moveTo(...point);ctx.lineTo(point[0]+7*Math.cos(t-.4),point[1]+7*Math.sin(t-.4));ctx.lineTo(point[0]+7*Math.cos(t+.4),point[1]+7*Math.sin(t+.4));ctx.closePath();ctx.fill();
     }
   }
   const tw=ctx.measureText(text).width,tx=(A[0]+B[0])/2,ty=(A[1]+B[1])/2;
   // Horizontal text centered over the continuous dimension line drawn above.
   ctx.save();ctx.translate(tx,ty);
   ctx.fillStyle='rgba(255,255,255,.96)';ctx.fillRect(-tw/2-5,-10,tw+10,20);
   ctx.fillStyle='#334155';ctx.fillText(text,0,0);ctx.restore();
 }
 ctx.save();ctx.globalAlpha=1;ctx.strokeStyle='#334155';ctx.fillStyle='#334155';ctx.lineWidth=1;ctx.font='600 12px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
 dimension(d.diameterAnchors[0],d.diameterAnchors[1],d.diameterLine,'D: '+fmt(d.diameter)+' m');
 dimension([d.base.x,d.base.y,d.base.z],[d.apex.x,d.apex.y,d.apex.z],d.heightLine,'H: '+fmt(d.height)+' m');
 ctx.restore();
}

// 3D Canvas Rendering
function draw(){
  const limits=forceLimits(current); updateLegend(limits);
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
    const isSelected=selected==='b'+s.b.id;
    if(isSelected||(installed&&fresh.has(s.b.id))){
      ctx.strokeStyle=isSelected?'#000000':'#FF00FF'; ctx.lineWidth=isSelected?7:6; ctx.stroke();
    }
    ctx.strokeStyle=!installed?'#CACACA':(window.AISCView?.color(s.b.id)||forceColor(f,limits));
    ctx.lineWidth=installed?3:1; ctx.stroke();
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
      ctx.strokeStyle=window.AISCView?.color(s.b.id)||'#7C3AED';
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
  drawDimensions(center,scale,w,h);
}

// Interaction Listeners
$('show-dimensions').addEventListener('change',draw);
$('element-select').addEventListener('change',()=>{selected=$('element-select').value; selectionDetail(); draw();});
$('stage-slider').addEventListener('input',()=>{
  stop();
  const stage=+$('stage-slider').value;
  if(calculated.has(stage)){
    applyStage(stage, calculated.get(stage));
  } else {
    pendingStage(stage);
    clearTimeout(sliderTimer);
    sliderTimer=setTimeout(()=>setStage(stage),80);
  }
});
$('btn-prev').onclick=()=>{stop(); setStage(currentStage-1);};
$('btn-next').onclick=()=>{stop(); setStage(currentStage+1);};
function showAnalysisProgress(done,total,complete=false,error=''){
  const percent=total?Math.floor(done/total*100):0;
  $('analysis-progress').hidden=false;
  $('analysis-fill').style.width=percent+'%';
  $('analysis-fill').style.background=complete?'#16a34a':'#2563eb';
  $('analysis-meter').setAttribute('aria-valuenow',percent);
  $('analysis-status').textContent=(language==='es'?'Análisis: ':'Analysis: ')+percent+'%'+(error?' · '+error:complete?(language==='es'?' · Completado':' · Complete'):'');
}
async function analyzeStages(){
  if(analyzing||$('btn-analyze').disabled||!geometry||!plan.length)return;
  stop();const token=++analysisToken,rev=revision,model=geometry,cfg=config(),steps=[...plan];
  analyzing=true;$('btn-analyze').disabled=true;let done=0,complete=false;showAnalysisProgress(0,steps.length);
  try{
    for(const step of steps){
      const result=calculated.get(step.stage)||await api('/api/stage',{geometry:model,config:cfg,stage:step.stage});
      if(token!==analysisToken||rev!==revision)return;
      calculated.set(step.stage,result);
      await window.AISCView?.precompute(step.stage);
      if(token!==analysisToken||rev!==revision)return;
      showAnalysisProgress(++done,steps.length);
    }
    showAnalysisProgress(done,steps.length,true);window.AISCView?.update();selectionDetail();draw();history();complete=true;
  }catch(e){if(token===analysisToken)showAnalysisProgress(done,steps.length,false,e.message);}
  finally{if(token===analysisToken){analyzing=false;$('btn-analyze').disabled=complete;}}
}
async function playAssembly(){
  if(playing){stop();return;}
  if(!plan.length)return;
  stop();const token=playbackToken,rev=revision;
  playing=true;$('btn-play').textContent=translate('⏸ Pause');
  try{
    for(let stage=currentStage;stage<plan.length;stage++){
      if(token!==playbackToken||rev!==revision)return;
      const result=await setStage(stage);
      if(token!==playbackToken||rev!==revision)return;
      if(!result)break;
      if(stage<plan.length-1)await new Promise(resolve=>setTimeout(resolve,250));
    }
  }finally{if(token===playbackToken)stop();}
}
$('btn-analyze').onclick=analyzeStages;
$('btn-play').onclick=playAssembly;


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
        alert(translate('✓ Loaded connection overrides for {count} support nodes from CSV.',{count:newSupports.length}));
      }
    } catch(err){
      alert(translate("Error parsing CSV: ") + err.message);
    }
  };
  reader.readAsText(file);
});

async function importDXF(){
  const file=$('dxf-file-input').files[0]; if(!file)return;
  const rev=++revision; stop(); calculated.clear(); clearCharts(); geometry=null; plan=[]; clearAnalysis();
  supportOverrides={}; setMessage("Reading DXF wireframe connectivity…");
  try{
    const value=await api('/api/import?units='+encodeURIComponent($('dxf-units').value)+'&tolerance='+encodeURIComponent(+$('dxf-tolerance').value/1000),null,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:await file.arrayBuffer()});
    if(rev!==revision)return; geometry=value.geometry; setModelSource(file.name,false);
    populateSupports(); await replan(true);
  }catch(e){
    if(rev!==revision)return; badge("INVALID DXF",'error'); setMessage(e.message);
  }
}
for(const id of ['dxf-file-input','dxf-units','dxf-tolerance'])$(id).addEventListener('change',importDXF);

// Results report: every stage is solved on the server and returned as an Excel workbook.
// Member checks use the material grade selected for the AISC view (same fields it reads).
function reportDesign(){
  const grade=$('design-grade')?.value||'';
  return grade==='custom'?{grade,Fy_MPa:$('design-fy').value,Fu_MPa:$('design-fu').value,source:$('design-source').value}:(grade?{grade}:{});
}
$('download-report').onclick=async()=>{
  if(!geometry||!plan.length)return; const button=$('download-report'), label=button.innerHTML;
  button.disabled=true; button.textContent=translate('Building report ({n} stages)…',{n:plan.length});
  try{
    const response=await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({geometry,config:config(),design:reportDesign(),language})});
    if(!response.ok){let m=translate('The engine could not build the report.');try{m=(await response.json()).message||m;}catch{} throw Error(m);}
    const url=URL.createObjectURL(await response.blob()), a=document.createElement('a');
    a.href=url; a.download=language==='es'?'reporte-resultados-domo.xlsx':'dome-results-report.xlsx'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    const d=reportDesign();
    $('message').textContent=translate(config().material!=='Acero'?'Results report exported. Member checks: not applicable to aluminum.':d.grade?'Results report exported with preliminary AISC member checks.':'Results report exported. Member checks: not checked (select a material grade).');
  }catch(e){$('message').textContent=e.message;}
  finally{button.disabled=false; button.innerHTML=label;}
};

// Default model (QuickDome) loaded at start; an uploaded DXF replaces it until the user restores it.
let modelSource={name:'',isDefault:true};
// Utilization figures (plan + elevation per % of progress) for the calculation report.
$('download-figures').onclick=async()=>{
  if(!geometry||!plan.length)return; const button=$('download-figures'), label=button.innerHTML;
  button.disabled=true; button.textContent=translate('Building utilization figures…');
  try{
    const response=await fetch('/api/utilization-figures',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({geometry,config:config(),design:reportDesign(),milestones:$('figures-milestones').value,language,model_name:modelSource.name})});
    if(!response.ok){let m=translate('The engine could not build the figures.');try{m=(await response.json()).message||m;}catch{} throw Error(m);}
    const url=URL.createObjectURL(await response.blob()), a=document.createElement('a');
    a.href=url; a.download=language==='es'?'figuras-utilizacion.html':'utilization-figures.html'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('message').textContent=translate('Utilization figures exported.');
  }catch(e){$('message').textContent=e.message;}
  finally{button.disabled=false; button.innerHTML=label;}
};
function setModelSource(name,isDefault){
  modelSource={name,isDefault};
  $('model-source').textContent=name+(isDefault?' '+translate('(default)'):'');
  $('btn-default-model').hidden=isDefault;
}
async function loadDefaultModel(){
  const rev=++revision; stop(); calculated.clear(); clearCharts(); geometry=null; plan=[]; clearAnalysis();
  supportOverrides={}; setMessage("Loading default model…");
  const value=await api('/api/default-model');
  if(rev!==revision)return;
  geometry=value.geometry; setModelSource(value.name,true);
  $('dxf-file-input').value='';
  populateSupports(); await replan(true);
}
$('btn-default-model').addEventListener('click',()=>loadDefaultModel().catch(e=>{badge("ERROR",'error');setMessage(e.message);}));

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
function clearCharts(){++analysisToken;analyzing=false;$('btn-analyze').disabled=false;$('analysis-progress').hidden=true;++seriesToken;series=null;$('btn-charts-csv').disabled=true;$('btn-charts').disabled=false;$('charts-message').textContent=translate('Compute all stages to see how the maximum axial force and maximum deflection change as assembly progresses.');renderCharts();}
const OUTLIER_FACTOR=20;
function median(v){const a=[...v].sort((x,y)=>x-y),m=a.length>>1;return a.length%2?a[m]:(a[m-1]+a[m])/2;}
// opts.limit: draw a reference line (e.g. utilization = 1) and paint points above it red.
// opts.noData: message when the series exists but these lines have no values (e.g. no material grade).
function chart(svg,lines,unit,emptyText,opts={}){
 svg.replaceChildren();const W=600,H=340,L=62,R=16,T=18,B=86,pw=W-L-R,ph=H-T-B;
 const useLog=$('chart-log').checked,useClip=$('chart-clip').checked;
 const x=p=>L+p/100*pw;
 const values=series?series.flatMap(s=>lines.map(l=>s[l.key])).filter(v=>v!==null&&v!==undefined&&Number.isFinite(v)):[];
 const positive=values.filter(v=>v>0);
 // Recorte: el eje se limita a OUTLIER_FACTOR × la mediana de los valores positivos.
 let cap=Infinity;
 if(useClip&&positive.length){const c=OUTLIER_FACTOR*median(positive);if(Math.max(...positive)>c)cap=c;}
 const limit=Number.isFinite(opts.limit)?opts.limit:null;
 if(limit!==null&&cap<limit)cap=limit; // never clip below the reference line
 const inRange=values.filter(v=>v<=cap),dataMax=Math.max(inRange.length?Math.max(...inRange):0,limit??0);
 let edge=Infinity;
 let y,ticks;
 if(useLog&&positive.length){
  const pin=positive.filter(v=>v<=cap),lo=10**Math.floor(Math.log10(Math.min(...(pin.length?pin:positive)))),hi=10**Math.ceil(Math.log10(Math.max(dataMax,lo*10)));
  if(cap<Infinity)edge=hi;
  const span=Math.log10(hi)-Math.log10(lo);
  y=v=>T+ph-(Math.log10(Math.max(v,lo))-Math.log10(lo))/span*ph;
  ticks=[];for(let e=Math.log10(lo);e<=Math.log10(hi)+1e-9;e++)ticks.push(10**e);
 }else{
  // With a reference line and every value below 1.25× it, use a 0.25-step axis up to 1.25× the limit.
  const top=limit!==null&&dataMax<=limit*1.25?limit*1.25:niceMax(dataMax*1.05);if(cap<Infinity)edge=top;
  y=v=>T+ph-Math.min(v,top)/top*ph;ticks=[0,1,2,3,4,5].map(i=>top*i/5);
 }
 for(const v of ticks)svg.append(el('line',{x1:L,x2:W-R,y1:y(v),y2:y(v),class:'chart-grid'}),el('text',{x:L-6,y:y(v)+4,'text-anchor':'end',class:'chart-label'},fmt(v,v<10?2:1)));
 if(edge<Infinity)svg.append(el('line',{x1:L,x2:W-R,y1:T,y2:T,stroke:'#F59E0B','stroke-width':1.5,'stroke-dasharray':'2 3'}));
 const yc=v=>v>cap?T:y(v);
 if(limit!==null){svg.append(el('line',{x1:L,x2:W-R,y1:y(limit),y2:y(limit),stroke:'#DC2626','stroke-width':1.5,'stroke-dasharray':'6 4'}));
  svg.append(el('text',{x:W-R-4,y:y(limit)-5,'text-anchor':'end','font-size':11,'font-weight':700,fill:'#B91C1C'},opts.limitLabel||String(limit)));}
 for(const p of [0,25,50,75,100])svg.append(el('line',{x1:x(p),x2:x(p),y1:T,y2:T+ph,class:'chart-grid'}),el('text',{x:x(p),y:T+ph+16,'text-anchor':'middle',class:'chart-label'},p+'%'));
 svg.append(el('line',{x1:L,x2:L,y1:T,y2:T+ph,class:'chart-axis'}),el('line',{x1:L,x2:W-R,y1:T+ph,y2:T+ph,class:'chart-axis'}));
 svg.append(el('text',{x:L+pw/2,y:T+ph+34,'text-anchor':'middle',class:'chart-title'},translate('Assembly progress (% of bars installed)')));
 svg.append(el('text',{x:14,y:T+ph/2,'text-anchor':'middle',class:'chart-title',transform:`rotate(-90 14 ${T+ph/2})`},unit+(useLog?' · log':'')));
 if(!series){svg.append(el('text',{x:L+pw/2,y:T+ph/2,'text-anchor':'middle',class:'chart-label'},translate(emptyText)));return 0;}
 if(!values.length&&opts.noData){svg.append(el('text',{x:L+pw/2,y:T+ph/2,'text-anchor':'middle',class:'chart-label',fill:'#B45309'},opts.noData));return 0;}
 let clipped=0;
 for(const l of lines){
  let d='';let pen=false;
  for(const s of series){const v=s[l.key];if(v===null||v===undefined){pen=false;continue;}d+=(pen?'L':'M')+x(s.progress_pct).toFixed(1)+' '+yc(v).toFixed(1)+' ';pen=true;}
  if(d)svg.append(el('path',{d,fill:'none',stroke:l.color,'stroke-width':l.width||2,'stroke-opacity':l.opacity||1,'stroke-linejoin':'round'}));
  for(const s of series){const v=s[l.key];if(v===null||v===undefined)continue;const px=x(s.progress_pct),label=`${l.label} · ${translate('Stage')} ${s.stage} · ${fmt(s.progress_pct,1)}% · ${fmt(v)}${l.unit?' '+l.unit:''}`+(l.extra?l.extra(s):'');
   if(v>cap){if(l.width>3)continue;clipped++;const m=el('path',{d:`M${px-5} ${T+7} L${px+5} ${T+7} L${px} ${T-3} Z`,fill:'#F59E0B',stroke:'#B45309','stroke-width':1});m.append(el('title',{},label+translate(' (off scale, clipped)')));svg.append(m);continue;}
   const c=el('circle',{cx:px,cy:y(v),r:l.width>3?0:2.6,fill:limit!==null&&v>limit?'#DC2626':l.color});c.append(el('title',{},label));svg.append(c);}
 }
 for(const s of series)if(s.status!=='stable'&&s.status!=='empty'){const m=el('path',{d:`M${x(s.progress_pct)-4} ${T+ph+1} L${x(s.progress_pct)+4} ${T+ph+1} L${x(s.progress_pct)} ${T+ph-7} Z`,fill:'#EF4444'});m.append(el('title',{},`${translate('Stage')} ${s.stage} · ${fmt(s.progress_pct,1)}% · ${s.status==='unstable'?translate('mechanism: no solution'):translate('error')}`));svg.append(m);}
 // Marker (not data): where the stage chosen with the slider sits on the progress axis.
 const cur=plan[currentStage];if(cur){const cx=x(cur.progress_pct),right=cx<L+pw-80;
  svg.append(el('line',{x1:cx,x2:cx,y1:T,y2:T+ph,stroke:'#00C853','stroke-width':2,'stroke-dasharray':'5 4'}));
  svg.append(el('text',{x:right?cx+5:cx-5,y:T+12,'text-anchor':right?'start':'end','font-size':11,'font-weight':700,fill:'#00873A'},`${translate('Stage')} ${cur.stage} · ${fmt(cur.progress_pct,1)}%`));}
 const legend=[...lines.filter(l=>!l.hideLegend),{label:translate('Stage without solution'),color:'#EF4444',marker:true},...(clipped?[{label:translate('Clipped (> {cap} {unit})',{cap:fmt(cap,1),unit:lines[0].unit}),color:'#F59E0B',marker:true}]:[]),...(limit!==null?[{label:opts.limitLabel||String(limit),color:'#DC2626',dash:true}]:[]),{label:translate('Selected stage (slider)'),color:'#00C853',dash:true}];
 // Leyenda en filas debajo del eje X: nunca tapa los datos.
 let gx=L,ly=T+ph+52;
 for(const l of legend){const w=30+l.label.length*6.2;if(gx+w>W-R){gx=L;ly+=17;}
  svg.append(l.marker?el('path',{d:`M${gx} ${ly+4} L${gx+10} ${ly+4} L${gx+5} ${ly-4} Z`,fill:l.color}):el('line',{x1:gx,x2:gx+16,y1:ly,y2:ly,stroke:l.color,'stroke-width':Math.min(l.width||2,6),'stroke-dasharray':l.dash?'5 4':'','stroke-opacity':l.opacity?Math.max(l.opacity,.35):1}));
  svg.append(el('text',{x:gx+22,y:ly+4,class:'chart-label'},l.label));gx+=w;}
 return clipped;
}
function renderCharts(){
 let clipped=chart($('chart-force'),[{key:'max_force_kn',label:translate('Max |F| (envelope)'),color:'#0B2265',width:7,opacity:.18,unit:'kN'},{key:'max_tension_kn',label:translate('Max tension'),color:'#001B96',unit:'kN'},{key:'max_compression_kn',label:translate('Max compression'),color:'#EF4444',unit:'kN'}],translate('Axial force (kN)'),translate('No data yet'));
 const mode=series?.[0]?.utilization_status;
 const noUtil={no_grade:'Select a material grade (Structural Properties) to compute the utilization.',aluminum:'AISC 360 does not apply to aluminum.',installer:'Utilization needs the installer load set to 0 (1.4D, dead load only).'}[mode];
 clipped+=chart($('chart-utilization'),[{key:'max_utilization',label:translate('Max utilization'),color:'#7C3AED',unit:'',extra:s=>s.governing_bar===null||s.governing_bar===undefined?'':` · ${translate('Bar #')}${s.governing_bar} · ${s.governing_equation||''}`}],translate('Utilization (AISC 360-22, preliminary)'),translate('No data yet'),{limit:1,limitLabel:translate('Limit U = 1.0'),noData:noUtil?translate(noUtil):null});
 clipped+=chart($('chart-displacement'),[{key:'max_displacement_mm',label:translate('Max deflection'),color:'#5A85D7',unit:'mm'}],translate('Max deflection (mm)'),translate('No data yet'));
 const note=$('charts-clip-note');if(note)note.textContent=series&&clipped?translate('{count} point(s) off scale, shown in orange on the top edge.',{count:clipped}):'';
}
for(const id of ['chart-log','chart-clip'])$(id).addEventListener('change',renderCharts);
// The utilization chart depends on the material grade: changing it invalidates the computed series.
for(const id of ['design-grade','design-fy','design-fu','design-source'])$(id)?.addEventListener('input',()=>{clearCharts();});
$('btn-charts').onclick=async()=>{
 if(!geometry||!plan.length)return;const token=++seriesToken,rev=revision;$('btn-charts').disabled=true;
 $('charts-message').textContent=translate('Computing {count} stages…',{count:plan.length});
 try{const value=await api('/api/progress',{geometry,config:config(),design:reportDesign()});if(token!==seriesToken||rev!==revision)return;series=value;
  const solved=series.filter(s=>s.status==='stable').length,unstable=series.filter(s=>s.status==='unstable').length;
  $('charts-message').textContent=translate('{solved} of {total} stages solved',{solved,total:series.length})+(unstable?translate(' · {unstable} with a mechanism (red triangles, no values)',{unstable}):'')+translate('. Hover over a point to see its stage.');
  $('btn-charts-csv').disabled=false;renderCharts();
 }catch(e){if(token!==seriesToken)return;$('charts-message').textContent=e.message;}finally{if(token===seriesToken)$('btn-charts').disabled=false;}
};
$('btn-charts-csv').onclick=()=>{if(!series)return;const cols=['stage','progress_pct','active_count','status','max_tension_kn','max_compression_kn','max_force_kn','max_displacement_mm','max_utilization','governing_bar','governing_equation','utilization_status'];const csv=[cols.join(','),...series.map(s=>cols.map(c=>s[c]===null||s[c]===undefined?'':s[c]).join(','))].join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download='assembly-progress.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
renderCharts();

// Language changes preserve model, support overrides, selected element and display settings.
$('language-select').addEventListener('change',()=>{
 language=$('language-select').value;
 try{localStorage.setItem('domestage-language',language);}catch{}
 translateStatic();
 for(const option of $('sel-material').options)option.textContent=translate(option.value);
 if(geometry)populateSupports(true);
 if(current)renderResult(current);else{badge(statusKey,statusType);setMessage(messageKey,messageValues);updateDeformation();selectionDetail();history();draw();}
 $('btn-play').textContent=translate(playing?'⏸ Pause':'▶ Play Assembly');
 const stage=plan[currentStage];
 if(stage)$('newest-bar-text').textContent=stage.new_bar_ids.length?stage.new_bar_ids.map(i=>translate('Bar #')+i).join(', '):translate('Base Ring Installed');
 renderCharts();
 if(modelSource.name)setModelSource(modelSource.name,modelSource.isDefault);
});
window.AISCView.init({context:()=>({geometry,config:config(),current,stage:currentStage,language}),redraw:()=>{selectionDetail();draw();history();},format:fmt});
translateStatic();

// Boot
(async()=>{
  try{
    const c=await api('/api/catalog');
    for(const item of c.profiles)$('sel-profile').append(new Option(item,item));
    $('sel-profile').selectedIndex=2;
    for(const item of c.materials)$('sel-material').append(new Option(translate(item),item));
    await loadDefaultModel();
    const urlParams = new URLSearchParams(window.location.search);
    if(urlParams.has('stage')) await setStage(parseInt(urlParams.get('stage'),10));
    if(urlParams.get('deformed')==='1'){ $('show-deformation').checked=true; updateDeformation(); draw(); }
    if(urlParams.get('reactions')==='1'){ $('show-reactions').checked=true; updateReactions(); draw(); }
    if(urlParams.get('aisc')==='1'){ $('show-aisc').checked=true; $('design-grade').value='a500-21-c'; window.AISCView?.update(); draw(); }
  }catch(e){
    badge("SERVER OFFLINE",'error'); setMessage(e.message+translate(" · Run: PYTHONPATH=src python -m domestage.server"));
  }
  window.simulator = {
    setStage,
    getStage: () => currentStage,
    getPlan: () => plan,
    getCurrent: () => current,
    getCalculated: () => calculated,
    applyStage,
    replan,
    draw,
    canvas,
    setCameraQ: (newQ) => { q = normalize(newQ); draw(); },
    getCameraQ: () => q,
    orbitZ: (angleRad) => {
      const rotZ = [Math.cos(angleRad / 2), 0, 0, Math.sin(angleRad / 2)];
      q = normalize(mul(q, rotZ));
      draw();
    },
    orbit: (dx, dy) => {
      const n = Math.hypot(dx, dy);
      if(n){
        const t = n * 0.004;
        q = normalize(mul([Math.cos(t), dy/n*Math.sin(t), dx/n*Math.sin(t), 0], q));
        draw();
      }
    }
  };
})();
})();
