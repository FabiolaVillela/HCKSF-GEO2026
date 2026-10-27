import io
import math
from copy import deepcopy
import numpy as np
import pytest
import ezdxf
from domestage.assembly import (G,geometry_from_dxf,stage_plan,solve_stage,catalog)


def tetrahedron():
    nodes=[dict(id=10+i*10,x=math.cos(i*2*math.pi/3),y=math.sin(i*2*math.pi/3),z=0.) for i in range(3)]
    nodes.append(dict(id=90,x=0.,y=0.,z=1.))
    bars=[dict(id=101+i,i=nodes[i]['id'],j=nodes[(i+1)%3]['id'],isBase=True,order=0) for i in range(3)]
    bars += [dict(id=201+i,i=nodes[i]['id'],j=90,isBase=False,order=i+1) for i in range(3)]
    return dict(nodes=nodes,bars=bars,support_nodes=[10,20,30])


def config(**kwargs):
    return dict(material='Acero',profile=catalog()['profiles'][2],connection='articulada',support='articulado',bars_per_step=1,worker_kg=0,**({'node_dead_load_kg': 0} | kwargs))


def test_stage_grouping_and_mass_exclude_future_bars():
    model=tetrahedron()
    assert [len(s['new_bar_ids']) for s in stage_plan(model,1)]==[3,1,1,1]
    assert [len(s['new_bar_ids']) for s in stage_plan(model,2)]==[3,2,1]
    results=[solve_stage(model,config(),stage) for stage in range(4)]
    assert results[0]['stable']  # El nodo 90 aún no está instalado: no debe crear singularidad.
    assert [n['node_id'] for n in results[0]['displacements']]==[10,20,30]
    assert results[1]['status']=='unstable'
    assert results[2]['status']=='unstable'
    assert results[3]['stable']
    assert all(results[i]['mass_kg']<results[i+1]['mass_kg'] for i in range(3))
    assert results[1]['forces']=={} and results[1]['max_tension_kn'] is None
    assert results[1]['reactions']==[] and 'solution' not in results[1]
    assert results[3]['solution']['nodes'][0]['source_id']==10
    assert results[3]['solution']['elements'][0]['source_id']==101
    assert set(results[3]['forces'])=={'101','102','103','201','202','203'}


def test_worker_is_one_nodal_load_and_matches_tripod_hand_solution():
    model=tetrahedron();cfg=config()
    unloaded=solve_stage(model,cfg,3)
    cfg['worker_kg']=1000/G
    loaded=solve_stage(model,cfg,3)
    assert loaded['worker_node']==90
    assert loaded['worker_load_N']==pytest.approx(1000)
    for bid in ('201','202','203'):
        assert loaded['forces'][bid]-unloaded['forces'][bid]==pytest.approx(-1000*math.sqrt(2)/3)
    delta_u=loaded['displacements'][-1]['values'][2]-unloaded['displacements'][-1]['values'][2]
    from domecalc.catalog import properties
    material,section=properties(cfg['material'],cfg['profile'])
    assert delta_u==pytest.approx(-1000*2*math.sqrt(2)/(3*material.E*section.A))
    assert sum(n['values'][2] for n in loaded['reactions'])==pytest.approx(loaded['mass_kg']*G+1000)
    np.testing.assert_allclose(loaded['balance_force_N'],0,atol=1e-7)
    np.testing.assert_allclose(loaded['balance_moment_Nm'],0,atol=1e-7)
    assert solve_stage(model,cfg,0)['worker_load_N']==0


def test_material_profile_geometry_and_support_changes_invalidate_cache():
    model=tetrahedron();cfg=config()
    steel=solve_stage(model,cfg,3)
    cfg['material']='Aluminio'
    alu=solve_stage(model,cfg,3)
    assert alu['mass_kg']/steel['mass_kg']==pytest.approx(2700/7850)
    cfg['profile']=catalog()['profiles'][-1]
    bigger=solve_stage(model,cfg,3)
    assert bigger['mass_kg']>alu['mass_kg']
    shifted=deepcopy(model);shifted['nodes'][-1]['z']=2.
    assert solve_stage(shifted,cfg,3)['mass_kg']!=bigger['mass_kg']
    cfg['connection']='empotrada';cfg['support']='empotrado'
    rigid=solve_stage(model,cfg,1)
    assert rigid['stable']  # Barra nueva en voladizo soporta flexión.
    cfg['connection']='articulada'
    assert not solve_stage(model,cfg,1)['stable']
    # No reutilizar una solución de un modelo con apoyos distintos.
    cfg['connection']='empotrada'
    changed=deepcopy(model);changed['support_nodes']=[90]
    assert solve_stage(changed,cfg,0)['status']=='unstable'


def test_final_stage_equals_direct_frame_solver():
    from domecalc.core import Model,analyze
    from domecalc.catalog import properties
    model=tetrahedron();cfg=config();cfg.update(connection='empotrada',support='empotrado',worker_kg=100)
    staged=solve_stage(model,cfg,3)
    ids={n['id']:i for i,n in enumerate(model['nodes'])}
    direct=Model([[n['x'],n['y'],n['z']] for n in model['nodes']],[(ids[b['i']],ids[b['j']],'montaje') for b in model['bars']],{ids[n]:tuple(range(6)) for n in model['support_nodes']})
    mat,section=properties(cfg['material'],cfg['profile'])
    result=analyze(direct,mat,section,nodal_loads={ids[90]:[0,0,-100*G,0,0,0]})
    assert staged['max_displacement_mm']==pytest.approx(result['summary']['max_displacement_m']*1000)
    for b,e in zip(model['bars'],result['elements']):
        assert staged['forces'][str(b['id'])]==pytest.approx(e['stations'][5]['N_Vy_Vz_T_My_Mz'][0])


def test_empty_stage_and_bad_configuration_do_not_get_fake_forces():
    m=tetrahedron()
    for b in m['bars']:b['isBase']=False
    r=solve_stage(m,config(),0)
    assert r['status']=='empty' and r['stable'] is None
    assert r['max_tension_kn'] is None
    with pytest.raises(ValueError):solve_stage(m,config(),999)
    cfg=config();cfg['worker_kg']=-1
    with pytest.raises(ValueError):solve_stage(m,cfg,1)
    m['nodes'][0]['x']=float('nan')
    with pytest.raises(ValueError):solve_stage(m,config(),1)


def test_dxf_diagnostics_block_bad_geometry_and_units_are_not_guessed():
    d=ezdxf.new();d.units=0;d.modelspace().add_line((0,0,0),(100,0,0))
    def content():
        s=io.StringIO();d.write(s);return s.getvalue().encode()
    with pytest.raises(ValueError):geometry_from_dxf(content())
    geom,report=geometry_from_dxf(content(),'mm')
    assert geom['nodes'][1]['x']==pytest.approx(.1)
    d.modelspace().add_line((100,0,0),(0,0,0))
    with pytest.raises(ValueError,match='duplicadas'):geometry_from_dxf(content(),'mm')


def test_nodal_dead_load_tracks_installed_nodes_and_support_reactions():
    model = tetrahedron()
    cfg = config()
    cfg.pop('node_dead_load_kg')  # Production default is 25 kg per node.
    for stage, count in [(0, 3), (3, 4)]:
        loaded = solve_stage(model, cfg, stage)
        assert loaded['node_dead_load_total_N'] == pytest.approx(count * 25 * G)
        assert sum(n['values'][2] for n in loaded['reactions']) == pytest.approx((loaded['mass_kg'] + count * 25) * G)
        np.testing.assert_allclose(loaded['balance_force_N'], 0, atol=1e-7)
    unloaded = solve_stage(model, config(), 3)
    for bid in ('201', '202', '203'):
        assert loaded['forces'][bid] - unloaded['forces'][bid] == pytest.approx(-25 * G * math.sqrt(2) / 3)
    from domestage.aisc import check_result
    GRADE = {'grade': 'a500-21-c'}
    checked = check_result(loaded, GRADE)
    assert checked['max_utilization'] > check_result(unloaded, GRADE)['max_utilization']
    member = next(m for m in checked['members'] if str(m['id']) == '201')
    assert abs(member['factored_actions'][0]) == pytest.approx(1.4 * abs(loaded['forces']['201']))
