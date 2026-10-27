"""3D pin-jointed truss solver. OWNER: Role 3 (solver).

Depends on: schema.py only. Must be testable WITHOUT dxf/excel/stages.
"""
from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from .schema import SolveResult, StructureModel


def solve_truss(
    model: StructureModel,
    active_bar_ids: Iterable[int],
    extra_loads: Optional[pd.DataFrame] = None,
    include_self_weight: bool = True,
) -> SolveResult:
    """Solve the equilibrium of the structure formed only by `active_bar_ids`.

    - Bars not active contribute neither stiffness nor weight.
    - Self-weight: each active bar weight = density * area * length * G, split 50/50 to
      its end nodes, acting in -z.
    - `extra_loads`: DataFrame with schema.LOADS_COLS minus `stage` (installation loads).
    - Stiffness: K_e = (E*A/L) * [[c c^T, -c c^T], [-c c^T, c c^T]], c = direction cosines.
    - Use scipy.sparse. Nodes with no active bar are ignored (not unstable).
    - Stability: if the reduced K is singular / ill-conditioned (e.g. cond > 1e12, or
      lowest eigenvalue ~ 0) return SolveResult(stable=False, message=...) with NaN
      results instead of raising.
    - Axial force positive = tension. stress = force / area.
    - buckling_ratio = max(-force, 0) / (pi^2 * E * I / L^2) when inertia_m4 > 0.

    Validation case: tests/test_solver.py (tripod with hand-calculated solution).
    """
    raise NotImplementedError
