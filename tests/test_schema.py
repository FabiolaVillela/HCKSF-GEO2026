import pandas as pd

from domestage.schema import StructureModel, validate_model


def tripod_model(density: float = 0.0) -> StructureModel:
    """Tripod: apex at (0,0,1), three base nodes on a circle of radius 1, load 1000 N down.

    Hand-calculated: each bar has force = -1000*sqrt(2)/3 = -471.40 N (compression),
    with A = 1e-4 m2 and E = 2e11 Pa the apex displacement is uz = -4.714e-5 m.
    """
    import math

    nodes = pd.DataFrame(
        [
            (1, math.cos(0), math.sin(0), 0.0),
            (2, math.cos(2 * math.pi / 3), math.sin(2 * math.pi / 3), 0.0),
            (3, math.cos(4 * math.pi / 3), math.sin(4 * math.pi / 3), 0.0),
            (4, 0.0, 0.0, 1.0),
        ],
        columns=["node_id", "x", "y", "z"],
    )
    bars = pd.DataFrame(
        [(1, 1, 4, "P", 0), (2, 2, 4, "P", 0), (3, 3, 4, "P", 0)],
        columns=["bar_id", "node_i", "node_j", "profile", "stage"],
    )
    profiles = pd.DataFrame(
        [("P", 1e-4, 0.0, 2e11, density)],
        columns=["profile", "area_m2", "inertia_m4", "E_pa", "density_kgm3"],
    )
    supports = pd.DataFrame(
        [(1, True, True, True), (2, True, True, True), (3, True, True, True)],
        columns=["node_id", "fix_x", "fix_y", "fix_z"],
    )
    loads = pd.DataFrame(
        [(0, 4, 0.0, 0.0, -1000.0)],
        columns=["stage", "node_id", "fx_n", "fy_n", "fz_n"],
    )
    return StructureModel(nodes, bars, profiles, supports, loads)


def test_tripod_is_valid():
    assert validate_model(tripod_model()) == []


def test_unknown_node_is_reported():
    m = tripod_model()
    m.bars.loc[0, "node_j"] = 99
    assert any("unknown nodes" in p for p in validate_model(m))
