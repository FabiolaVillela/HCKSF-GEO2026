"""Generate a synthetic geodesic/ring dome StructureModel for demonstration and tests."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from domestage.schema import StructureModel


def generate_demo_dome(
    rings: int = 4,
    sides: int = 12,
    radius: float = 6.0,
    total_height: float = 3.5,
) -> StructureModel:
    """Generate a hemisphere-like dome with concentric rings and triangulation."""
    nodes_data = []
    node_id = 0

    # Ring 0: base at ground (z=0)
    # Ring rings-1: highest ring
    # Top apex node
    ring_nodes = []
    for r in range(rings):
        phi = (math.pi / 2) * (r / rings)  # 0 at base, approaching apex
        z = total_height * math.sin(phi)
        r_current = radius * math.cos(phi)
        current_ring = []
        for s in range(sides):
            theta = 2 * math.pi * s / sides
            # Stagger alternate rings for nice triangulation
            if r % 2 == 1:
                theta += (math.pi / sides)
            x = r_current * math.cos(theta)
            y = r_current * math.sin(theta)
            nodes_data.append((node_id, round(x, 4), round(y, 4), round(z, 4)))
            current_ring.append(node_id)
            node_id += 1
        ring_nodes.append(current_ring)

    # Apex node
    apex_id = node_id
    nodes_data.append((apex_id, 0.0, 0.0, round(total_height, 4)))

    bars_data = []
    bar_id = 0

    # 1. Base ring bars (Stage 0: already in place)
    for s in range(sides):
        ni = ring_nodes[0][s]
        nj = ring_nodes[0][(s + 1) % sides]
        bars_data.append((bar_id, ni, nj, "PIPE-4IN", 0))
        bar_id += 1

    # 2. Intermediate rings and diagonal braces
    stage_counter = 1
    for r in range(rings - 1):
        lower_ring = ring_nodes[r]
        upper_ring = ring_nodes[r + 1]
        
        # Diagonals / verticals connecting ring r to r+1
        for s in range(sides):
            ni = lower_ring[s]
            nj = upper_ring[s]
            bars_data.append((bar_id, ni, nj, "PIPE-4IN", stage_counter))
            bar_id += 1
            stage_counter += 1

            # Diagonal
            nk = upper_ring[(s + 1) % sides]
            bars_data.append((bar_id, ni, nk, "PIPE-4IN", stage_counter))
            bar_id += 1
            stage_counter += 1

        # Horizontal ring bars
        for s in range(sides):
            ni = upper_ring[s]
            nj = upper_ring[(s + 1) % sides]
            bars_data.append((bar_id, ni, nj, "PIPE-4IN", stage_counter))
            bar_id += 1
            stage_counter += 1

    # 3. Apex bars to top node
    top_ring = ring_nodes[-1]
    for s in range(sides):
        ni = top_ring[s]
        bars_data.append((bar_id, ni, apex_id, "PIPE-4IN", stage_counter))
        bar_id += 1
        stage_counter += 1

    nodes_df = pd.DataFrame(nodes_data, columns=["node_id", "x", "y", "z"])
    bars_df = pd.DataFrame(bars_data, columns=["bar_id", "node_i", "node_j", "profile", "stage"])

    profiles_df = pd.DataFrame(
        [("PIPE-4IN", 9.81e-4, 1.15e-6, 200e9, 7850.0)],
        columns=["profile", "area_m2", "inertia_m4", "E_pa", "density_kgm3"],
    )

    # Base supports at z == 0
    supports_data = [(n, True, True, True) for n in ring_nodes[0]]
    supports_df = pd.DataFrame(supports_data, columns=["node_id", "fix_x", "fix_y", "fix_z"])

    # Sample installation load (person 100 kg = ~980 N) on newest node per stage
    loads_data = []
    for st in range(1, stage_counter + 1):
        # find newly active bars in this stage
        st_bars = bars_df[bars_df["stage"] == st]
        if len(st_bars) > 0:
            target_node = st_bars.iloc[-1]["node_j"]
            loads_data.append((st, target_node, 0.0, 0.0, -981.0))
        else:
            loads_data.append((st, 0, 0.0, 0.0, 0.0))
    loads_df = pd.DataFrame(loads_data, columns=["stage", "node_id", "fx_n", "fy_n", "fz_n"])

    return StructureModel(
        nodes=nodes_df,
        bars=bars_df,
        profiles=profiles_df,
        supports=supports_df,
        loads=loads_df,
        criteria={"yield_pa": 250e6},
    )
