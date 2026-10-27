from dataclasses import dataclass, field
from pathlib import Path
import csv
import json
import math
import numpy as np

@dataclass(frozen=True)
class Material:
    E: float = 200e9
    nu: float = 0.30
    density: float = 7850.0

    def __post_init__(self):
        if not (self.E > 0 and -1 < self.nu < .5 and self.density >= 0):
            raise ValueError('Propiedades de material inválidas')

    @property
    def G(self):
        return self.E / (2 * (1 + self.nu))

@dataclass(frozen=True)
class Section:
    A: float
    Iy: float
    Iz: float
    J: float

    def __post_init__(self):
        if not all(math.isfinite(v) and v > 0 for v in (self.A,self.Iy,self.Iz,self.J)):
            raise ValueError('Propiedades de sección inválidas')

    @classmethod
    def circular(cls, diameter=.1016, thickness=.003175):
        if not 0 < 2 * thickness < diameter:
            raise ValueError('Diámetro o espesor inválido')
        inner = diameter - 2 * thickness
        area = math.pi * (diameter**2 - inner**2) / 4
        inertia = math.pi * (diameter**4 - inner**4) / 64
        return cls(area, inertia, inertia, 2 * inertia)

@dataclass
class Model:
    nodes: list
    elements: list  # (nodo i, nodo j, capa), índices desde cero
    supports: dict = field(default_factory=dict)  # nodo: índices de GDL restringidos

    def pin_base(self, tolerance=1e-6):
        z = min(p[2] for p in self.nodes)
        self.supports = {i: (0,1,2) for i,p in enumerate(self.nodes) if abs(p[2]-z)<=tolerance}
        return self


def read_dxf(path, scale=None, tolerance=1e-6):
    """DXF ASCII LINE 3D; tolerancia en metros. No divide cruces interiores."""
    if tolerance <= 0:
        raise ValueError('Tolerancia debe ser positiva')
    rows = Path(path).read_text().splitlines()
    if len(rows)%2:
        raise ValueError('DXF ASCII inválido')
    pairs = [(rows[i].strip(), rows[i+1].strip()) for i in range(0,len(rows),2)]
    if scale is None:
        unit = next((pairs[i+1][1] for i,p in enumerate(pairs[:-1]) if p==('9','$INSUNITS')),None)
        scales = {'1':.0254,'2':.3048,'4':.001,'5':.01,'6':1.0}
        if unit not in scales:
            raise ValueError('Unidades desconocidas; especificar scale (metros/unidad DXF)')
        scale = scales[unit]
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Escala inválida')
    entities=[]; current=None; active=False
    for code,value in pairs:
        if code=='2' and value=='ENTITIES':
            active=True; continue
        if not active: continue
        if code=='0':
            if current: entities.append(current)
            current=None
            if value=='ENDSEC': break
            current={'type':value}
        elif current is not None: current[code]=value
    unsupported = sorted({e['type'] for e in entities if e['type']!='LINE'})
    if unsupported:
        raise ValueError(f'Convertir entidades a LINE 3D antes de importar: {unsupported}')
    nodes=[]; elements=[]; seen=set()
    def node(point):
        for i,p in enumerate(nodes):
            if np.linalg.norm(np.array(p)-point)<=tolerance: return i
        nodes.append(point.tolist()); return len(nodes)-1
    for e in entities:
        p=np.array([float(e.get(str(k),0))*scale for k in (10,20,30)])
        q=np.array([float(e.get(str(k),0))*scale for k in (11,21,31)])
        if not np.isfinite([p,q]).all(): raise ValueError('Coordenada no finita')
        i,j=node(p),node(q)
        if i==j: raise ValueError('Barra de longitud nula o menor que tolerancia')
        key=tuple(sorted((i,j)))
        if key in seen: raise ValueError(f'Barra duplicada {key}')
        seen.add(key); elements.append((i,j,e.get('8','0')))
    if not elements: raise ValueError('DXF sin líneas')
    return Model(nodes,elements)


def element_matrices(p, q, material, section, gravity):
    delta=q-p; L=float(np.linalg.norm(delta))
    if L<=1e-12: raise ValueError('Elemento de longitud nula')
    x=delta/L
    ref=np.array([0.,0.,1.]) if abs(x[2])<.9 else np.array([0.,1.,0.])
    y=np.cross(ref,x); y/=np.linalg.norm(y); z=np.cross(x,y)
    R=np.array([x,y,z]); T=np.zeros((12,12))
    for i in (0,3,6,9): T[i:i+3,i:i+3]=R
    k=np.zeros((12,12))
    for ids,value in [([0,6],material.E*section.A/L),([3,9],material.G*section.J/L)]:
        k[np.ix_(ids,ids)]=value*np.array([[1,-1],[-1,1]])
    base=np.array([[12,6*L,-12,6*L],[6*L,4*L*L,-6*L,2*L*L],[-12,-6*L,12,-6*L],[6*L,2*L*L,-6*L,4*L*L]])
    k[np.ix_([1,5,7,11],[1,5,7,11])]=material.E*section.Iz/L**3*base
    signs=np.diag([1,-1,1,-1])
    k[np.ix_([2,4,8,10],[2,4,8,10])]=material.E*section.Iy/L**3*(signs@base@signs)
    w=R@np.asarray(gravity)*material.density*section.A
    f=np.zeros(12)
    f[:3]=f[6:9]=w*L/2
    f[4]=-w[2]*L**2/12; f[10]=-f[4]
    f[5]=w[1]*L**2/12; f[11]=-f[5]
    return L,R,T,k,f,w


def analyze(model, material=None, section=None, gravity=(0,0,-9.80665), nodal_loads=None, stations=11):
    """Carga nodal: dict nodo -> [Fx,Fy,Fz,Mx,My,Mz]. Apoyos con movimiento cero.
    Retorna datos serializables; cada sección interior reporta acción sobre cara +x.
    """
    material=material or Material(); section=section or Section.circular()
    if stations<2: raise ValueError('Se requieren al menos dos estaciones')
    xyz=np.asarray(model.nodes,dtype=float); n=len(xyz); nd=6*n
    if xyz.shape!=(n,3) or not np.isfinite(xyz).all(): raise ValueError('Nodos inválidos')
    K=np.zeros((nd,nd)); F=np.zeros(nd); records=[]; total_length=0
    for i,j,layer in model.elements:
        if not (0<=i<n and 0<=j<n) or i==j: raise ValueError('Conectividad inválida')
        L,R,T,k,f,w=element_matrices(xyz[i],xyz[j],material,section,gravity)
        dofs=np.r_[np.arange(6*i,6*i+6),np.arange(6*j,6*j+6)]
        K[np.ix_(dofs,dofs)]+=T.T@k@T; F[dofs]+=T.T@f
        records.append((i,j,layer,L,R,T,k,f,w,dofs)); total_length+=L
    for node,load in (nodal_loads or {}).items():
        if not 0<=node<n or len(load)!=6 or not np.isfinite(load).all(): raise ValueError('Carga inválida')
        F[6*node:6*node+6]+=load
    fixed=[]
    for node,axes in model.supports.items():
        if not 0<=node<n or any(a not in range(6) for a in axes): raise ValueError('Apoyo inválido')
        fixed.extend(6*node+a for a in axes)
    fixed=np.array(sorted(set(fixed)),dtype=int)
    free=np.setdiff1d(np.arange(nd),fixed); U=np.zeros(nd)
    if len(free):
        A=K[np.ix_(free,free)]; diagonal=np.diag(A)
        if np.any(diagonal<=0): raise ValueError('Modelo inestable: GDL sin rigidez')
        s=1/np.sqrt(diagonal); scaled=s[:,None]*A*s[None,:]
        eig=np.linalg.eigvalsh(scaled)
        if eig[0]<=1e-12*eig[-1]: raise ValueError('Modelo inestable o excesivamente mal condicionado')
        U[free]=s*np.linalg.solve(scaled,s*F[free])
        condition=float(eig[-1]/eig[0])
    else: condition=1.
    residual=K@U-F
    if len(free) and np.max(np.abs(residual[free]))>1e-6*max(1,np.max(np.abs(F))):
        raise ValueError('Residual de solución excesivo')
    reactions=np.zeros(nd); reactions[fixed]=residual[fixed]
    bars=[]
    for eid,(i,j,layer,L,R,T,k,f,w,dofs) in enumerate(records):
        ends=k@(T@U[dofs])-f
        samples=[]
        for distance in np.linspace(0,L,stations):
            force=-ends[:3]-w*distance
            moment=-ends[3:6]+np.cross([distance,0,0],ends[:3])+np.cross([distance**2/2,0,0],w)
            samples.append({'x_m':float(distance),'N_Vy_Vz_T_My_Mz':np.r_[force,moment].tolist()})
        bars.append({'id':eid,'i':i,'j':j,'layer':layer,'length_m':L,'local_axes_rows':R.tolist(),
                     'end_actions_local':ends.tolist(),'stations':samples})
    applied=F.reshape(n,6); reac=reactions.reshape(n,6)
    balance_force=np.sum(applied[:,:3]+reac[:,:3],axis=0)
    balance_moment=np.sum(applied[:,3:]+reac[:,3:]+np.cross(xyz,applied[:,:3]+reac[:,:3]),axis=0)
    return {'units':{'length':'m','force':'N','moment':'N m','rotation':'rad'},
            'summary':{'nodes':n,'elements':len(bars),'supports':len(model.supports),'length_m':total_length,
                       'mass_kg':total_length*section.A*material.density,'max_displacement_m':float(np.linalg.norm(U.reshape(n,6)[:,:3],axis=1).max()),
                       'scaled_condition_number':condition,'balance_force_N':balance_force.tolist(),'balance_moment_Nm':balance_moment.tolist()},
            'nodes':[{'id':i,'xyz_m':xyz[i].tolist(),'displacement':U.reshape(n,6)[i].tolist(),
                      'reaction':reac[i].tolist(),'fixed_dofs':list(model.supports.get(i,()))} for i in range(n)],'elements':bars}


def export(result, directory):
    out=Path(directory); out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    with (out/'nodes.csv').open('w',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['node','x_m','y_m','z_m','ux_m','uy_m','uz_m','rx_rad','ry_rad','rz_rad','Fx_N','Fy_N','Fz_N','Mx_Nm','My_Nm','Mz_Nm'])
        for node in result['nodes']: writer.writerow([node['id'],*node['xyz_m'],*node['displacement'],*node['reaction']])
    with (out/'forces.csv').open('w',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['element','i','j','layer','x_m','N_N','Vy_N','Vz_N','T_Nm','My_Nm','Mz_Nm'])
        for bar in result['elements']:
            for station in bar['stations']: writer.writerow([bar['id'],bar['i'],bar['j'],bar['layer'],station['x_m'],*station['N_Vy_Vz_T_My_Mz']])
    (out/'report.md').write_text('# Análisis elástico lineal del domo\n\n'+ '\n'.join(f'- {k}: {v}' for k,v in result['summary'].items())+'\n\nUnidades SI. No incluye comprobaciones de resistencia, pandeo ni segundo orden.\n')
