"""Importación general de entramados DXF y diagnóstico antes del análisis."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product
import math
from pathlib import Path
import tempfile

import ezdxf
import numpy as np
from .core import Model

UNITS = {'mm': .001, 'cm': .01, 'm': 1., 'in': .0254, 'ft': .3048}
DXF_UNITS = {1: 'in', 2: 'ft', 4: 'mm', 5: 'cm', 6: 'm'}
ANNOTATIONS = {'TEXT', 'MTEXT', 'DIMENSION', 'ATTRIB', 'ATTDEF', 'POINT', 'LEADER', 'MLEADER'}

@dataclass
class Inspection:
    model: Model
    report: dict

    @property
    def ready(self):
        return not self.report['errors']


def read_document(content):
    if not content or len(content) > 20 * 1024 * 1024:
        raise ValueError('El DXF está vacío o supera el límite de 20 MB.')
    # readfile detecta formato binario y codificación de DXF antiguos.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'upload.dxf'
        path.write_bytes(content)
        try:
            return ezdxf.readfile(path)
        except (ezdxf.DXFError, OSError, UnicodeError, ValueError) as exc:
            raise ValueError(f'No se pudo leer el DXF: {exc}') from exc


def declared_units(content):
    return DXF_UNITS.get(read_document(content).units)


def inspect_dxf(content, units=None, tolerance=1e-6, layers=None):
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('La tolerancia debe ser finita y positiva, en metros.')
    doc = read_document(content)
    detected = DXF_UNITS.get(doc.units)
    units = units or detected
    if units not in UNITS:
        raise ValueError('Selecciona las unidades; el DXF no declara unidades compatibles.')
    scale = UNITS[units]
    counts, ignored, unsupported = Counter(), Counter(), Counter()
    raw, errors = [], []
    selected_layers = set(layers or [])
    skipped_layers = Counter()
    def visit(entity, parent_layer='0', depth=0):
        if depth > 16:
            errors.append('Bloques anidados más de 16 niveles o referencia circular.'); return
        kind = entity.dxftype()
        layer = entity.dxf.get('layer', '0')
        if layer == '0': layer = parent_layer
        counts[kind] += 1
        if kind == 'INSERT':
            if entity.block() is None or entity.block().block.dxf.flags & 12:
                if selected_layers and layer not in selected_layers:
                    skipped_layers[layer] += 1; return
                errors.append(f'Bloque externo o ausente: {entity.dxf.name}.'); return
            def skipped(e, reason):
                errors.append(f'Entidad de bloque no transformable: {e.dxftype()} ({reason}).')
            inserts = entity.multi_insert() if entity.mcount > 1 else [entity]
            for insert in inserts:
                for child in insert.virtual_entities(skipped_entity_callback=skipped):
                    visit(child, layer, depth+1)
            return
        if selected_layers and layer not in selected_layers:
            skipped_layers[layer] += 1; return
        if kind == 'LINE':
            raw.append((np.array(entity.dxf.start)*scale, np.array(entity.dxf.end)*scale, layer))
        elif kind in ('LWPOLYLINE', 'POLYLINE'):
            if kind == 'POLYLINE' and (entity.is_polygon_mesh or entity.is_poly_face_mesh):
                unsupported[kind+' (malla)'] += 1; return
            if entity.has_arc:
                unsupported[kind+' (curva)'] += 1; return
            children = list(entity.virtual_entities())
            if not children:
                errors.append(f'Polilínea vacía o sin segmentos en capa {layer}.')
            for child in children: visit(child, layer, depth+1)
        elif kind in ANNOTATIONS:
            ignored[kind] += 1
        else:
            unsupported[kind] += 1
    try:
        for entity in doc.modelspace(): visit(entity)
    except (ezdxf.DXFError, ValueError, TypeError, AttributeError, RecursionError) as exc:
        raise ValueError(f'No se pudo convertir la geometría DXF: {exc}') from exc
    nodes, elements, cells = [], [], defaultdict(list)
    merged = duplicates = zero = 0
    seen = set()
    offsets = list(product((-1,0,1), repeat=3))
    def node(p):
        nonlocal merged
        cell = tuple(math.floor(v/tolerance) for v in p)
        for offset in offsets:
            for i in cells.get(tuple(a+b for a,b in zip(cell,offset)), ()):
                if np.linalg.norm(np.array(nodes[i])-p) <= tolerance:
                    merged += 1; return i
        i = len(nodes); nodes.append(p.tolist()); cells[cell].append(i); return i
    for p,q,layer in raw:
        if not np.isfinite([p,q]).all():
            errors.append('Coordenadas no finitas.'); continue
        if np.linalg.norm(q-p) <= tolerance:
            zero += 1; continue
        i,j = node(p),node(q)
        if i == j:
            zero += 1; continue
        key = tuple(sorted((i,j)))
        if key in seen:
            duplicates += 1; continue
        seen.add(key); elements.append((i,j,layer))
    # Quitar cualquier nodo huérfano generado por una línea que colapsó al agrupar.
    used = sorted({n for i,j,_ in elements for n in (i,j)})
    remap = {old:new for new,old in enumerate(used)}
    nodes = [nodes[i] for i in used]
    elements = [(remap[i],remap[j],layer) for i,j,layer in elements]
    adjacency = [set() for _ in nodes]
    for i,j,_ in elements: adjacency[i].add(j); adjacency[j].add(i)
    unseen = set(range(len(nodes))); components = []
    while unseen:
        start = unseen.pop(); stack = [start]; group = [start]
        while stack:
            u = stack.pop()
            for v in adjacency[u] & unseen:
                unseen.remove(v); stack.append(v); group.append(v)
        components.append(sorted(group))
    if not elements: errors.append('No se encontraron barras rectas utilizables en el espacio modelo.')
    if duplicates: errors.append(f'{duplicates} barras duplicadas: eliminarlas del DXF antes de analizar.')
    if zero: errors.append(f'{zero} barras nulas o menores que la tolerancia: corregir el DXF.')
    if len(components)>1: errors.append(f'Geometría desconectada: {len(components)} componentes independientes.')
    if unsupported: errors.append('Entidades geométricas no compatibles: '+str(dict(unsupported))+'. Convertir a líneas rectas o filtrar capas.')
    warnings = ['Los cruces interiores no crean nodos; dividir las barras en CAD si deben conectarse.']
    if ignored: warnings.append('Anotaciones omitidas: '+str(dict(ignored)))
    leaves = [i for i,a in enumerate(adjacency) if len(a)==1]
    if leaves: warnings.append(f'{len(leaves)} nodos con una sola barra; revisar extremos libres.')
    bounds = [[min(p[i] for p in nodes),max(p[i] for p in nodes)] for i in range(3)] if nodes else []
    report = dict(units=units, declared_units=detected, tolerance_m=tolerance, nodes=len(nodes), elements=len(elements),
                  layers=dict(Counter(e[2] for e in elements)), entities=dict(counts), ignored=dict(ignored),
                  excluded_layers=dict(skipped_layers), unsupported=dict(unsupported), merged_endpoints=merged,
                  duplicate_bars=duplicates, zero_bars=zero, components=components, leaf_nodes=leaves,
                  bounds_m=bounds, errors=list(dict.fromkeys(errors)), warnings=warnings)
    return Inspection(Model(nodes,elements),report)
