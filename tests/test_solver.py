import math

import pytest

from domestage.solver import solve_truss
from test_schema import tripod_model


@pytest.mark.xfail(raises=NotImplementedError, reason="solver not implemented yet")
def test_tripod_hand_calculation():
    m = tripod_model(density=0.0)
    res = solve_truss(m, active_bar_ids=[1, 2, 3], extra_loads=m.loads, include_self_weight=False)
    assert res.stable
    expected = -1000 * math.sqrt(2) / 3
    for f in res.axial_force_n:
        assert f == pytest.approx(expected, rel=1e-6)
    uz = res.displacements.loc[res.displacements["node_id"] == 4, "uz"].iloc[0]
    assert uz == pytest.approx(-4.714e-5, rel=1e-3)


@pytest.mark.xfail(raises=NotImplementedError, reason="solver not implemented yet")
def test_two_bars_is_unstable():
    m = tripod_model()
    res = solve_truss(m, active_bar_ids=[1, 2], extra_loads=m.loads, include_self_weight=False)
    assert not res.stable
