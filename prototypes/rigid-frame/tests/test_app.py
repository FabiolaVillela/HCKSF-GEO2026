"""Prueba el flujo completo sin servidor ni navegador externo."""
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import ezdxf

HAS_STREAMLIT = importlib.util.find_spec('streamlit') is not None


@unittest.skipUnless(HAS_STREAMLIT, 'Instalar streamlit para probar la interfaz')
class AppTests(unittest.TestCase):
    def test_upload_configure_analyze_and_invalidate(self):
        from streamlit.testing.v1 import AppTest
        doc=ezdxf.new();doc.units=6;m=doc.modelspace()
        for p in [(1,0,0),(-.5,.866,0),(-.5,-.866,0)]: m.add_line(p,(0,0,1))
        stream=io.StringIO();doc.write(stream)
        upload=io.BytesIO(stream.getvalue().encode());upload.name='tripod.dxf'
        app=Path(__file__).resolve().parents[1]/'app.py'
        with patch('streamlit.file_uploader',return_value=upload):
            at=AppTest.from_file(str(app),default_timeout=30).run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(at.button[0].disabled)
            at.checkbox[0].check().run()
            self.assertFalse(at.button[0].disabled)
            at.button[0].click().run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(at.session_state['analysis'][1]['stable'])
            at.selectbox[1].select('Aluminio').run()
            self.assertTrue(any('configuración cambió' in i.value for i in at.info))
            at.radio[0].set_value('Articuladas').run()
            at.button[0].click().run()
            self.assertEqual(len(at.exception),0)
            self.assertEqual(at.session_state['analysis'][1]['configuration']['connections'],'Articuladas')

    def test_import_error_stops_before_configuration(self):
        from streamlit.testing.v1 import AppTest
        doc=ezdxf.new();doc.units=6;m=doc.modelspace()
        m.add_line((0,0,0),(1,0,0));m.add_line((1,0,0),(0,0,0))
        stream=io.StringIO();doc.write(stream)
        upload=io.BytesIO(stream.getvalue().encode());upload.name='duplicate.dxf'
        with patch('streamlit.file_uploader',return_value=upload):
            at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            self.assertEqual(len(at.exception),0)
            self.assertTrue(any('duplicadas' in error.value for error in at.error))
            self.assertEqual(len(at.radio),0)

if __name__=='__main__': unittest.main()
