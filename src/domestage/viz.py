"""Plotly views of construction stages (SI units) and the dynamic dashboard charts."""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd
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


def create_dome_3d_figure(
    model: StructureModel,
    active_bar_ids: List[int],
    new_bar_ids: List[int],
    axial_forces: Optional[pd.Series] = None,
    color_by: str = "axial_force",  # "axial_force" | "stage"
    show_future_bars: bool = True,
    analysis_stable: bool = True,
    worker_node: Optional[int] = None,
    support_label: str = "articulado",
) -> go.Figure:
    """Build an interactive 3D wireframe plot representing the current installation stage."""
    fig = go.Figure()

    nodes_dict = {
        row.node_id: (row.x, row.y, row.z)
        for _, row in model.nodes.iterrows()
    }
    active_set = set(active_bar_ids)
    new_set = set(new_bar_ids)

    # 1. Plot Future / Uninstalled bars (ghost wireframe)
    if show_future_bars:
        ghost_x, ghost_y, ghost_z = [], [], []
        for _, bar in model.bars.iterrows():
            if bar.bar_id not in active_set:
                p1 = nodes_dict[bar.node_i]
                p2 = nodes_dict[bar.node_j]
                ghost_x.extend([p1[0], p2[0], None])
                ghost_y.extend([p1[1], p2[1], None])
                ghost_z.extend([p1[2], p2[2], None])

        if ghost_x:
            fig.add_trace(
                go.Scatter3d(
                    x=ghost_x,
                    y=ghost_y,
                    z=ghost_z,
                    mode="lines",
                    line=dict(color="rgba(202, 202, 202, 0.4)", width=1.5, dash="dot"),  # 29% Gray: #CACACA
                    name="Barras pendientes",
                    hoverinfo="none",
                )
            )

    # 2. Installed bars (active)
    # Segregate by tension, compression, or newly installed
    # Colors: Tension (Blue/Cyan), Compression (Red/Orange), Newly added (Lime/Yellow highlight)
    for _, bar in model.bars.iterrows():
        b_id = bar.bar_id
        if b_id not in active_set:
            continue

        p1 = nodes_dict[bar.node_i]
        p2 = nodes_dict[bar.node_j]
        bx = [p1[0], p2[0]]
        by = [p1[1], p2[1]]
        bz = [p1[2], p2[2]]

        force = axial_forces.get(b_id) if analysis_stable and axial_forces is not None else None
        is_new = b_id in new_set

        if force is None:
            color = "#737373"
            width = 3.5
            status_text = "Sin solución de equilibrio"
        elif is_new:
            color = "#00FF66"  # Highlight neon green
            width = 6.0
            status_text = "NUEVA EN ESTA ETAPA"
        elif force < -1e-1:
            color = "#EF4444"  # Red: Compresión
            width = 3.5
            status_text = f"Compresión ({force/1000:.2f} kN)"
        elif force > 1e-1:
            color = "#3B82F6"  # Blue: Tracción
            width = 3.5
            status_text = f"Tracción ({force/1000:.2f} kN)"
        else:
            color = "#9CA3AF"  # Gray
            width = 2.5
            status_text = f"Neutro ({force/1000:.2f} kN)"

        hover = (
            f"<b>Barra #{b_id}</b><br>"
            f"Nodos: {bar.node_i} ➔ {bar.node_j}<br>"
            f"Perfil: {bar.profile}<br>"
            + (f"Axial: {force/1000:.2f} kN<br>" if force is not None else "Axial: sin solución<br>")
            + f"Estado: {status_text}"
        )

        fig.add_trace(
            go.Scatter3d(
                x=bx,
                y=by,
                z=bz,
                mode="lines",
                line=dict(color=color, width=width),
                hovertext=hover,
                hoverinfo="text",
                showlegend=False,
            )
        )

    # 3. Supports (Base nodes)
    support_ids = set(model.supports["node_id"])
    sup_x = [nodes_dict[n][0] for n in support_ids if n in nodes_dict]
    sup_y = [nodes_dict[n][1] for n in support_ids if n in nodes_dict]
    sup_z = [nodes_dict[n][2] for n in support_ids if n in nodes_dict]

    fig.add_trace(
        go.Scatter3d(
            x=sup_x,
            y=sup_y,
            z=sup_z,
            mode="markers",
            marker=dict(size=5, color="#F59E0B", symbol="diamond"),
            name="Apoyos " + support_label,
            hoverinfo="name",
        )
    )

    # 4. Highlight newly installed node / worker position
    if worker_node is not None and worker_node in nodes_dict:
        person_node = worker_node
        px, py, pz = nodes_dict[person_node]
        fig.add_trace(
            go.Scatter3d(
                x=[px],
                y=[py],
                z=[pz],
                mode="markers+text",
                marker=dict(size=9, color="#10B981", symbol="circle"),
                text=["👷 Carga Instalador"],
                textposition="top center",
                textfont=dict(color="#10B981", size=12),
                name="Punto de instalación",
                hoverinfo="text",
            )
        )

    fig.update_layout(
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
            bgcolor="rgba(10, 15, 29, 0.95)",
            aspectmode="data",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.02,
            xanchor="center",
            x=0.5,
            font=dict(color="#E2E8F0"),
        ),
    )
    return fig


def create_history_chart(stage_history: List[dict], current_stage: int) -> go.Figure:
    """Line plot showing maximum axial forces evolution across stages."""
    df = pd.DataFrame(stage_history)

    fig = go.Figure()

    if not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["stage"],
                y=df["max_tension_kn"],
                mode="lines",
                name="Tracción Máx (kN)",
                line=dict(color="#3B82F6", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["stage"],
                y=df["max_compression_kn"],
                mode="lines",
                name="Compresión Máx (kN)",
                line=dict(color="#EF4444", width=2),
            )
        )
        # Vertical marker for current stage
        fig.add_vline(
            x=current_stage,
            line_width=2,
            line_dash="dash",
            line_color="#10B981",
            annotation_text=f"Etapa {current_stage}",
            annotation_position="top left",
            annotation_font_color="#10B981",
        )

    fig.update_layout(
        title="Historial de Fuerzas Axiales Extremas vs. Etapa de Montaje",
        title_font=dict(size=14, color="#E2E8F0"),
        xaxis=dict(title="Etapa de Construcción", color="#94A3B8", gridcolor="#334155"),
        yaxis=dict(title="Fuerza (kN)", color="#94A3B8", gridcolor="#334155"),
        paper_bgcolor="rgba(15, 23, 42, 0.6)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(font=dict(color="#E2E8F0")),
        height=260,
    )
    return fig

