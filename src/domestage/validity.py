"""Validity limit of the small-displacement linear analysis (issue #14).

A shallow near-mechanism (for example a node held by almost coplanar bars) has a tiny
stiffness out of that plane, so the linear solution is a valid equilibrium of the linear
model but swings the node through a large angle. Linear truss theory assumes small bar
rotations, so such a stage is reported as unsolved, like a mechanism, instead of as a
stable result with meaningless values.

The check is on the chord rotation of each bar: the transverse relative displacement of
its ends divided by its length. It does not depend on the size of the structure.
This is a validity limit of the model, not a serviceability or safety check.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

# 0.1 rad (5.7 degrees): sin(theta) and tan(theta) differ from theta by less than 0.4 %.
ROTATION_LIMIT_RAD = 0.1


def chord_rotations(start: Sequence[Sequence[float]], end: Sequence[Sequence[float]],
                    start_displacement: Sequence[Sequence[float]],
                    end_displacement: Sequence[Sequence[float]]) -> np.ndarray:
    """Chord rotation (rad) of every bar, from end coordinates and end displacements."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    delta = end - start
    length = np.linalg.norm(delta, axis=1)
    direction = delta / length[:, None]
    relative = np.asarray(end_displacement, dtype=float) - np.asarray(start_displacement, dtype=float)
    transverse = relative - np.sum(relative * direction, axis=1)[:, None] * direction
    return np.linalg.norm(transverse, axis=1) / length


def rotation_problem(bar_id, rotation_rad: float,
                     limit_rad: float = ROTATION_LIMIT_RAD) -> Optional[str]:
    """Return an explanatory message if a bar rotates more than the validity limit."""
    if not np.isfinite(rotation_rad) or rotation_rad > limit_rad:
        return (f'Linear analysis not valid: bar {bar_id} rotates {rotation_rad:.3g} rad '
                f'(limit {limit_rad:g} rad, {np.degrees(limit_rad):.1f} deg). '
                f'The active structure is a shallow near-mechanism.')
    return None
