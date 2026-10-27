"""Armadura espacial articulada: 3 GDL/nodo y peso propio nodal equivalente."""
import numpy as np
from .core import Material, Section, element_matrices


def analyze_truss(model, material=None, section=None, gravity=(0,0,-9.80665), nodal_loads=None):
    material = material or Material(); section = section or Section.circular()
    xyz = np.asarray(model.nodes, dtype=float); n = len(xyz)
    if xyz.shape != (n,3) or not np.isfinite(xyz).all() or n == 0:
        raise ValueError('Nodos inválidos.')
    K = np.zeros((3*n,3*n)); F = np.zeros(3*n); records = []; length = 0.
    for i,j,layer in model.elements:
        if not (0<=i<n and 0<=j<n) or i==j: raise ValueError('Conectividad inválida.')
        delta = xyz[j]-xyz[i]; L = float(np.linalg.norm(delta))
        if L<=1e-12: raise ValueError('Barra nula.')
        direction = delta/L
        local = material.E*section.A/L*np.outer(direction,direction)
        dofs = np.r_[np.arange(3*i,3*i+3),np.arange(3*j,3*j+3)]
        k = np.block([[local,-local],[-local,local]])
        K[np.ix_(dofs,dofs)] += k
        weight = np.asarray(gravity)*material.density*section.A*L
        F[3*i:3*i+3] += weight/2; F[3*j:3*j+3] += weight/2
        records.append((i,j,layer,L,direction)); length += L
    for node,load in (nodal_loads or {}).items():
        if not 0<=node<n or len(load) not in (3,6) or not np.isfinite(load).all():
            raise ValueError('Carga nodal inválida.')
        if len(load)==6 and any(load[3:]): raise ValueError('Una armadura articulada no admite momentos nodales.')
        F[3*node:3*node+3] += load[:3]
    fixed = []
    for node,axes in model.supports.items():
        if not 0<=node<n or any(a not in range(6) for a in axes): raise ValueError('Apoyo inválido.')
        fixed.extend(3*node+a for a in axes if a<3)
    fixed = np.array(sorted(set(fixed)),dtype=int)
    free = np.setdiff1d(np.arange(3*n),fixed); U = np.zeros(3*n); condition = 1.
    if len(free):
        matrix = K[np.ix_(free,free)]; diag = np.diag(matrix)
        if np.any(diag<=0): raise ValueError('Modelo articulado inestable: traslaciones sin rigidez.')
        scale = 1/np.sqrt(diag); matrix = scale[:,None]*matrix*scale[None,:]
        eig = np.linalg.eigvalsh(matrix)
        if eig[0]<=1e-12*eig[-1]: raise ValueError('Modelo articulado inestable: mecanismo o matriz mal condicionada.')
        U[free] = scale*np.linalg.solve(matrix,scale*F[free]); condition=float(eig[-1]/eig[0])
    residual = K@U-F
    if len(free) and np.max(np.abs(residual[free]))>1e-6*max(1,np.max(np.abs(F))):
        raise ValueError('Residual de solución excesivo.')
    reactions = np.zeros(3*n); reactions[fixed] = residual[fixed]
    bars = []
    for eid,(i,j,layer,L,direction) in enumerate(records):
        axial = float(material.E*section.A/L*np.dot(direction,U[3*j:3*j+3]-U[3*i:3*i+3]))
        _,R,_,_,_,_ = element_matrices(xyz[i],xyz[j],material,section,(0,0,0))
        bars.append(dict(id=eid,i=i,j=j,layer=layer,length_m=L,local_axes_rows=R.tolist(),
                         end_actions_local=[-axial,0,0,0,0,0,axial,0,0,0,0,0],
                         stations=[{'x_m':float(s),'N_Vy_Vz_T_My_Mz':[axial,0,0,0,0,0]} for s in np.linspace(0,L,11)]))
    force = (F+reactions).reshape(n,3)
    return dict(units={'length':'m','force':'N','moment':'N m','rotation':'rad'},
                summary=dict(nodes=n,elements=len(bars),supports=len(model.supports),length_m=length,
                             mass_kg=length*section.A*material.density,
                             max_displacement_m=float(np.linalg.norm(U.reshape(n,3),axis=1).max()),
                             scaled_condition_number=condition,balance_force_N=force.sum(axis=0).tolist(),
                             balance_moment_Nm=np.cross(xyz,force).sum(axis=0).tolist()),
                nodes=[dict(id=i,xyz_m=xyz[i].tolist(),displacement=[*U[3*i:3*i+3].tolist(),0,0,0],
                            reaction=[*reactions[3*i:3*i+3].tolist(),0,0,0],fixed_dofs=list(model.supports.get(i,()))) for i in range(n)],
                elements=bars)
