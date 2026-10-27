"""Synthetic triangulated dome shared by the CLI and app."""
from __future__ import annotations
import math
from numbers import Integral
import pandas as pd
from .schema import (StructureModel, NODES_COLS, BARS_COLS, PROFILES_COLS,
                     SUPPORTS_COLS, LOADS_COLS)


def generate_dome(rings: int = 3, sides: int = 8, radius: float = 5.0):
    if (not isinstance(rings, Integral) or not isinstance(sides, Integral)
            or rings < 1 or sides < 3 or not math.isfinite(radius) or radius <= 0):
        raise ValueError('Require rings >= 1, sides >= 3, and a positive finite radius')
    nodes, bars, loads = [], [], []
    for ring in range(rings):
        angle = ring * math.pi / (2 * rings)
        for side in range(sides):
            azimuth = side * 2 * math.pi / sides
            nodes.append((ring*sides+side+1, radius*math.cos(angle)*math.cos(azimuth),
                          radius*math.cos(angle)*math.sin(azimuth), radius*math.sin(angle)))
    apex = len(nodes) + 1
    nodes.append((apex, 0., 0., radius))
    def add(i, j, stage):
        bars.append((len(bars)+1, i, j, 'TUBE', stage))
    for ring in range(rings):
        for side in range(sides):
            i = ring*sides+side+1
            following = ring*sides+(side+1) % sides+1
            add(i, following, ring)
            if ring < rings-1:
                add(i, i+sides, ring+1)
                add(i, following+sides, ring+1)
            else:
                add(i, apex, rings)
    for stage in range(1, rings+1):
        node = stage*sides+1 if stage < rings else apex
        loads.append((stage, node, 0., 0., -1000.))
    return StructureModel(
        pd.DataFrame(nodes, columns=NODES_COLS), pd.DataFrame(bars, columns=BARS_COLS),
        pd.DataFrame([('TUBE', 5e-4, 5e-7, 200e9, 7850.)], columns=PROFILES_COLS),
        pd.DataFrame([(i+1, True, True, True) for i in range(sides)], columns=SUPPORTS_COLS),
        pd.DataFrame(loads, columns=LOADS_COLS))
