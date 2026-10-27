"""Plotly views of construction stages. Values shown in SI units."""
from __future__ import annotations
from typing import List
import numpy as np
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from .schema import StageResult, StructureModel


def figure_3d(model: StructureModel, stage_result: StageResult, color_by: str = 'stress',
              deformation_scale: float = 0.0) -> go.Figure:
    r = stage_result.result
    available = {'stress': (r.stress_pa, 'Stress (Pa)'), 'force': (r.axial_force_n, 'Axial force (N)'),
                 'utilization': (r.stress_pa.abs() / model.criteria['yield_pa'], 'Axial stress / yield'),
                 'buckling': (r.buckling_ratio, 'Compression / Euler load')}
    if color_by not in available:
        raise ValueError(f'Unknown color metric: {color_by}')
    if not np.isfinite(deformation_scale) or deformation_scale < 0:
        raise ValueError('deformation_scale must be finite and nonnegative')
    values, label = available[color_by]
    finite = values.dropna() if values is not None else []
    signed = color_by in ('force', 'stress')
    limit = float(np.max(np.abs(finite))) if len(finite) else 1.
    limit = max(limit, 1e-30)
    low, high = (-limit, limit) if signed else (0., limit)
    palette = 'RdBu_r' if signed else 'Viridis'
    xyz = model.nodes.set_index('node_id')[['x', 'y', 'z']]
    figure = go.Figure()
    active = set(stage_result.active_bars)
    for bar in model.bars.itertuples():
        points = xyz.loc[[bar.node_i, bar.node_j]].to_numpy()
        value = values.get(bar.bar_id, np.nan) if values is not None else np.nan
        installed = bar.bar_id in active
        color = (sample_colorscale(palette, [(value-low)/(high-low)])[0]
                 if installed and r.stable and np.isfinite(value) else '#666666' if installed else '#dddddd')
        text = f'Bar {bar.bar_id} · {label}: {value:.4g}' if installed and r.stable else f'Bar {bar.bar_id} · ' + ('unstable' if installed else 'not installed')
        figure.add_trace(go.Scatter3d(x=points[:, 0], y=points[:, 1], z=points[:, 2],
                                     mode='lines', line=dict(color=color, width=5 if installed else 2),
                                     text=text, hoverinfo='text', showlegend=False))
    supports = xyz.loc[model.supports.node_id]
    figure.add_trace(go.Scatter3d(x=supports.x, y=supports.y, z=supports.z, mode='markers',
                                 marker=dict(color='black', size=4, symbol='diamond'), name='Supports'))
    if r.stable and len(finite):
        figure.add_trace(go.Scatter3d(x=[None], y=[None], z=[None], mode='markers',
                                     marker=dict(color=[low], colorscale=palette, cmin=low, cmax=high,
                                                 showscale=True, colorbar=dict(title=label)), showlegend=False))
    if r.stable and deformation_scale:
        moved = xyz.copy()
        disp = r.displacements.set_index('node_id')[['ux', 'uy', 'uz']]
        moved.loc[disp.index] += deformation_scale * disp.to_numpy()
        coords = [[], [], []]
        for bar in model.bars.loc[model.bars.bar_id.isin(active)].itertuples():
            points = moved.loc[[bar.node_i, bar.node_j]].to_numpy()
            for axis in range(3):
                coords[axis].extend([*points[:, axis], None])
        figure.add_trace(go.Scatter3d(x=coords[0], y=coords[1], z=coords[2], mode='lines',
                                     line=dict(color='orange', width=3), name=f'Deformed ×{deformation_scale:g}'))
    figure.update_layout(title=f'Step {stage_result.stage}' + (' — UNSTABLE' if not r.stable else ''),
                         scene=dict(aspectmode='data', xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)'),
                         height=550, margin=dict(l=0, r=0, b=0, t=40))
    return figure


def figure_stage_history(results: List[StageResult], metric: str = 'max_force') -> go.Figure:
    labels = {'max_force': 'Max |axial force| (N)', 'max_stress': 'Max |stress| (Pa)',
              'max_disp': 'Max displacement (m)', 'max_buckling': 'Max compression / Euler load'}
    if metric not in labels:
        raise ValueError(f'Unknown metric: {metric}')
    values = []
    for stage in results:
        r = stage.result
        if not r.stable:
            values.append(None)
        elif metric == 'max_disp':
            values.append(float(np.linalg.norm(r.displacements[['ux', 'uy', 'uz']], axis=1).max()))
        else:
            series = {'max_force': r.axial_force_n, 'max_stress': r.stress_pa,
                      'max_buckling': r.buckling_ratio}[metric]
            values.append(float(series.abs().max()) if series is not None and series.notna().any() else None)
    figure = go.Figure(go.Scatter(x=[s.stage for s in results], y=values, mode='lines+markers',
                                 connectgaps=False, name=labels[metric]))
    unstable = [s for s in results if not s.result.stable]
    figure.add_trace(go.Scatter(x=[s.stage for s in unstable], y=[0]*len(unstable), mode='markers',
                                 marker=dict(color='red', symbol='x', size=10), name='Unstable (no result)',
                                 text=[s.result.message for s in unstable], hoverinfo='text+x'))
    figure.update_layout(xaxis_title='Analysis step', yaxis_title=labels[metric])
    return figure
