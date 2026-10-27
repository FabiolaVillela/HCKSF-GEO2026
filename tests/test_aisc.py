"""Independent hand checks, interaction branches, station extrema and API regression."""
import json
import math
from copy import deepcopy
import pytest
from domestage.aisc import (round_capacities,station_checks,critical_stations,check_result,check_stage,check_all_stages)
from domestage.design_materials import design_material,material_catalog
from domestage.assembly import solve_stage
from test_assembly import tetrahedron,config
from test_server import post

GRADE={'grade':'a500-21-c'}


def cap(L=2.,Fy=345e6,Fu=425e6):
    return round_capacities(.1016,.003175,L,Fy,Fu)


def element(actions,length=2.):
    return dict(id=99,length_m=length,stations=[dict(x_m=length*x,N_Vy_Vz_T_My_Mz=actions(x)) for x in [i/10 for i in range(11)]])


def test_properties_and_hand_capacity():
    c=cap();D=101.6;t=.93*3.175;d=D-2*t
    A=math.pi/4*(D**2-d**2);I=math.pi/64*(D**4-d**4);Z=(D**3-d**3)/6;r=math.sqrt(I/A)
    assert c['t_design_m']*1000==pytest.approx(2.95275)
    assert c['A_m2']*1e6==pytest.approx(A)
    assert c['I_m4']*1e12==pytest.approx(I)
    assert c['Z_m3']*1e9==pytest.approx(Z)
    Fe=math.pi**2*200000/(2000/r)**2
    Fcr=.658**(345/Fe)*345
    assert c['phiPn_compression_N']==pytest.approx(.9*Fcr*A)
    assert c['phiPn_tension_N']==pytest.approx(min(.9*345*A,.75*425*A))
    assert c['phiMn_Nm']==pytest.approx(.9*345*Z/1000)
    assert c['flexure_class']=='compact'
    assert c['tension_reference']=='D2-1'


@pytest.mark.parametrize('p,expected,ref',[(.199,.199/2+.3,'H1-1b'),(.2,.2+8/9*.3,'H1-1a'),(.8,.8+8/9*.3,'H1-1a')])
@pytest.mark.parametrize('sign',[-1,1])
def test_interaction_uses_h1_for_both_compression_and_tension(p,expected,ref,sign):
    c=cap();P=c['phiPn_tension_N' if sign==1 else 'phiPn_compression_N'];M=c['phiMn_Nm']
    result=station_checks([sign*p*P/1.4,0,0,0,.1*M/1.4,-.2*M/1.4],c)
    assert result['interaction_ratio']==pytest.approx(expected)
    assert result['equation'].endswith(ref)
    assert result['limit_state']==('flexotension' if sign==1 else 'flexocompression')


def test_axial_is_not_halved_and_exceedance_not_clamped():
    c=cap();P=c['phiPn_tension_N']
    assert station_checks([.1*P/1.4,0,0,0,0,0],c)['utilization']==pytest.approx(.1)
    assert station_checks([1.5*P/1.4,0,0,0,0,0],c)['utilization']==pytest.approx(1.5)
    assert station_checks([0,0,0,0,c['phiMn_Nm']/1.4,0],c)['utilization']==pytest.approx(1)


def test_elastic_column_branch_and_local_buckling_classes():
    c=cap(30)
    assert c['compression_reference']=='E3-3'
    assert c['Fcr_Pa']==pytest.approx(.877*c['Fe_Pa'])
    # Select design D/t directly by choosing nominal t accordingly.
    def section(lam):return round_capacities(.2,.2/lam/.93,2.,345e6,425e6)
    noncompact=section(60);slender=section(200)
    assert noncompact['flexure_class']=='noncompact'
    assert noncompact['phiMn_Nm']==pytest.approx(.9*(.021*200e9/60+345e6)*noncompact['S_m3'])
    assert slender['flexure_class']=='slender' and slender['compression_class']=='slender'
    assert slender['Ae_compression_m2']==pytest.approx((.038*200e9/(345e6*200)+2/3)*slender['A_m2'])
    assert slender['phiMn_Nm']==pytest.approx(.9*.33*200e9/200*slender['S_m3'])
    with pytest.raises(ValueError,match='scope'):section(300)


@pytest.mark.parametrize('D,t,L,Fy,Fu',[(0,.01,2,345e6,425e6),(.1,.05,2,345e6,425e6),(.1,.003,0,345e6,425e6),(.1,.003,2,float('nan'),425e6),(.1,.003,2,345e6,200e6)])
def test_invalid_dimensions_and_material_rejected(D,t,L,Fy,Fu):
    with pytest.raises(ValueError):round_capacities(D,t,L,Fy,Fu)


def test_analytic_critical_point_between_stations():
    c=cap();M=c['phiMn_Nm']
    e=element(lambda x:[0,0,0,0,M/1.4*(1.2-(x-.37)**2),0])
    checks=[(x,station_checks(v,c)['utilization']) for x,v in critical_stations(e,c)]
    x,u=max(checks,key=lambda v:v[1])
    assert x==pytest.approx(.74)
    assert u==pytest.approx(1.2)
    assert u>max(station_checks(s['N_Vy_Vz_T_My_Mz'],c)['utilization'] for s in e['stations'])


def test_sign_and_branch_splits_match_dense_reference():
    c=cap();P=c['phiPn_compression_N'];M=c['phiMn_Nm']
    actions=lambda x:[P/1.4*(x-.4),0,0,0,M/1.4*(.8-3*(x-.35)**2),M/1.4*(x-.6)]
    e=element(actions)
    candidates=max(station_checks(v,c)['utilization'] for _,v in critical_stations(e,c))
    dense=max(station_checks(actions(i/10000),c)['utilization'] for i in range(10001))
    assert candidates>=dense-1e-9
    assert candidates==pytest.approx(dense,abs=1e-6)
    e['stations'][3]['N_Vy_Vz_T_My_Mz'][4]+=100
    with pytest.raises(ValueError,match='quadratic'):critical_stations(e,c)


def test_stage_identity_only_active_members_no_physics_mutation():
    g,cfg=tetrahedron(),config();r=solve_stage(g,cfg,3);before=deepcopy(r)
    checked=check_result(r,GRADE)
    assert checked['stage']==3 and checked['status']=='preliminary'
    assert {m['id'] for m in checked['members']}==set(r['active_bar_ids'])
    assert r==before
    assert solve_stage(g,cfg,3)==before
    governing=max(checked['members'],key=lambda m:m['utilization'])
    assert checked['max_utilization']==governing['utilization']
    series=check_all_stages(g,cfg,GRADE)
    assert [r['stage'] for r in series]==[0,1,2,3]
    assert series[1]['max_utilization'] is None and series[1]['members']==[]
    assert series[-1]==checked
    assert {m['id'] for m in series[0]['members']}=={101,102,103}


def test_aluminum_grade_matching_and_worker_rejection():
    g,cfg=tetrahedron(),config();cfg['material']='Aluminio'
    r=check_stage(g,cfg,3,{'grade':'6061-t6'})
    assert r['status']=='unavailable' and r['max_utilization'] is None
    with pytest.raises(ValueError):check_stage(g,cfg,3,GRADE)
    cfg['material']='Acero';cfg['worker_kg']=100
    with pytest.raises(ValueError,match='dead load only'):check_stage(g,cfg,3,GRADE)


def test_catalog_and_custom_sources_and_validation():
    assert len(material_catalog())==4
    assert design_material('Acero',GRADE)['Fy_MPa']==345
    custom=dict(grade='custom',Fy_MPa=250,Fu_MPa=400,source='certificate 123')
    assert design_material('Acero',custom)['source']=='certificate 123'
    for changes in [dict(source=''),dict(Fy_MPa=float('nan')),dict(Fu_MPa=100)]:
        with pytest.raises(ValueError):design_material('Acero',{**custom,**changes})
    with pytest.raises(ValueError):design_material('Acero',{})


def test_report_exceedance_and_unknown_scope():
    r=solve_stage(tetrahedron(),config(),3)
    for e in r['elements']:
        for s in e['stations']:s['N_Vy_Vz_T_My_Mz'][0]=1e8
    checked=check_result(r,GRADE)
    assert checked['max_utilization']>1
    assert all(m['status']=='exceeds' for m in checked['members'])
    custom=dict(grade='custom',Fy_MPa=5000,Fu_MPa=6000,source='synthetic test')
    limited=check_result(r,custom)
    assert limited['status']=='incomplete' and limited['max_utilization'] is None


def test_aisc_api_separate_from_stage_endpoint():
    payload=dict(geometry=tetrahedron(),config=config(),stage=3,design=GRADE)
    before=post('/api/stage',payload)[1]
    status,r=post('/api/aisc',payload)
    assert status==200 and r['status']=='preliminary'
    assert post('/api/stage',payload)[1]==before
    status,series=post('/api/aisc/progress',payload)
    assert status==200 and len(series)==4
    assert post('/api/aisc',{**payload,'design':{}})[0]==400


def test_rupture_controls_and_zero_demand():
    c=cap(Fy=400e6,Fu=425e6)
    assert c['tension_reference']=='D2-2'
    assert station_checks([0]*6,c)['utilization']==0
    assert station_checks([c['phiPn_tension_N']/1.4,0,0,0,0,0],c)['utilization']==pytest.approx(1)


def test_round_boundaries_and_capacity_reduction():
    E,Fy=200e9,345e6
    for coefficient,classification in [(.07,'compact'),(.070001,'noncompact'),(.31,'noncompact'),(.310001,'slender')]:
        lam=coefficient*E/Fy
        c=round_capacities(.2,.2/lam/.93,2,Fy,425e6)
        assert c['flexure_class']==classification
    for L in (2.,10.,30.):
        c=cap(L)
        assert c['phiPn_compression_N']>0
    assert cap(2)['phiPn_compression_N']>cap(10)['phiPn_compression_N']>cap(30)['phiPn_compression_N']


def test_no_combining_demands_from_distinct_stations():
    c=cap();P=c['phiPn_compression_N'];M=c['phiMn_Nm']
    # Compression peaks at i; bending peaks at j. No fictitious combined peak.
    e=element(lambda x:[-.6*P/1.4*(1-x),0,0,0,.6*M/1.4*x,0])
    result=max(station_checks(a,c)['utilization'] for _,a in critical_stations(e,c))
    assert result==pytest.approx(.6,abs=1e-7)
    assert result<.6+8/9*.6


def test_h1_boundary_includes_conservative_one_sided_limit():
    c=cap();P=c['phiPn_compression_N'];M=c['phiMn_Nm']
    r=station_checks([-.2*P/1.4,0,0,0,2*M/1.4,0],c)
    assert r['utilization']==pytest.approx(2.1)
    assert 'boundary envelope' in r['equation']
