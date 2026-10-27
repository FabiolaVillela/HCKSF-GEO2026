import io
import math
from pathlib import Path
import tempfile
import unittest
import ezdxf
import numpy as np
from domecalc import Model, Material, Section
from domecalc.importer import inspect_dxf, declared_units, Inspection
from domecalc.catalog import MATERIALS, HSS
from domecalc.truss import analyze_truss
from domecalc.workflow import run_analysis


def encode(doc):
    stream = io.StringIO(); doc.write(stream)
    return stream.getvalue().encode('utf-8')


def tripod():
    nodes = [[math.cos(i*2*math.pi/3),math.sin(i*2*math.pi/3),0] for i in range(3)]+[[0,0,1]]
    return Model(nodes,[(i,3,'test') for i in range(3)],{i:(0,1,2) for i in range(3)})


class ImportTests(unittest.TestCase):
    def test_mm_merges_euclidean_endpoints(self):
        d=ezdxf.new(); d.units=4
        d.modelspace().add_line((0,0,0),(1000,0,0))
        d.modelspace().add_line((1000.0005,0,0),(1000,1000,0))
        result=inspect_dxf(encode(d))
        self.assertTrue(result.ready)
        self.assertEqual(len(result.model.nodes),3)
        np.testing.assert_allclose(result.model.nodes[-1],[1,1,0])

    def test_unknown_units_must_be_selected(self):
        d=ezdxf.new();d.units=0;d.modelspace().add_line((0,0,0),(10,0,0))
        self.assertIsNone(declared_units(encode(d)))
        with self.assertRaises(ValueError): inspect_dxf(encode(d))
        self.assertTrue(inspect_dxf(encode(d),'ft').ready)

    def test_block_and_polyline_world_coordinates(self):
        d=ezdxf.new();d.units=6
        block=d.blocks.new('B')
        block.add_lwpolyline([(0,0),(1,0),(1,1)])
        d.modelspace().add_blockref('B',(10,20,3),dxfattribs={'rotation':90,'xscale':2,'yscale':2})
        result=inspect_dxf(encode(d))
        self.assertTrue(result.ready,result.report['errors'])
        self.assertEqual(len(result.model.elements),2)
        np.testing.assert_allclose(result.model.nodes,[[10,20,3],[10,22,3],[8,22,3]],atol=1e-10)

    def test_binary_dxf(self):
        d=ezdxf.new();d.units=6;d.modelspace().add_line((0,0,0),(1,0,0))
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'binary.dxf';d.saveas(p,fmt='bin');content=p.read_bytes()
        self.assertTrue(inspect_dxf(content).ready)

    def test_duplicate_zero_and_disconnection_reported(self):
        d=ezdxf.new();d.units=6;m=d.modelspace()
        m.add_line((0,0,0),(1,0,0));m.add_line((1,0,0),(0,0,0))
        m.add_line((2,0,0),(2,0,0));m.add_line((5,0,0),(6,0,0))
        result=inspect_dxf(encode(d))
        self.assertFalse(result.ready)
        self.assertEqual(result.report['duplicate_bars'],1)
        self.assertEqual(result.report['zero_bars'],1)
        self.assertEqual(len(result.report['components']),2)

    def test_curves_block_analysis_unless_layer_excluded(self):
        d=ezdxf.new();d.units=6;m=d.modelspace()
        m.add_line((0,0,0),(1,0,0),dxfattribs={'layer':'bars'})
        m.add_circle((0,0),2,dxfattribs={'layer':'cover'})
        m.add_text('nota')
        content=encode(d)
        self.assertFalse(inspect_dxf(content).ready)
        result=inspect_dxf(content,layers=['bars'])
        self.assertTrue(result.ready)
        self.assertIn('cover',result.report['excluded_layers'])

    def test_3d_polyline(self):
        d=ezdxf.new();d.units=6;d.modelspace().add_polyline3d([(0,0,0),(1,0,1),(1,1,2)])
        result=inspect_dxf(encode(d))
        self.assertTrue(result.ready,result.report['errors'])
        self.assertEqual(len(result.model.elements),2)

    def test_malformed(self):
        with self.assertRaises(ValueError): inspect_dxf(b'not a dxf')


class ConfigurationTests(unittest.TestCase):
    def test_pin_jointed_tripod_analytical(self):
        m=tripod();material=Material(density=0);section=Section(1e-4,1e-8,1e-8,2e-8)
        r=analyze_truss(m,material,section,nodal_loads={3:[0,0,-1000]})
        for e in r['elements']:
            self.assertAlmostEqual(e['stations'][0]['N_Vy_Vz_T_My_Mz'][0],-1000*math.sqrt(2)/3)
        self.assertAlmostEqual(r['nodes'][3]['displacement'][2],-1000*2*math.sqrt(2)/(3*200e9*1e-4))
        self.assertAlmostEqual(sum(n['reaction'][2] for n in r['nodes']),1000)

    def test_configuration_material_changes_mass_and_connection_changes_result(self):
        inspection=Inspection(tripod(),{'errors':[]})
        profile=list(HSS)[2]
        steel=run_analysis(inspection,'Acero',profile,'Empotradas',[0,1,2])
        alu=run_analysis(inspection,'Aluminio',profile,'Empotradas',[0,1,2])
        truss=run_analysis(inspection,'Acero',profile,'Articuladas',[0,1,2])
        self.assertTrue(all(r['stable'] for r in [steel,alu,truss]))
        self.assertAlmostEqual(alu['summary']['mass_kg']/steel['summary']['mass_kg'],2700/7850)
        self.assertNotEqual(steel['nodes'][3]['displacement'][2],truss['nodes'][3]['displacement'][2])
        self.assertEqual(truss['configuration']['self_weight_model'],'lumped_at_nodes')
        for r in [steel,alu,truss]: np.testing.assert_allclose(r['summary']['balance_force_N'],0,atol=1e-6)

    def test_mechanism_returned_without_crash(self):
        m=Model([[0,0,0],[1,0,0]],[(0,1,'test')])
        inspection=Inspection(m,{'errors':[]})
        r=run_analysis(inspection,'Acero',list(HSS)[2],'Articuladas',[0])
        self.assertFalse(r['stable']);self.assertIn('inestable',r['message'])
        r=run_analysis(inspection,'Acero',list(HSS)[2],'Empotradas',[0],'Empotrados')
        self.assertTrue(r['stable'])

    def test_all_catalog_sections_positive(self):
        for diameter,thickness in HSS.values(): self.assertGreater(Section.circular(diameter,thickness).A,0)

if __name__=='__main__': unittest.main()
