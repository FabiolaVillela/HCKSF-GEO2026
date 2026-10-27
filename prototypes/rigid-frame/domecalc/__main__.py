import argparse
import json
from . import read_dxf, analyze, export
from .viewer import export_viewer

p = argparse.ArgumentParser(description='Pórtico 3D: peso propio, acero, HSS circular y base articulada')
p.add_argument('dxf')
p.add_argument('--output', default='resultados')
p.add_argument('--scale', type=float)
p.add_argument('--viewer', action='store_true', help='Generar también visor.html autocontenido')
a = p.parse_args()
model = read_dxf(a.dxf, scale=a.scale).pin_base()
r = analyze(model)
export(r, a.output)
if a.viewer:
    from pathlib import Path
    export_viewer(r, Path(a.output) / 'visor.html')
print(json.dumps(r['summary'], indent=2))
