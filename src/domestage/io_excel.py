"""Read/write the shared Excel model and export stage results, in SI units."""
from __future__ import annotations
from typing import List
import numpy as np
import pandas as pd
from .schema import (StageResult, StructureModel, validate_model, NODES_COLS,
                     BARS_COLS, PROFILES_COLS, SUPPORTS_COLS, LOADS_COLS)

TABLES = [('Nodes', 'nodes', NODES_COLS), ('Bars', 'bars', BARS_COLS),
          ('Profiles', 'profiles', PROFILES_COLS), ('Supports', 'supports', SUPPORTS_COLS),
          ('Loads', 'loads', LOADS_COLS)]


def read_template(path: str) -> StructureModel:
    sheets = pd.read_excel(path, sheet_name=None, engine='openpyxl')
    required = {name for name, _, _ in TABLES} | {'Criteria'}
    if not required <= sheets.keys():
        raise ValueError(f'Missing sheets: {sorted(required - sheets.keys())}')
    for name, _, cols in TABLES:
        missing = set(cols) - set(sheets[name].columns)
        if missing:
            raise ValueError(f'{name}: missing columns {sorted(missing)}')
    supports = sheets['Supports'].copy()
    for col in ['fix_x', 'fix_y', 'fix_z']:
        def boolean(value):
            if isinstance(value, str):
                value = value.strip().lower()
                if value in ('true', 'false'):
                    return value == 'true'
            if value not in (0, 1, True, False):
                raise ValueError(f'Supports.{col}: use true/false or 0/1')
            return bool(value)
        supports[col] = supports[col].map(boolean)
    sheets['Supports'] = supports
    criteria = sheets['Criteria']
    if not {'name', 'value'} <= set(criteria.columns) or criteria.name.duplicated().any():
        raise ValueError('Criteria requires unique name/value rows, including yield_pa')
    model = StructureModel(**{attr: sheets[name][cols].copy() for name, attr, cols in TABLES},
                           criteria=dict(zip(criteria.name, criteria.value)))
    problems = validate_model(model)
    if problems:
        raise ValueError('; '.join(problems))
    return model


def write_template(model: StructureModel, path: str) -> None:
    problems = validate_model(model)
    if problems:
        raise ValueError('; '.join(problems))
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, attr, cols in TABLES:
            getattr(model, attr)[cols].to_excel(writer, sheet_name=name, index=False)
        pd.DataFrame(list(model.criteria.items()), columns=['name', 'value']).to_excel(
            writer, sheet_name='Criteria', index=False)


def export_results(results: List[StageResult], path: str) -> None:
    summary, bars, reactions, displacements = [], [], [], []
    for stage in results:
        r = stage.result
        disp = r.displacements[['ux', 'uy', 'uz']].to_numpy(dtype=float)
        summary.append(dict(stage=stage.stage, stable=r.stable, message=r.message,
                            active_bars=len(stage.active_bars),
                            max_force_n=r.axial_force_n.abs().max(),
                            max_stress_pa=r.stress_pa.abs().max(),
                            max_displacement_m=float(np.max(np.linalg.norm(disp, axis=1))) if len(disp) else np.nan))
        for bar in stage.active_bars:
            bars.append(dict(stage=stage.stage, bar_id=bar, force_n=r.axial_force_n.get(bar, np.nan),
                             stress_pa=r.stress_pa.get(bar, np.nan),
                             buckling_ratio=r.buckling_ratio.get(bar, np.nan) if r.buckling_ratio is not None else np.nan))
        reactions.append(r.reactions.assign(stage=stage.stage))
        displacements.append(r.displacements.assign(stage=stage.stage))
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        pd.DataFrame(summary, columns=['stage', 'stable', 'message', 'active_bars', 'max_force_n',
                                      'max_stress_pa', 'max_displacement_m']).to_excel(writer, sheet_name='Summary', index=False)
        pd.DataFrame(bars, columns=['stage', 'bar_id', 'force_n', 'stress_pa', 'buckling_ratio']).to_excel(writer, sheet_name='Bars', index=False)
        for name, frames, cols in [('Reactions', reactions, ['node_id', 'rx', 'ry', 'rz', 'stage']),
                                   ('Displacements', displacements, ['node_id', 'ux', 'uy', 'uz', 'stage'])]:
            (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols)).to_excel(writer, sheet_name=name, index=False)
