"""Optional Streamlit design controls, independent from physical config/caches."""
import json
import streamlit as st
from .design_materials import material_catalog
from .aisc import check_result,check_all_stages,LIMITATIONS


def select_design(material):
    catalog=[g for g in material_catalog() if g['material']==material]
    options=['Seleccionar grado…',*[g['id'] for g in catalog],'custom']
    labels={g['id']:g['label'] for g in catalog}
    grade=st.selectbox('Norma / grado / temple',options,format_func=lambda x:labels.get(x,'Personalizado' if x=='custom' else x),key='design_grade')
    if grade=='Seleccionar grado…':return None
    if grade=='custom':
        fy=st.number_input('Fy (MPa)',min_value=0.,value=None,key='design_fy')
        fu=st.number_input('Fu (MPa)',min_value=0.,value=None,key='design_fu')
        source=st.text_input('Fuente / certificado',key='design_source')
        return dict(grade=grade,Fy_MPa=fy,Fu_MPa=fu,source=source)
    selected=next(g for g in catalog if g['id']==grade)
    st.caption(f'Fy = {selected["Fy_MPa"]:g} MPa · Fu = {selected["Fu_MPa"]:g} MPa')
    st.markdown(f'[Fuente de propiedades]({selected["source"]})')
    if material=='Aluminio':st.caption('Material extruido sin afectación por soldadura; requiere norma de diseño de aluminio.')
    return dict(grade=grade)


def render_design(result,geometry,config,design):
    show=st.checkbox('Mostrar utilización AISC (preliminar)',value=False,key='show_aisc')
    if not show:return None
    st.warning('ANSI/AISC 360-22 LRFD · 1.4D · t=0.93t · K=1 · L entre nodos · An=Ag · U=1. Solo primer orden: no constituye verificación integral de estabilidad ni aprobación de diseño.')
    if design is None:st.info('Selecciona un grado de material.');return None
    try:r=check_result(result,design)
    except ValueError as exc:st.error(str(exc));return None
    if r['max_utilization'] is not None:
        g=r['governing'];st.metric('Utilización máxima AISC de la etapa',f'{r["max_utilization"]:.3f}')
        st.write(f'Etapa {r["stage"]} · Barra {g["member_id"]} · {g["equation"]} · x={g["x_m"]:.4f} m')
    else:st.info(r['message'])
    st.caption('Verde ≤1: dentro de revisiones incluidas; rojo >1: excede; gris: no disponible. Las fuerzas originales conservan sus valores.')
    with st.expander('Resultados AISC y limitaciones'):
        st.code(json.dumps(r,ensure_ascii=False,indent=2),language='json')
        st.download_button('Descargar reporte AISC',json.dumps(dict(report=r,original_stage=result),ensure_ascii=False,indent=2),f'aisc-etapa-{r["stage"]}.json','application/json')
        if st.button('Verificar todas las etapas AISC'):
            try:
                with st.spinner('Verificando etapas…'):series=check_all_stages(geometry,config,design)
                st.code(json.dumps([dict(stage=s['stage'],status=s['status'],max_utilization=s['max_utilization'],governing=s['governing']) for s in series],ensure_ascii=False,indent=2),language='json')
            except ValueError as exc:st.error(str(exc))
    return {m['id']:m['utilization'] for m in r['members']}
