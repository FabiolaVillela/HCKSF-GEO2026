"""Dynamic Plotly visualization for stage-by-stage dome assembly."""
from __future__ import annotations

from typing import List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .schema import StageResult, StructureModel


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

