"""Coordenadas de deformada nodal para visualización; nunca altera el análisis."""
import math

MAX_FACTOR=100000.


def nodal_positions(nodes, displacements, factor=10.):
    """nodes/displacements: dict id -> [x,y,z,...], todo en metros.

    Une nodos desplazados con barras rectas; no interpola flexión dentro de barras.
    """
    if not math.isfinite(factor) or not 0<=factor<=MAX_FACTOR:
        raise ValueError('El factor visual debe estar entre 0 y 100000.')
    points={}
    for node_id,values in displacements.items():
        if node_id not in nodes or len(values)<3:
            raise ValueError('Desplazamiento sin nodo válido.')
        p=nodes[node_id]
        if len(p)<3 or not all(math.isfinite(x) for x in [*p[:3],*values[:3]]):
            raise ValueError('Coordenadas o desplazamientos no finitos.')
        points[node_id]=[p[i]+factor*values[i] for i in range(3)]
        if not all(math.isfinite(x) for x in points[node_id]):
            raise ValueError('La deformada amplificada excede el rango numérico.')
    return points
