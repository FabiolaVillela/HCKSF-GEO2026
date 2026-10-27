"""Adaptador de montaje al motor de pórticos/armaduras, sin cambiar schema.py.

Se resuelve un equilibrio independiente por etapa. Unidades SI, tensión positiva.
"""
from __future__ import annotations

from functools import lru_cache
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import numpy as np

PROTOTYPE = Path(__file__).resolve().parents[2] / 'prototypes' / 'rigid-frame'
if str(PROTOTYPE) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE))
from domecalc.catalog import MATERIALS, HSS, properties
from domecalc.core import Model, analyze
from domecalc.truss import analyze_truss
from domecalc.importer import inspect_dxf
from .validity import chord_rotations, rotation_problem

G = 9.80665
MAX_NODES = 500


def finite(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name}: se requiere un número.') from exc
    if not math.isfinite(result):
        raise ValueError(f'{name}: número no finito.')
    return result


def identifier(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name}: identificador entero requerido.')
    return value


def validate_geometry(geometry):
    if not isinstance(geometry, dict):
        raise ValueError('Modelo geométrico inválido.')
    raw_nodes, raw_bars = geometry.get('nodes', []), geometry.get('bars', [])
    if not isinstance(raw_nodes, list) or not isinstance(raw_bars, list) or not 1 <= len(raw_nodes) <= MAX_NODES:
        raise ValueError(f'Se requieren entre 1 y {MAX_NODES} nodos.')
    if len(raw_bars) > 5000:
        raise ValueError('Esta versión admite hasta 5000 barras.')
    nodes = {}; bars = []; seen = set(); edges = set()
    for n in raw_nodes:
        if not isinstance(n, dict): raise ValueError('Nodo inválido.')
        nid = identifier(n.get('id'), 'Nodo')
        if nid in nodes: raise ValueError('Identificador de nodo duplicado.')
        nodes[nid] = [finite(n.get(a), a) for a in ('x', 'y', 'z')]
    supports = geometry.get('support_nodes', [])
    if not isinstance(supports, list) or not supports:
        raise ValueError('Se requiere al menos un nodo de apoyo.')
    for n in supports:
        identifier(n, 'Apoyo')
        if n not in nodes: raise ValueError('Apoyo en nodo inexistente.')
    for b in raw_bars:
        if not isinstance(b, dict): raise ValueError('Barra inválida.')
        bid = identifier(b.get('id'), 'Barra')
        i, j = identifier(b.get('i'), 'Nodo i'), identifier(b.get('j'), 'Nodo j')
        if bid in seen: raise ValueError('Identificador de barra duplicado.')
        if i not in nodes or j not in nodes: raise ValueError('Barra conectada a nodo inexistente.')
        if math.dist(nodes[i], nodes[j]) <= 1e-9: raise ValueError('Barra de longitud nula.')
        edge = tuple(sorted((i, j)))
        if edge in edges: raise ValueError('Barras geométricamente duplicadas.')
        seen.add(bid); edges.add(edge)
        order = finite(b.get('order', b.get('stage', bid)), 'Orden de montaje')
        base = bool(b.get('isBase', b.get('stage') == 0))
        bars.append(dict(id=bid, i=i, j=j, order=order, isBase=base))
    if not bars: raise ValueError('El modelo no contiene barras.')
    return nodes, bars, sorted(set(supports))


def stage_plan(geometry, bars_per_step=2):
    nodes, bars, supports = validate_geometry(geometry)
    try:
        step = int(bars_per_step)
    except (TypeError, ValueError):
        raise ValueError('Paso de barras inválido.')
    if step <= 0:
        raise ValueError('bars_per_step debe ser mayor que cero.')
    step = min(100, step)
    base = [b for b in bars if b['isBase']]
    others = sorted([b for b in bars if not b['isBase']], key=lambda b: (b['order'], b['id']))
    total = len(bars)
    stages = []
    base_ids = [b['id'] for b in base]
    stages.append(dict(stage=0, active_count=len(base_ids), total_bars=total,
                       progress_pct=round(len(base_ids) / total * 100, 1),
                       new_bar_ids=base_ids, active_bar_ids=list(base_ids)))
    accumulated = list(base_ids)
    for i in range(0, len(others), step):
        batch = [b['id'] for b in others[i:i + step]]
        accumulated.extend(batch)
        stages.append(dict(stage=len(stages), active_count=len(accumulated), total_bars=total,
                           progress_pct=round(len(accumulated) / total * 100, 1),
                           new_bar_ids=batch, active_bar_ids=list(accumulated)))
    return stages


def catalog():
    return dict(materials=list(MATERIALS), profiles=list(HSS),
                connections=['articulada', 'empotrada'], supports=['articulado', 'empotrado'])


def geometry_from_structure(model):
    nodes = [dict(id=int(r.node_id), x=float(r.x), y=float(r.y), z=float(r.z))
             for _, r in model.nodes.iterrows()]
    base = set(int(r.node_id) for _, r in model.supports.iterrows())
    bars = [dict(id=int(r.bar_id), i=int(r.node_i), j=int(r.node_j),
                 isBase=int(r.stage) == 0, order=float(r.stage))
            for _, r in model.bars.iterrows()]
    geometry = dict(nodes=nodes, bars=bars, support_nodes=sorted(base))
    validate_geometry(geometry)
    return geometry


def geometry_from_dxf(content, units=None, tolerance=0.001):
    inspection = inspect_dxf(content, units or 'auto', tolerance, ())
    if inspection.report['errors']:
        raise ValueError('; '.join(inspection.report['errors']))
    model = inspection.model
    zmin = min(p[2] for p in model.nodes)
    supports = [i for i, p in enumerate(model.nodes) if abs(p[2] - zmin) <= tolerance]
    base = set(supports)
    geometry = dict(nodes=[dict(id=i, x=p[0], y=p[1], z=p[2]) for i, p in enumerate(model.nodes)],
                   bars=[dict(id=bid, i=i, j=j, isBase=i in base and j in base,
                              order=(model.nodes[i][2] + model.nodes[j][2]) / 2)
                         for bid, (i, j, _) in enumerate(model.elements)], support_nodes=supports)
    validate_geometry(geometry)
    return geometry, inspection.report


def solve_stage(geometry, config=None, stage=0):
    config = dict(config or {})
    payload = json.dumps(dict(geometry=geometry, config=config, stage=stage), sort_keys=True, allow_nan=False)
    return json.loads(_cached_stage(payload))


def progress_series(geometry, config=None):
    """Máximos por etapa frente al % de avance, para las gráficas de resultados.

    Las etapas sin solución (mecanismo o error) se devuelven con valores None:
    no se inventan fuerzas ni desplazamientos.
    """
    config=dict(config or {})
    plan=stage_plan(geometry,config.get('bars_per_step',2))
    series=[]
    for info in plan:
        r=solve_stage(geometry,config,info['stage'])
        stable=r['status']=='stable'
        tension=r['max_tension_kn'] if stable else None
        compression=r['max_compression_kn'] if stable else None
        series.append(dict(stage=info['stage'],progress_pct=info['progress_pct'],active_count=info['active_count'],
                           status=r['status'],max_tension_kn=tension,max_compression_kn=compression,
                           max_force_kn=max(tension,compression) if stable else None,
                           max_displacement_mm=r['max_displacement_mm'] if stable else None))
    return series


@lru_cache(maxsize=32)
def _cached_stage(payload):
    p = json.loads(payload)
    return json.dumps(_solve(p['geometry'], p['config'], p['stage']), allow_nan=False)


def _solve(geometry, config, stage):
    nodes, bars, support_nodes = validate_geometry(geometry)
    plan = stage_plan(geometry, config.get('bars_per_step', 2))
    if isinstance(stage, bool) or not isinstance(stage, int) or stage not in range(len(plan)):
        raise ValueError('Etapa fuera de rango.')
    material_name = config.get('material', 'Acero')
    profile_name = config.get('profile', list(HSS)[2])
    if material_name not in MATERIALS or profile_name not in HSS:
        raise ValueError('Material o perfil no disponible en el catálogo.')
    connection = config.get('connection', 'empotrada')
    support = config.get('support', 'empotrado')
    if connection not in ('articulada', 'empotrada') or support not in ('articulado', 'empotrado'):
        raise ValueError('Tipo de conexión o apoyo inválido.')

    # Worker mass validation (kept for test compatibility, but default 0 in UI)
    worker_kg = finite(config.get('worker_kg', 0), 'Masa de instalador')
    if not 0 <= worker_kg <= 10000:
        raise ValueError('Masa de instalador fuera de rango (0–10000 kg).')

    support_overrides = config.get('support_overrides', {})

    material, section = properties(material_name, profile_name)
    info = plan[stage]
    by_id = {b['id']: b for b in bars}
    active = [by_id[bid] for bid in info['active_bar_ids']]
    mass = sum(math.dist(nodes[b['i']], nodes[b['j']]) for b in active) * material.density * section.A
    worker_node = by_id[info['new_bar_ids'][-1]]['j'] if stage > 0 and info['new_bar_ids'] and worker_kg else None

    result = dict(**info, stable=None, status='empty', message='No hay barras instaladas en esta etapa.',
                 forces={}, reactions=[], displacements=[], elements=[], max_tension_kn=None, max_compression_kn=None,
                 max_displacement_mm=None, mass_kg=mass, worker_node=worker_node,
                 worker_load_N=worker_kg * G if worker_node is not None else 0,
                 material=material_name, profile=profile_name, connection=connection, support=support)
    if not active: return result
    active_nodes = sorted({n for b in active for n in (b['i'], b['j'])})
    mapping = {nid: i for i, nid in enumerate(active_nodes)}

    support_conditions = {}
    for n in support_nodes:
        if n in mapping:
            stype = support_overrides.get(str(n), support_overrides.get(n, support))
            axes = tuple(range(6)) if stype == 'empotrado' else (0, 1, 2)
            support_conditions[mapping[n]] = axes

    model = Model([nodes[n] for n in active_nodes],
                  [(mapping[b['i']], mapping[b['j']], 'montaje') for b in active],
                  support_conditions)

    loads = {mapping[worker_node]: [0, 0, -worker_kg * G, 0, 0, 0]} if worker_node is not None else {}
    solver = analyze if connection == 'empotrada' else analyze_truss
    try:
        solved = solver(model, material, section, nodal_loads=loads)
    except (ValueError, np.linalg.LinAlgError) as exc:
        message = str(exc)
        unstable = isinstance(exc, np.linalg.LinAlgError) or any(w in message.lower() for w in ('inestable', 'condicionado', 'singular', 'unstable', 'mechanism'))
        result.update(stable=False if unstable else None, status='unstable' if unstable else 'error', message=message)
        return result
    shift = {active_nodes[node['id']]: node['displacement'][:3] for node in solved['nodes']}
    rotations = chord_rotations([nodes[b['i']] for b in active], [nodes[b['j']] for b in active],
                                [shift[b['i']] for b in active], [shift[b['j']] for b in active])
    worst = int(np.argmax(rotations))
    problem = rotation_problem(active[worst]['id'], float(rotations[worst]))
    if problem:
        # Shallow near-mechanism: report it as unsolved, like a mechanism, with no values.
        result.update(stable=False, status='unstable', message=problem)
        return result
    solution = deepcopy(solved)
    for node in solution['nodes']: node['source_id'] = active_nodes[node['id']]
    for b, e in zip(active, solution['elements']): e['source_id'] = b['id']
    solution['configuration'] = dict(material=material_name, profile=profile_name, connections='Empotradas' if connection == 'empotrada' else 'Articuladas')
    forces = {}; elements = []
    for b, e in zip(active, solved['elements']):
        e['id'] = b['id']; e['i'] = b['i']; e['j'] = b['j']
        forces[b['id']] = e['stations'][len(e['stations']) // 2]['N_Vy_Vz_T_My_Mz'][0]
        elements.append(e)
    reactions = []; displacements = []
    for node in solved['nodes']:
        original = active_nodes[node['id']]
        displacements.append(dict(node_id=original, values=node['displacement']))
        if original in support_nodes:
            reactions.append(dict(node_id=original, values=node['reaction']))
    result['solution'] = solution
    result.update(stable=True, status='stable', message='Equilibrio elástico lineal calculado.', forces=forces,
                  reactions=reactions, displacements=displacements, elements=elements,
                  max_tension_kn=max(0, max(s["N_Vy_Vz_T_My_Mz"][0] for e in elements for s in e["stations"])) / 1000,
                  max_compression_kn=max(0, -min(s["N_Vy_Vz_T_My_Mz"][0] for e in elements for s in e["stations"])) / 1000,
                  max_displacement_mm=solved['summary']['max_displacement_m'] * 1000,
                  balance_force_N=solved['summary']['balance_force_N'],
                  balance_moment_Nm=solved['summary']['balance_moment_Nm'])
    return result
