import unittest
import numpy as np
from domecalc import Model, Material, Section, analyze

class SolverTests(unittest.TestCase):
    def setUp(self):
        self.mat=Material(); self.sec=Section.circular(); self.L=4.

    def test_cantilever_gravity_all_axes(self):
        for direction in ([1,0,0],[0,1,0],[0,0,1],[.3,.4,.5]):
            x=np.array(direction,dtype=float); x/=np.linalg.norm(x)
            gravity=np.array([0.,0.,-9.80665])
            m=Model([[0,0,0],(x*self.L).tolist()],[(0,1,'test')],{0:tuple(range(6))})
            r=analyze(m,self.mat,self.sec)
            w=self.mat.density*self.sec.A*gravity
            parallel=x*np.dot(x,w); perpendicular=w-parallel
            expected=parallel*self.L**2/(2*self.mat.E*self.sec.A)+perpendicular*self.L**4/(8*self.mat.E*self.sec.Iy)
            np.testing.assert_allclose(r['nodes'][1]['displacement'][:3],expected,atol=1e-10)
            np.testing.assert_allclose(r['nodes'][0]['reaction'][:3],-w*self.L,atol=1e-7)
            np.testing.assert_allclose(r['elements'][0]['stations'][-1]['N_Vy_Vz_T_My_Mz'],0,atol=1e-7)

    def test_fixed_beam_distributed_load(self):
        m=Model([[0,0,0],[self.L,0,0]],[(0,1,'test')],{0:tuple(range(6)),1:tuple(range(6))})
        r=analyze(m,self.mat,self.sec)
        w=self.mat.density*self.sec.A*9.80665
        self.assertAlmostEqual(r['nodes'][0]['reaction'][2],w*self.L/2)
        self.assertAlmostEqual(abs(r['nodes'][0]['reaction'][4]),w*self.L**2/12)
        middle=r['elements'][0]['stations'][5]['N_Vy_Vz_T_My_Mz']
        self.assertAlmostEqual(abs(middle[4]),w*self.L**2/24)

    def test_tip_axial_and_torsion(self):
        m=Model([[0,0,0],[self.L,0,0]],[(0,1,'test')],{0:tuple(range(6))})
        r=analyze(m,self.mat,self.sec,gravity=(0,0,0),nodal_loads={1:[1000,0,0,100,0,0]})
        self.assertAlmostEqual(r['nodes'][1]['displacement'][0],1000*self.L/(self.mat.E*self.sec.A))
        self.assertAlmostEqual(r['nodes'][1]['displacement'][3],100*self.L/(self.mat.G*self.sec.J))
        self.assertAlmostEqual(r['elements'][0]['stations'][0]['N_Vy_Vz_T_My_Mz'][0],1000)

    def test_unrestrained_rejected(self):
        with self.assertRaises(ValueError):
            analyze(Model([[0,0,0],[4,0,0]],[(0,1,'test')]))

if __name__=='__main__': unittest.main()
