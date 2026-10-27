"""DXF straight-line geometry import, stage assignment and base restraints."""
from __future__ import annotations
from collections import defaultdict
from itertools import product
from typing import Tuple
import math
import ezdxf
import numpy as np
import pandas as pd
from .schema import NODES_COLS, BARS_COLS, SUPPORTS_COLS


def read_dxf(path: str, unit_scale: float = 1.0, tol: float = 1e-3,
             layers: Tuple[str, ...] = ()) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read LINE and straight POLYLINE/LWPOLYLINE segments.

    Coordinates are multiplied by explicit unit_scale (default: meters).
    Curves, polygon meshes, blocks, duplicates and disconnected components are
    rejected instead of silently dropping geometry. Layer filtering is explicit.
    """
    if not math.isfinite(unit_scale) or unit_scale <= 0 or not math.isfinite(tol) or tol <= 0:
        raise ValueError('unit_scale and tol must be positive and finite')
    document = ezdxf.readfile(path)
    points, bars, edges = [], [], set()
    buckets = defaultdict(list)
    neighbors = list(product((-1, 0, 1), repeat=3))
    def node(point):
        point = np.array(point, dtype=float) * unit_scale
        if not np.isfinite(point).all():
            raise ValueError('DXF coordinates must be finite')
        cell = tuple(np.floor(point / tol).astype(np.int64))
        candidates = []
        for offset in neighbors:
            candidates.extend(buckets[tuple(cell[i]+offset[i] for i in range(3))])
        for index in sorted(candidates):
            if np.linalg.norm(points[index] - point) <= tol:
                return index + 1
        index = len(points)
        points.append(point)
        buckets[cell].append(index)
        return index + 1
    for entity in document.modelspace():
        if layers and entity.dxf.layer not in layers:
            continue
        kind = entity.dxftype()
        if kind == 'LINE':
            vertices, closed = [entity.dxf.start, entity.dxf.end], False
        elif kind == 'LWPOLYLINE':
            if entity.has_arc:
                raise ValueError('Curved polylines are unsupported; provide straight segments')
            vertices, closed = list(entity.vertices_in_wcs()), entity.closed
        elif kind == 'POLYLINE':
            if (entity.is_polygon_mesh or entity.is_poly_face_mesh or entity.dxf.flags & 6
                    or any(v.dxf.get('bulge', 0) for v in entity.vertices)):
                raise ValueError('Meshes and curved polylines are unsupported')
            vertices, closed = list(entity.points_in_wcs()), entity.is_closed
        else:
            raise ValueError(f'Unsupported DXF entity: {kind}; select wireframe layers or convert to lines')
        pairs = list(zip(vertices, vertices[1:]))
        if closed and vertices:
            pairs.append((vertices[-1], vertices[0]))
        for start, end in pairs:
            i, j = node(start), node(end)
            if i == j:
                raise ValueError('Zero-length segment after merging endpoints')
            edge = tuple(sorted((i, j)))
            if edge in edges:
                raise ValueError(f'Duplicate bar between nodes {edge}')
            edges.add(edge)
            bars.append((len(bars)+1, i, j, 'DEFAULT', 0))
    if not bars:
        raise ValueError('No wireframe segments found in selected layers')
    adjacency = defaultdict(set)
    for _, i, j, _, _ in bars:
        adjacency[i].add(j)
        adjacency[j].add(i)
    seen, pending = set(), [1]
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(adjacency[current] - seen)
    if len(seen) != len(points):
        raise ValueError('Disconnected geometry: import one connected structure at a time')
    return (pd.DataFrame([(i+1, *p) for i, p in enumerate(points)], columns=NODES_COLS),
            pd.DataFrame(bars, columns=BARS_COLS))


def assign_stages_by_height(nodes: pd.DataFrame, bars: pd.DataFrame, ring_height: float) -> pd.DataFrame:
    if not math.isfinite(ring_height) or ring_height <= 0:
        raise ValueError('ring_height must be positive and finite')
    result = bars.copy()
    if bars.empty:
        return result
    heights = nodes.set_index('node_id').z
    a, b = bars.node_i.map(heights), bars.node_j.map(heights)
    if a.isna().any() or b.isna().any():
        raise ValueError('Bars reference unknown nodes')
    means = (a + b) / 2
    if not np.isfinite(means.to_numpy()).all():
        raise ValueError('Node heights must be finite')
    result['stage'] = np.floor((means - means.min()) / ring_height + 1e-10).astype(int)
    return result


def detect_base_supports(nodes: pd.DataFrame, z_tol: float = 1e-3) -> pd.DataFrame:
    if nodes.empty or not np.isfinite(nodes.z.to_numpy(dtype=float)).all():
        raise ValueError('Require nonempty nodes with finite heights')
    if not math.isfinite(z_tol) or z_tol < 0:
        raise ValueError('z_tol must be nonnegative and finite')
    ids = nodes.loc[nodes.z <= nodes.z.min() + z_tol, 'node_id']
    return pd.DataFrame([(i, True, True, True) for i in ids], columns=SUPPORTS_COLS)
