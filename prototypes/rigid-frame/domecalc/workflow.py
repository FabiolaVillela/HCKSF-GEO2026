"""Configuración común para la interfaz e integraciones futuras."""
from dataclasses import asdict
from copy import deepcopy
import numpy as np
from .catalog import properties
from .core import analyze
from .truss import analyze_truss


def run_analysis(inspection, material_name, profile_name, connections, support_nodes, support_type='Articulados'):
    if not inspection.ready:
        return {'stable': False, 'message': 'Corregir la geometría antes de analizar.', 'errors': inspection.report['errors']}
    if connections not in ('Articuladas', 'Empotradas'):
        raise ValueError('Selecciona conexiones articuladas o empotradas.')
    if support_type not in ('Articulados', 'Empotrados'):
        raise ValueError('Tipo de apoyo desconocido.')
    model = deepcopy(inspection.model)
    if not support_nodes or any(i not in range(len(model.nodes)) for i in support_nodes):
        raise ValueError('Selecciona al menos un nodo de apoyo válido.')
    if len(model.nodes)>500:
        raise ValueError('Esta versión de matrices densas admite hasta 500 nodos por análisis.')
    material, section = properties(material_name, profile_name)
    axes = tuple(range(6)) if support_type=='Empotrados' else (0,1,2)
    model.supports = {i:axes for i in support_nodes}
    try:
        result = (analyze if connections=='Empotradas' else analyze_truss)(model,material,section)
    except (ValueError, np.linalg.LinAlgError) as exc:
        return {'stable': False, 'message': str(exc)}
    result['stable'] = True
    result['configuration'] = dict(material=material_name,profile=profile_name,connections=connections,
                                   support_type=support_type,support_nodes=list(support_nodes),
                                   material_properties=asdict(material),section_properties=asdict(section),
                                   import_report=inspection.report,
                                   self_weight_model='distributed_consistent' if connections=='Empotradas' else 'lumped_at_nodes')
    return result
