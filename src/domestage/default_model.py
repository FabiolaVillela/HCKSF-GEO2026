"""Default model shown when the app starts: QuickDome Ø40.0 m, 13.3 m shell height (Geometrica).

The geometry comes from `examples/quickdome-40-0m-dia-13-3m-shell-height-no-boost.dxf`
(LINE entities, millimetres declared in $INSUNITS) and is imported with the same path a user
upload takes (`assembly.geometry_from_dxf`), so supports (lowest nodes) and the installation
order (by bar height) follow the same rules. Users can still upload any other DXF.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from .assembly import geometry_from_dxf

DEFAULT_DXF = Path(__file__).resolve().parents[2] / 'examples' / 'quickdome-40-0m-dia-13-3m-shell-height-no-boost.dxf'
DEFAULT_NAME = 'QuickDome Ø40.0 m · 13.3 m'
DEFAULT_TOLERANCE_M = 0.001  # same default merge tolerance as the simulator (1 mm)


@lru_cache(maxsize=1)
def _load():
    return geometry_from_dxf(DEFAULT_DXF.read_bytes(), None, DEFAULT_TOLERANCE_M)


def default_geometry():
    """Geometry dict of the default model (a fresh copy on every call)."""
    return deepcopy(_load()[0])


def default_model():
    """Default model for the UI: geometry plus a short description and the import report."""
    geometry, report = _load()
    return dict(name=DEFAULT_NAME, file=DEFAULT_DXF.name, geometry=deepcopy(geometry),
                nodes=report['nodes'], bars=report['elements'], supports=len(geometry['support_nodes']),
                units=report['units'], report=deepcopy(report))
