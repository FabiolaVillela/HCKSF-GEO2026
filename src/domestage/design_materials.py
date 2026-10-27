"""Strength catalog, separate from the existing elastic-analysis catalog (SI)."""
from copy import deepcopy
import math

STI='https://steeltubeinstitute.org/wp-content/uploads/2022/08/STI_Webinar_Dos_and_Donts_HSS_1Slide.pdf'
HYDRO='https://www.hydro.com/globalassets/01-products--services/extruded-profiles/americas/ena-resources/alloy-data-sheets/hydro_2019_data_sheet_6061.pdf'
GRADES={
 'a500-21-b':dict(material='Acero',label='ASTM A500/A500M-21 Grade B',Fy_MPa=315.,Fu_MPa=400.,source=STI),
 'a500-21-c':dict(material='Acero',label='ASTM A500/A500M-21 Grade C',Fy_MPa=345.,Fu_MPa=425.,source=STI),
 '6061-t4':dict(material='Aluminio',label='6061-T4 extruded / Hydro 2019',Fy_MPa=110.,Fu_MPa=180.,source=HYDRO),
 '6061-t6':dict(material='Aluminio',label='6061-T6 extruded / Hydro 2019',Fy_MPa=240.,Fu_MPa=260.,source=HYDRO),
}

def material_catalog():
    return [dict(id=key,**deepcopy(value)) for key,value in GRADES.items()]


def design_material(material,design):
    grade=design.get('grade')
    if grade=='custom':
        values={}
        for name in ('Fy_MPa','Fu_MPa'):
            v=design.get(name)
            if isinstance(v,bool):raise ValueError('Strengths must be finite positive MPa values.')
            try:v=float(v)
            except (TypeError,ValueError):raise ValueError('Fy and Fu are required in MPa.')
            if not math.isfinite(v) or v<=0:raise ValueError('Strengths must be finite positive MPa values.')
            values[name]=v
        source=design.get('source','')
        if not isinstance(source,str) or not source.strip():raise ValueError('Custom material requires a source/certificate reference.')
        result=dict(material=material,label='Custom',source=source.strip()[:1000],**values)
    else:
        if grade not in GRADES:raise ValueError('Select a material grade before checking resistance.')
        result=deepcopy(GRADES[grade])
        if result['material']!=material:raise ValueError('Grade does not match the selected material.')
    if material not in ('Acero','Aluminio'):raise ValueError('Unsupported material.')
    if result['Fu_MPa']<result['Fy_MPa']:raise ValueError('Fu must be greater than or equal to Fy.')
    return dict(id=grade,**result)
