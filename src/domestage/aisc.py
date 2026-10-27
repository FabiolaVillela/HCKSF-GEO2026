"""Preliminary ANSI/AISC 360-22 LRFD checks for round steel HSS only.

Design basis approved by user: 1.4D, K=1, L=node-to-node in both planes,
0.93 nominal t, An=Ag, U=1, first-order demands. Not a Chapter C stability
verification. See docs/AISC.md. Analysis inputs/results are never mutated.
"""
from __future__ import annotations
import math
import numpy as np
from .assembly import HSS, MATERIALS, solve_stage, stage_plan
from .design_materials import design_material

BASIS=dict(specification='ANSI/AISC 360-22',method='LRFD',load_combination='1.4D',load_factor=1.4,
           thickness_factor=.93,K_y=1.,K_z=1.,phi_t_yield=.9,phi_t_rupture=.75,phi_c=.9,phi_b=.9,length_basis='node-to-node, both local bending planes',
           net_area='An=Ag; no holes',U=1.,analysis='first-order, independent stage')
LIMITATIONS=[
 'Preliminary member checks only: Chapter C second-order/stability requirements are not verified.',
 'K=1 and unbraced compression length equal to the modeled member length in each stage are assumptions, not verified bracing.',
 'Full-section load transfer U=1 and no holes are assumed; connections, welds and block shear are not checked.',
 'Shear, torsion and their combined-force interactions (G/H3), fatigue, serviceability and erection stability are outside this check.',
 'Elastic stiffness and self-weight retain existing nominal geometry; only resistance properties use 0.93t.',
]


def positive(value,name):
    if isinstance(value,bool):raise ValueError(name+' must be finite and positive.')
    value=float(value)
    if not math.isfinite(value) or value<=0:raise ValueError(name+' must be finite and positive.')
    return value


def round_capacities(diameter,nominal_t,length,Fy,Fu,E=200e9):
    """SI: m, Pa, N, N m. B4, D2, E3/E7.2, F8; no LTB for round HSS."""
    D,tn,L,Fy,Fu,E=[positive(v,n) for v,n in zip((diameter,nominal_t,length,Fy,Fu,E),('D','t','L','Fy','Fu','E'))]
    if Fu<Fy:raise ValueError('Fu must be >= Fy.')
    if 2*tn>=D:raise ValueError('Invalid hollow section dimensions.')
    t=.93*tn;d=D-2*t;A=math.pi*(D*D-d*d)/4;I=math.pi*(D**4-d**4)/64
    S=2*I/D;Z=(D**3-d**3)/6;r=math.sqrt(I/A);lam=D/t
    if lam>=.45*E/Fy:raise ValueError('D/t outside E7.2/F8 scope (must be < 0.45E/Fy).')
    Ae=A if lam<=.11*E/Fy else min(A,(.038*E/(Fy*lam)+2/3)*A)
    slenderness=L/r;Fe=math.pi**2*E/slenderness**2
    # E3-2 / E3-3, using the stress-ratio boundary specified in E3.
    inelastic=Fy/Fe<=2.25
    Fcr=(.658**(Fy/Fe))*Fy if inelastic else .877*Fe
    Pc=.9*Fcr*Ae
    Pt_yield=.9*Fy*A;Pt_rupture=.75*Fu*A  # D2, An=Ag and approved U=1.
    Pt=min(Pt_yield,Pt_rupture)
    Mp=Fy*Z
    if lam<=.07*E/Fy:
        classification='compact';Mn=Mp;flex_ref='F8-1'
    elif lam<=.31*E/Fy:
        classification='noncompact';Mn=min(Mp,(.021*E/lam+Fy)*S);flex_ref='F8-2'
    else:
        classification='slender';Mn=min(Mp,.33*E/lam*S);flex_ref='F8-3/F8-4'
    return dict(E_Pa=E,Fy_Pa=Fy,Fu_Pa=Fu,D_m=D,t_nominal_m=tn,t_design_m=t,A_m2=A,I_m4=I,S_m3=S,Z_m3=Z,r_m=r,D_over_t=lam,
                L_m=L,K=1.,KL_over_r=slenderness,Fe_Pa=Fe,Fcr_Pa=Fcr,Ae_compression_m2=Ae,
                compression_class='nonslender' if Ae==A else 'slender',flexure_class=classification,
                phiPn_compression_N=Pc,phiPn_tension_N=Pt,phiPn_yield_N=Pt_yield,phiPn_rupture_N=Pt_rupture,
                phiMn_Nm=.9*Mn,tension_reference='D2-1' if Pt_yield<=Pt_rupture else 'D2-2',
                compression_reference=('E3-2' if inelastic else 'E3-3')+(' + E7-7' if Ae<A else ''),
                flexure_reference=flex_ref,LTB='not applicable to round HSS')


def station_checks(actions,c):
    """Concurrent six local actions of ONE station, factored only here."""
    if len(actions)!=6 or not all(math.isfinite(x) for x in actions):raise ValueError('Six finite local actions required.')
    N,Vy,Vz,T,My,Mz=[1.4*x for x in actions]
    tension=N>=0;Pc=c['phiPn_tension_N'] if tension else c['phiPn_compression_N']
    p=abs(N)/Pc;my=abs(My)/c['phiMn_Nm'];mz=abs(Mz)/c['phiMn_Nm'];m=my+mz
    # H1.2 also invokes H1-1a/b for tension; local y/z correspond to AISC bending axes.
    interaction=p+8/9*m if p>=.2 else p/2+m
    ref='H1-1a' if p>=.2 else 'H1-1b'
    # At the H1 branch cut include the one-sided limit conservatively; the
    # piecewise expressions need not coincide for large bending ratios.
    if math.isclose(p,.2,rel_tol=1e-10,abs_tol=1e-12) and p/2+m>interaction:
        interaction=p/2+m;ref='H1-1b (boundary envelope)'
    axial_ref=c['tension_reference'] if tension else c['compression_reference']
    candidates=[(p,axial_ref,'tension' if tension else 'compression'),
                (m,c['flexure_reference'],'biaxial flexure (conservative sum)'),
                (interaction,('H1.2/' if tension else 'H1.1/')+ref,'flexotension' if tension else 'flexocompression')]
    u,equation,state=max(candidates,key=lambda a:a[0])
    return dict(utilization=u,equation=equation,limit_state=state,axial_ratio=p,bending_ratio=m,
                interaction_ratio=interaction,component_ratios=dict(axial=p,My=my,Mz=m),factored_actions=[N,Vy,Vz,T,My,Mz])


def critical_stations(element,c):
    """Exact candidates for piecewise-quadratic H1 under current uniform gravity.

    Reconstruct the six action polynomials from solver samples; validate their
    agreement. Split at sign changes and H1 branch boundaries, then find each
    quadratic derivative zero. This avoids missing extrema between 11 samples.
    """
    stations=element['stations'];L=positive(element['length_m'],'L')
    if len(stations)<3:raise ValueError('At least three station samples required.')
    x=np.array([s['x_m']/L for s in stations]);a=np.array([s['N_Vy_Vz_T_My_Mz'] for s in stations],dtype=float)
    if a.shape!=(len(x),6) or not np.isfinite(a).all() or not np.isfinite(x).all():raise ValueError('Invalid station data.')
    if x[0]!=0 or not math.isclose(x[-1],1) or np.any(np.diff(x)<=0):raise ValueError('Station coordinates must span the member in order.')
    idx=[0,len(x)//2,len(x)-1]
    coeff=np.linalg.solve(np.array([[1,x[i],x[i]**2] for i in idx]),a[idx])
    fitted=np.array([1+0*x,x,x*x]).T@coeff
    if not np.allclose(fitted,a,rtol=1e-7,atol=1e-7):raise ValueError('Actions are not quadratic: unsupported load distribution.')
    def roots(poly):
        poly=np.trim_zeros(np.array(poly,dtype=float)[::-1],'f')
        if len(poly)<2:return []
        return [float(r.real) for r in np.roots(poly) if abs(r.imag)<1e-9 and 0<r.real<1]
    cuts={0.,1.,*x.tolist()}
    for col in (0,4,5):cuts.update(roots(coeff[:,col]))
    for Pc in (c['phiPn_compression_N'],c['phiPn_tension_N']):
        for sign in (-1,1):
            p=coeff[:,0].copy();p[0]-=sign*.2*Pc/1.4;cuts.update(roots(p))
    points=set(cuts);ordered=sorted(cuts)
    for lo,hi in zip(ordered,ordered[1:]):
        mid=(lo+hi)/2;v=np.array([1,mid,mid*mid])@coeff
        Pc=c['phiPn_tension_N'] if v[0]>=0 else c['phiPn_compression_N']
        ppoly=1.4*np.sign(v[0])*coeff[:,0]/Pc
        mpoly=1.4*(np.sign(v[4])*coeff[:,4]+np.sign(v[5])*coeff[:,5])/c['phiMn_Nm']
        high=abs(v[0])*1.4/Pc>=.2
        for poly in (ppoly,mpoly,ppoly+(8/9)*mpoly if high else ppoly/2+mpoly):
            if abs(poly[2])>1e-18:
                critical=-poly[1]/(2*poly[2])
                if lo<critical<hi:points.add(float(critical))
    return [(float(v*L),(np.array([1,v,v*v])@coeff).tolist()) for v in sorted(points)]


def check_result(result,design):
    """Pure postprocess; does not change original demands or original result JSON."""
    mat=design_material(result['material'],design)
    report=dict(stage=result['stage'],profile=result['profile'],material=mat,basis=dict(BASIS),
                limitations=list(LIMITATIONS),status='unavailable',members=[],max_utilization=None,governing=None)
    if result['material']!='Acero':
        report['message']='AISC 360 does not apply to aluminum; a dedicated aluminum design module is required.';return report
    if result.get('worker_load_N',0):raise ValueError('1.4D check accepts dead load only: remove installer load.')
    if not result.get('stable'):
        report['message']='No resistance check without stage equilibrium.';return report
    D,t=HSS[result['profile']];E=MATERIALS['Acero'].E
    for element in result['elements']:
        member=dict(id=element['id'],status='unavailable',utilization=None)
        try:
            c=round_capacities(D,t,element['length_m'],mat['Fy_MPa']*1e6,mat['Fu_MPa']*1e6,E)
            checks=[dict(x_m=x,**station_checks(actions,c)) for x,actions in critical_stations(element,c)]
            governing=max(checks,key=lambda v:v['utilization'])
            member.update(status='within_scope' if governing['utilization']<=1 else 'exceeds',capacities=c,**governing)
            if c['KL_over_r']>200:member['warning']='KL/r > 200; E2 preferred slenderness limit exceeded.'
        except ValueError as exc:member['message']=str(exc)
        report['members'].append(member)
    valid=[m for m in report['members'] if m['utilization'] is not None]
    if valid:
        g=max(valid,key=lambda m:m['utilization']);report.update(max_utilization=g['utilization'],governing=dict(member_id=g['id'],equation=g['equation'],limit_state=g['limit_state'],x_m=g['x_m']))
    complete=len(valid)==len(report['members']) and bool(valid)
    report.update(status='preliminary' if complete else 'incomplete',message='Preliminary first-order member checks; not a complete AISC design approval.')
    return report


def check_stage(geometry,config,stage,design):
    return check_result(solve_stage(geometry,config,stage),design)


def check_all_stages(geometry,config,design):
    return [check_stage(geometry,config,s['stage'],design) for s in stage_plan(geometry,config.get('bars_per_step',2))]
