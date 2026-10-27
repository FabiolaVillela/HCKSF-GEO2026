"""Linear 3D pin-jointed truss analysis; SI units, tension positive."""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.linalg import eigvalsh
from scipy.sparse.linalg import ArpackNoConvergence, eigsh, spsolve

from .schema import G, SolveResult, StructureModel, validate_model


def solve_truss(model: StructureModel, active_bar_ids: Iterable[int],
                extra_loads: Optional[pd.DataFrame] = None,
                include_self_weight: bool = True) -> SolveResult:
    problems = validate_model(model)
    if problems:
        raise ValueError('; '.join(problems))
    ids = list(active_bar_ids)
    if len(set(ids)) != len(ids) or not set(ids) <= set(model.bars.bar_id):
        raise ValueError('Active bar IDs must be unique and present in the model')
    bars = model.bars.set_index('bar_id').loc[ids]
    node_ids = sorted(set(bars.node_i) | set(bars.node_j))
    nodes = model.nodes.set_index('node_id').loc[node_ids]
    lookup = {node: i for i, node in enumerate(node_ids)}
    n = len(nodes)

    def unavailable(message):
        return SolveResult(False, message, pd.Series(np.nan, index=ids, dtype=float),
                           pd.Series(np.nan, index=ids, dtype=float),
                           pd.DataFrame({'node_id': node_ids, 'ux': np.nan, 'uy': np.nan, 'uz': np.nan}),
                           pd.DataFrame({'node_id': node_ids, 'rx': np.nan, 'ry': np.nan, 'rz': np.nan}),
                           pd.Series(np.nan, index=ids, dtype=float))

    if not n:
        return unavailable('No active bars')
    rows, cols, values, elements = [], [], [], []
    force = np.zeros(3 * n)
    profiles = model.profiles.set_index('profile')
    xyz = nodes[['x', 'y', 'z']].to_numpy(dtype=float)
    for bar in bars.itertuples():
        i, j = lookup[bar.node_i], lookup[bar.node_j]
        delta = xyz[j] - xyz[i]
        length = np.linalg.norm(delta)
        if length <= 0:
            raise ValueError(f'Bar {bar.Index} has zero length')
        c = delta / length
        p = profiles.loc[bar.profile]
        dofs = np.r_[np.arange(3*i, 3*i+3), np.arange(3*j, 3*j+3)]
        direction = np.r_[-c, c]
        stiffness = p.E_pa * p.area_m2 / length
        ke = stiffness * np.outer(direction, direction)
        rows.extend(np.repeat(dofs, 6))
        cols.extend(np.tile(dofs, 6))
        values.extend(ke.ravel())
        if include_self_weight:
            weight = p.density_kgm3 * p.area_m2 * length * G
            force[3*i+2] -= weight / 2
            force[3*j+2] -= weight / 2
        elements.append((dofs, direction, stiffness, length, p))
    if extra_loads is not None:
        required = ['node_id', 'fx_n', 'fy_n', 'fz_n']
        if not set(required) <= set(extra_loads.columns):
            raise ValueError('Loads require node_id, fx_n, fy_n, fz_n')
        if not np.isfinite(extra_loads[required[1:]].to_numpy(dtype=float)).all():
            raise ValueError('Loads must be finite')
        for load in extra_loads.itertuples():
            if load.node_id not in set(model.nodes.node_id):
                raise ValueError('Load references an unknown node')
            vector = np.array([load.fx_n, load.fy_n, load.fz_n], dtype=float)
            if load.node_id not in lookup:
                if np.any(vector):
                    return unavailable(f'Load applied to inactive node {load.node_id}')
                continue
            k = 3 * lookup[load.node_id]
            force[k:k+3] += vector
    matrix = sparse.coo_matrix((values, (rows, cols)), shape=(3*n, 3*n)).tocsc()
    fixed = np.zeros(3*n, dtype=bool)
    for support in model.supports.itertuples():
        if support.node_id in lookup:
            i = 3 * lookup[support.node_id]
            fixed[i:i+3] |= np.array([support.fix_x, support.fix_y, support.fix_z], dtype=bool)
    free = np.flatnonzero(~fixed)
    displacement = np.zeros(3*n)
    if len(free):
        reduced = matrix[free][:, free]
        diagonal = reduced.diagonal()
        if np.any(diagonal <= 0):
            return unavailable('Mechanism: an active degree of freedom has no stiffness')
        scaling = sparse.diags(1 / np.sqrt(diagonal))
        normalized = (scaling @ reduced @ scaling).tocsc()
        try:
            if len(free) <= 300:
                spectrum = eigvalsh(normalized.toarray())
                low, high = spectrum[0], spectrum[-1]
            else:
                low = eigsh(normalized, k=1, which='SA', return_eigenvectors=False)[0]
                high = eigsh(normalized, k=1, which='LA', return_eigenvectors=False)[0]
            if low <= high * 1e-12:
                return unavailable('Mechanism or ill-conditioned stiffness matrix')
            scaled_load = scaling @ force[free]
            displacement[free] = scaling @ spsolve(normalized, scaled_load)
        except (ArpackNoConvergence, np.linalg.LinAlgError, RuntimeError) as error:
            return unavailable(f'Stability/solution check failed: {error}')
        residual = matrix @ displacement - force
        if not np.isfinite(displacement).all() or np.max(np.abs(residual[free])) > 1e-7 * max(1., np.max(np.abs(force))):
            return unavailable('Equilibrium solution failed its residual check')
    reactions = matrix @ displacement - force
    reactions[~fixed] = 0
    axial, stress, buckling = [], [], []
    for dofs, direction, stiffness, length, p in elements:
        tension = stiffness * direction @ displacement[dofs]
        axial.append(tension)
        stress.append(tension / p.area_m2)
        buckling.append(max(-tension, 0) / (np.pi**2 * p.E_pa * p.inertia_m4 / length**2)
                        if p.inertia_m4 > 0 else np.nan)
    def table(vector, labels):
        frame = pd.DataFrame(vector.reshape(n, 3), columns=labels)
        frame.insert(0, 'node_id', node_ids)
        return frame
    return SolveResult(True, 'Stable linear equilibrium', pd.Series(axial, index=ids),
                       pd.Series(stress, index=ids), table(displacement, ['ux', 'uy', 'uz']),
                       table(reactions, ['rx', 'ry', 'rz']), pd.Series(buckling, index=ids))
