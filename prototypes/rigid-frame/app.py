"""Ejecutar: streamlit run app.py (desde prototypes/rigid-frame)."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile
import streamlit as st
import streamlit.components.v1 as components
from domecalc.catalog import MATERIALS, HSS, properties
from domecalc.core import export
from domecalc.importer import UNITS, declared_units, inspect_dxf
from domecalc.viewer import export_viewer
from domecalc.workflow import run_analysis

st.set_page_config(page_title='Domo · importar y analizar', layout='wide')
st.title('Importar y analizar una estructura DXF')
st.caption('Peso propio · análisis elástico lineal · conexiones y apoyos configurables')

@st.cache_data(show_spinner=False)
def inspect(content, units, tolerance, layers):
    return inspect_dxf(content, units, tolerance, layers)

@st.cache_data(show_spinner=False)
def detect_units(content):
    return declared_units(content)

@st.cache_data(show_spinner=False)
def outputs(result):
    with tempfile.TemporaryDirectory() as directory:
        export(result, directory)
        viewer = export_viewer(result, Path(directory)/'visor.html').read_text(encoding='utf-8')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in Path(directory).iterdir(): archive.writestr(path.name,path.read_bytes())
    return viewer, buffer.getvalue()

st.subheader('1. Importar DXF y revisar conectividad')
example = Path(__file__).with_name('examples')/'demo-dome.dxf'
if example.exists():
    st.download_button('Descargar DXF de ejemplo',example.read_bytes(),'demo-dome.dxf','application/dxf')
upload = st.file_uploader('Archivo DXF',type=['dxf'],help='Hasta 20 MB. Líneas, polilíneas rectas y bloques en espacio modelo.')
if upload is None:
    st.info('Carga un DXF para revisar su geometría antes de elegir las propiedades.')
    st.stop()
content = upload.getvalue()
try:
    detected = detect_units(content)
except ValueError as exc:
    st.error(str(exc)); st.stop()
choices = ['Seleccionar…',*UNITS]
units = st.selectbox('Unidades del dibujo',choices,index=choices.index(detected) if detected else 0,
                     key='units_'+hashlib.sha256(content).hexdigest()[:12])
st.caption(f'Unidades declaradas: {detected or "sin unidades compatibles; selección obligatoria"}. Z es el eje vertical.')
tolerance = st.number_input('Tolerancia para unir extremos (mm)',min_value=.0001,max_value=100.,value=.001,format='%.4f')/1000
layer_text = st.text_input('Capas estructurales (opcional, separadas por coma)',help='Vacío: todas. Usa este filtro para excluir cubierta, textos u otra geometría.')
layers = tuple(s.strip() for s in layer_text.split(',') if s.strip())
if units=='Seleccionar…': st.stop()
try:
    inspection = inspect(content,units,tolerance,layers)
except ValueError as exc:
    st.error(str(exc)); st.stop()
report = inspection.report
cols = st.columns(3)
for col,title,value in zip(cols,['Nodos','Barras','Componentes conectados'],[report['nodes'],report['elements'],len(report['components'])]): col.metric(title,value)
for error in report['errors']: st.error(error)
for warning in report['warnings']: st.warning(warning)
with st.expander('Detalle de conectividad, capas y coordenadas'):
    st.json(report)
    coordinates = 'nodo,x_m,y_m,z_m\n'+'\n'.join(f'{i},{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}' for i,p in enumerate(inspection.model.nodes))
    st.code(coordinates,language='csv')
st.download_button('Descargar diagnóstico JSON',json.dumps(report,indent=2,ensure_ascii=False),'conectividad.json','application/json')
if not inspection.ready: st.stop()
if report['nodes']>500:
    st.error('Esta versión admite hasta 500 nodos por análisis. Filtra capas o utiliza un modelo menor.'); st.stop()

st.subheader('2. Elegir material, perfil y conexiones')
material_name = st.selectbox('Material',list(MATERIALS))
profile_name = st.selectbox('Perfil HSS circular',list(HSS),index=2)
material,section = properties(material_name,profile_name)
st.caption(f'E = {material.E/1e9:g} GPa · ν = {material.nu:g} · densidad = {material.density:g} kg/m³ · área = {section.A*1e6:.2f} mm² · masa lineal = {section.A*material.density:.3f} kg/m')
st.caption('Catálogo geométrico nominal: diámetro exterior × espesor. Confirmar dimensiones, aleación y disponibilidad con el proveedor.')
connections = st.radio('Conexiones entre barras',['Empotradas','Articuladas'],horizontal=True)
if connections=='Articuladas':
    st.info('Armadura espacial: solo axial; peso propio repartido a los extremos. Se comprobará si existen mecanismos.')
else:
    st.info('Pórtico espacial: las uniones transmiten axial, cortantes, torsión y momentos.')

st.subheader('3. Confirmar apoyos y analizar')
model = inspection.model
zmin = min(p[2] for p in model.nodes)
base = [i for i,p in enumerate(model.nodes) if abs(p[2]-zmin)<=tolerance]
if len(base)==len(model.nodes):
    st.warning('Todos los nodos tienen la misma cota Z. Confirma el eje vertical y selecciona los apoyos reales; la propuesta inicial incluye todos los nodos.')
geometry_key = hashlib.sha256(content+repr((units,tolerance,layers)).encode()).hexdigest()
support_nodes = st.multiselect('Nodos de apoyo',list(range(len(model.nodes))),default=base,key='supports_'+geometry_key,
                               help='Se proponen los nodos de cota mínima. Confirma o cambia esta selección.')
support_type = st.radio('Apoyos',['Articulados','Empotrados'],horizontal=True)
st.caption('Articulados: restringen Ux, Uy, Uz. Empotrados: también restringen los giros; en una armadura axial los giros no forman parte del modelo.')
confirmed = st.checkbox('He revisado las unidades, conectividad y nodos de apoyo.',key='confirm_'+geometry_key)
signature = repr((geometry_key,material_name,profile_name,connections,tuple(support_nodes),support_type))
if st.button('Analizar peso propio',type='primary',disabled=not confirmed or not support_nodes):
    with st.spinner('Calculando…'):
        try:
            result = run_analysis(inspection,material_name,profile_name,connections,support_nodes,support_type)
            st.session_state['analysis'] = (signature,result)
        except (ValueError,KeyError) as exc:
            st.error(str(exc)); st.stop()
previous = st.session_state.get('analysis')
if previous and previous[0]!=signature:
    st.info('La configuración cambió. Ejecuta el análisis para actualizar los resultados.')
elif previous:
    result = previous[1]
    if not result['stable']:
        st.error('No se obtuvo una solución estable: '+result['message'])
    else:
        st.subheader('Resultados')
        st.write(f'Masa: {result["summary"]["mass_kg"]:.2f} kg · desplazamiento máximo: {result["summary"]["max_displacement_m"]*1000:.3f} mm')
        viewer,archive = outputs(result)
        components.html(viewer,height=880,scrolling=True)
        st.download_button('Descargar visor HTML',viewer,'visor.html','text/html')
        st.download_button('Descargar reporte y resultados ZIP',archive,'analisis.zip','application/zip')
st.caption('No incluye resistencia normativa, pandeo, segundo orden ni análisis de construcción por etapas.')
