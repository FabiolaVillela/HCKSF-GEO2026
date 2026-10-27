"""DXF -> nodes and bars tables. OWNER: Role 1 (DXF / geometry).

Depends on: schema.py only.
"""
from __future__ import annotations

from typing import Tuple

import pandas as pd


def read_dxf(
    path: str,
    unit_scale: float = 1.0,
    tol: float = 1e-3,
    layers: Tuple[str, ...] = (),
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read a 3D wireframe DXF.

    Args:
        path: DXF file path.
        unit_scale: multiply coordinates by this to get meters (mm -> 0.001).
        tol: endpoints closer than this (in meters) are merged into one node.
        layers: if not empty, only read entities in these layers.

    Returns:
        (nodes, bars) with columns schema.NODES_COLS and schema.BARS_COLS.
        `profile` is set to "DEFAULT" and `stage` to 0 (assigned later by stages_assign).

    TODO:
        - Read LINE (and POLYLINE/LWPOLYLINE segments) with ezdxf.
        - Merge endpoints within `tol` (e.g. scipy.spatial.cKDTree).
        - Report disconnected bars / duplicate bars.
    """
    raise NotImplementedError


def assign_stages_by_height(
    nodes: pd.DataFrame, bars: pd.DataFrame, ring_height: float
) -> pd.DataFrame:
    """Return a copy of `bars` with `stage` = ring index by bar mean height (lowest = 0).

    The first ring (stage 0) is considered already installed.
    """
    raise NotImplementedError


def detect_base_supports(nodes: pd.DataFrame, z_tol: float = 1e-3) -> pd.DataFrame:
    """Return a supports table (schema.SUPPORTS_COLS) with all nodes at minimum z fixed."""
    raise NotImplementedError
