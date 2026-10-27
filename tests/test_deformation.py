from copy import deepcopy
import pytest
from domestage.deformation import nodal_positions


def test_real_two_mm_scaled_to_twenty_without_mutation():
    nodes={10:[0,0,0],90:[1,0,0]}
    u={10:[0,0,0],90:[0,0,-.002,5,6,7]}
    before=deepcopy((nodes,u))
    assert nodal_positions(nodes,u,10)=={10:[0,0,0],90:[1,0,-.02]}
    assert nodal_positions(nodes,u,0)==nodes
    assert (nodes,u)==before


@pytest.mark.parametrize('factor',[-1,float('inf'),float('nan'),100001])
def test_invalid_factor_rejected(factor):
    with pytest.raises(ValueError):nodal_positions({10:[0,0,0]},{10:[0,0,0]},factor)


def test_plotly_opt_in_and_active_only():
    from types import SimpleNamespace
    import pandas as pd
    from domestage.viz import create_dome_3d_figure
    model=SimpleNamespace(nodes=pd.DataFrame([[10,0,0,0],[90,1,0,0],[99,2,0,1]],columns=['node_id','x','y','z']),bars=pd.DataFrame([[201,10,90,0,'HSS'],[202,90,99,1,'HSS']],columns=['bar_id','node_i','node_j','stage','profile']),supports=pd.DataFrame([[10]],columns=['node_id']))
    args=dict(model=model,active_bar_ids=[201],new_bar_ids=[],displacements={10:[0,0,0],90:[0,0,-.002]})
    assert not any((t.name or '').startswith('Deformada') for t in create_dome_3d_figure(**args).data)
    fig=create_dome_3d_figure(**args,show_deformed=True,deformation_scale=10)
    trace=next(t for t in fig.data if (t.name or '').startswith('Deformada'))
    assert tuple(trace.z)==(0,-.02,None)
    assert len(trace.x)==3
    assert not any((t.name or '').startswith('Deformada') for t in create_dome_3d_figure(**args,show_deformed=True,analysis_stable=False).data)
