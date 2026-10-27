import json
from html import unescape
from pathlib import Path
import re
import tempfile
import unittest
from domecalc import Model, analyze
from domecalc.viewer import export_viewer


class ViewerExportTests(unittest.TestCase):
    def test_embedded_data_safe_and_reactions_preserved(self):
        layer = '</script><img src=x onerror=alert(1)>'
        result = analyze(Model([[0, 0, 0], [3, 0, 0]], [(0, 1, layer)], {0: tuple(range(6))}))
        with tempfile.TemporaryDirectory() as directory:
            html = export_viewer(result, Path(directory) / 'viewer.html').read_text()
        self.assertNotIn('__DOME_DATA__', html)
        frame = unescape(re.search(r'data-srcdoc="(.*?)"', html, re.S)[1])
        payload = re.search(r'<script type="application/json" id="di-data">(.*?)</script>', frame, re.S)[1]
        self.assertNotIn('<img', payload)
        data = json.loads(payload)
        self.assertEqual(data['bars'][0]['layer'], layer)
        self.assertAlmostEqual(data['nodes'][0]['r'][2], result['nodes'][0]['reaction'][2] / 1000)
        self.assertTrue(data['nodes'][0]['s'])


if __name__ == '__main__':
    unittest.main()
