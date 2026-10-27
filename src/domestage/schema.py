"""Shared data contract. OWNER: Role 0 (lead). Do NOT change without team agreement.

Units everywhere in the code: meters (m), newtons (N), pascals (Pa), kilograms (kg).
Convert units only when reading external files (DXF / Excel).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

G = 9.81  # m/s^2

NODES_COLS = ["node_id", "x", "y", "z"]
BARS_COLS = ["bar_id", "node_i", "node_j", "profile", "stage"]
PROFILES_COLS = ["profile", "area_m2", "inertia_m4", "E_pa", "density_kgm3"]
SUPPORTS_COLS = ["node_id", "fix_x", "fix_y", "fix_z"]  # booleans (True = restrained)
LOADS_COLS = ["stage", "node_id", "fx_n", "fy_n", "fz_n"]  # z is up, gravity is -z


@dataclass
class StructureModel:
    """Complete input of an analysis. All tables are pandas DataFrames."""

    nodes: pd.DataFrame
    bars: pd.DataFrame
    profiles: pd.DataFrame
    supports: pd.DataFrame
    loads: pd.DataFrame  # installation loads, by stage
    criteria: Dict[str, float] = field(default_factory=lambda: {"yield_pa": 250e6})


@dataclass
class SolveResult:
    """Result of solving ONE state of the structure."""

    stable: bool
    message: str
    axial_force_n: pd.Series  # index bar_id, tension positive
    stress_pa: pd.Series  # index bar_id
    displacements: pd.DataFrame  # columns node_id, ux, uy, uz
    reactions: pd.DataFrame  # columns node_id, rx, ry, rz
    buckling_ratio: Optional[pd.Series] = None  # |compression| / Euler load, index bar_id


@dataclass
class StageResult:
    """Result of one construction stage."""

    stage: int
    active_bars: List[int]
    new_bars: List[int]
    result: SolveResult


def validate_model(model: StructureModel) -> List[str]:
    """Return a list of problems found (empty list = model is valid)."""
    problems: List[str] = []
    for name, df, cols in [
        ("nodes", model.nodes, NODES_COLS),
        ("bars", model.bars, BARS_COLS),
        ("profiles", model.profiles, PROFILES_COLS),
        ("supports", model.supports, SUPPORTS_COLS),
        ("loads", model.loads, LOADS_COLS),
    ]:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            problems.append(f"{name}: missing columns {missing}")
    if problems:
        return problems

    node_ids = set(model.nodes["node_id"])
    if model.nodes["node_id"].duplicated().any():
        problems.append("nodes: duplicated node_id")
    if model.bars["bar_id"].duplicated().any():
        problems.append("bars: duplicated bar_id")
    bad = model.bars[
        ~model.bars["node_i"].isin(node_ids) | ~model.bars["node_j"].isin(node_ids)
    ]
    if len(bad):
        problems.append(f"bars: {len(bad)} bars reference unknown nodes")
    if (model.bars["node_i"] == model.bars["node_j"]).any():
        problems.append("bars: zero-length bar (node_i == node_j)")
    unknown_prof = set(model.bars["profile"]) - set(model.profiles["profile"])
    if unknown_prof:
        problems.append(f"bars: unknown profiles {sorted(unknown_prof)}")
    if not model.supports["node_id"].isin(node_ids).all():
        problems.append("supports: unknown node_id")
    if len(model.supports) == 0:
        problems.append("supports: at least one support is required")
    return problems
