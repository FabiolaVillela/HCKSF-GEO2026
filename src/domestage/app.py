"""Dashboard con equilibrio real por etapa. Ejecutar desde la raíz del repo."""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/'src') not in sys.path: sys.path.insert(0,str(ROOT/'src'))
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from domestage.assembly import (catalog,geometry_from_dxf,geometry_from_structure,stage_plan,solve_stage)
from domestage.demo_model import generate_demo_dome
from domecalc.importer import declared_units,UNITS
from domecalc.viewer import export_viewer

st.set_page_config(page_title='DomeStage · motor estructural',layout='wide')
st.title('GEOMETRICA · Montaje de domos')
st.caption('Equilibrio elástico lineal real por etapa · peso propio y un instalador')

@st.cache_data(show_spinner=False,max_entries=4)
def import_geometry(content,units,tolerance):
    return geometry_from_dxf(content,units,tolerance)

@st.cache_data(show_spinner=False,max_entries=32)
def calculate(geometry,config,stage):
    # Todos los parámetros participan en la clave de caché, incluida la geometría.
    return solve_stage(geometry,config,stage)

with st.sidebar:
    source=st.radio('Fuente del modelo',['Generador Sintético Paramétrico','Importar Archivo DXF'])
    if source=='Generador Sintético Paramétrico':
        rings=st.slider('Número de anillos',2,8,4)
        sides=st.slider('Lados por anillo',6,24,12,2)
        radius=st.number_input('Radio (m)',min_value=.1,value=6.)
        height=st.number_input('Altura (m)',min_value=.1,value=3.2)
        model=generate_demo_dome(rings,sides,radius,height)
        geometry=geometry_from_structure(model)
    else:
        upload=st.file_uploader('Subir DXF',type=['dxf'])
        if upload is None:
            st.info('Carga un DXF para comenzar.');st.stop()
        try:
            content=upload.getvalue();detected=declared_units(content)
            choices=['Seleccionar…',*UNITS]
            units=st.selectbox('Unidades',choices,index=choices.index(detected) if detected else 0)
            tolerance=st.number_input('Tolerancia (mm)',min_value=.0001,value=.001,format='%.4f')/1000
            if units=='Seleccionar…':st.stop()
            geometry,report=import_geometry(content,units,tolerance)
        except ValueError as exc:
            st.error(str(exc));st.stop()
        with st.expander('Diagnóstico DXF'):st.json(report)
    c=catalog()
    material=st.selectbox('Material',c['materials'])
    profile=st.selectbox('Perfil HSS',c['profiles'],index=2)
    connection=st.radio('Conexiones',['articulada','empotrada'],format_func=lambda s:s.capitalize())
    support=st.radio('Apoyos',['articulado','empotrado'],format_func=lambda s:s.capitalize())
    geometry['support_nodes']=st.multiselect('Nodos de apoyo',[n['id'] for n in geometry['nodes']],default=geometry['support_nodes'])
    step=st.selectbox('Barras por etapa',[1,2,3,4],index=1)
    worker=st.number_input('Instalador y herramientas (kg)',min_value=0.,max_value=10000.,value=100.,step=10.)
    st.caption('Un instalador en nodo j de la última barra nueva; no se aplica en etapa 0.')
config=dict(material=material,profile=profile,connection=connection,support=support,bars_per_step=step,worker_kg=worker)
try:
    plan=stage_plan(geometry,step)
except ValueError as exc:
    st.error(str(exc));st.stop()
# Mantener la posición solo mientras la secuencia y propiedades no cambien.
signature=json.dumps([geometry,config],sort_keys=True)
if st.session_state.get('geometry_signature')!=signature:
    st.session_state['geometry_signature']=signature
    st.session_state['stage_idx']=0
    st.session_state['visited']={}
max_stage=len(plan)-1
if max_stage:
    stage=st.slider('Etapa de montaje',0,max_stage,key='stage_idx')
else:
    stage=0;st.write('Etapa 0 · todas las barras están instaladas en la base.')
with st.spinner('Calculando equilibrio de la etapa…'):
    try:result=calculate(geometry,config,stage)
    except ValueError as exc:st.error(str(exc));st.stop()
st.session_state['visited'][stage]=result
st.progress(result['progress_pct']/100)
st.write(f'Barras instaladas: {result["active_count"]} / {result["total_bars"]} · nuevas: {result["new_bar_ids"]}')
if result['stable']:
    st.success('Equilibrio calculado: '+result['message'])
elif result['status']=='empty':
    st.info(result['message'])
else:
    st.error('Etapa sin solución: '+result['message'])
cols=st.columns(4)
cols[0].metric('Peso propio instalado',f'{result["mass_kg"]*9.80665/1000:.3f} kN')
cols[1].metric('Carga instalador',f'{result["worker_load_N"]/1000:.3f} kN')
cols[2].metric('Tracción máxima',f'{result["max_tension_kn"]:.3f} kN' if result['stable'] else '—')
cols[3].metric('Compresión máxima',f'{result["max_compression_kn"]:.3f} kN' if result['stable'] else '—')
# Mantener el visualizador del equipo si Plotly está instalado.
try:
    from domestage.viz import create_dome_3d_figure,create_history_chart
except ImportError:
    create_dome_3d_figure=None
if create_dome_3d_figure:
    from domestage.schema import StructureModel
    nodes=pd.DataFrame([(n['id'],n['x'],n['y'],n['z']) for n in geometry['nodes']],columns=['node_id','x','y','z'])
    bars=pd.DataFrame([(b['id'],b['i'],b['j'],profile,0) for b in geometry['bars']],columns=['bar_id','node_i','node_j','profile','stage'])
    supports=pd.DataFrame([(n,True,True,True) for n in geometry['support_nodes']],columns=['node_id','fix_x','fix_y','fix_z'])
    view_model=StructureModel(nodes,bars,pd.DataFrame(),supports,pd.DataFrame())
    fig=create_dome_3d_figure(view_model,result['active_bar_ids'],result['new_bar_ids'],
                              pd.Series({int(k):v for k,v in result['forces'].items()},dtype=float) if result['stable'] else None,
                              analysis_stable=result['stable'] is True,worker_node=result['worker_node'],support_label=support)
    st.plotly_chart(fig,use_container_width=True)
if result['stable']:
    with tempfile.TemporaryDirectory() as directory:
        viewer=export_viewer(result['solution'],Path(directory)/'etapa.html').read_text()
    if not create_dome_3d_figure:components.html(viewer,height=880,scrolling=True)
    st.download_button('Descargar visor de la etapa',viewer,f'etapa-{stage}.html','text/html')
    options=[f'Barra {b}' for b in result['active_bar_ids']]+[f'Apoyo {r["node_id"]}' for r in result['reactions']]
    selection=st.selectbox('Consultar barra o apoyo',options)
    if selection.startswith('Barra '):
        bid=int(selection.split()[-1]);element=next(e for e in result['elements'] if e['id']==bid)
        st.json({'barra':bid,'estaciones':element['stations']})
    else:
        nid=int(selection.split()[-1]);st.json(next(r for r in result['reactions'] if r['node_id']==nid))
st.download_button('Descargar resultado de etapa',json.dumps({'geometry':geometry,'config':config,'result':result},indent=2),f'etapa-{stage}.json','application/json')
with st.expander('Historial de etapas calculadas'):
    st.json([{**{k:r[k] for k in ('stage','active_count','status','max_tension_kn','max_compression_kn')}} for _,r in sorted(st.session_state['visited'].items())])
st.caption('Equilibrio independiente de cada etapa. No incluye pandeo, resistencia normativa ni deformaciones acumuladas del montaje.')
