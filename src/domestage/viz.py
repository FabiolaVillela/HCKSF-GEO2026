"""Plotly figures. OWNER: Role 5 (visualization).

Depends on: schema.py only (StageResult / StructureModel). Develop with fake data.
"""
from __future__ import annotations

from typing import List

import plotly.graph_objects as go

from .schema import StageResult, StructureModel


def figure_3d(
    model: StructureModel,
    stage_result: StageResult,
    color_by: str = "stress",
    deformation_scale: float = 0.0,
) -> go.Figure:
    """3D view: active bars colored by `color_by` ("stress", "force", "utilization",
    "buckling"), inactive bars in light gray, supports marked, optional deformed shape.
    Unstable stages must show a clear warning in the title.
    """
    raise NotImplementedError


def figure_stage_history(results: List[StageResult], metric: str = "max_force") -> go.Figure:
    """Line plot of a metric vs stage ("max_force", "max_stress", "max_disp",
    "max_buckling"). Unstable stages are marked in red."""
    raise NotImplementedError
