"""Servidor local del simulador: PYTHONPATH=src python -m domestage.server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import argparse
import json

from .assembly import catalog, geometry_from_dxf, geometry_from_structure, progress_series, stage_plan, solve_stage
from .demo_model import generate_demo_dome
from .default_model import DEFAULT_NAME, default_model
from .report_figures import build_figures, figures_html
from .design_materials import material_catalog
from .aisc import check_stage, check_all_stages
from .report import build_report, report_xlsx

ROOT=Path(__file__).resolve().parents[2]
MAX_BODY=20*1024*1024


class Handler(BaseHTTPRequestHandler):
    def send(self,status,payload,content_type='application/json; charset=utf-8'):
        body=payload if isinstance(payload,bytes) else json.dumps(payload,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        path=urlsplit(self.path).path
        if path in ('/','/simulador.html'):
            return self.send(200,(ROOT/'simulador.html').read_bytes(),'text/html; charset=utf-8')
        if path in ('/simulator.js','/deformation.js','/reactions.js','/aisc-view.js'):
            return self.send(200,(ROOT/'src/domestage/static'/path.lstrip('/')).read_bytes(),'text/javascript; charset=utf-8')
        if path=='/api/design-materials': return self.send(200,material_catalog())
        if path=='/api/catalog': return self.send(200,catalog())
        if path=='/api/default-model': return self.send(200,default_model())
        if path=='/api/demo': return self.send(200,geometry_from_structure(generate_demo_dome(total_height=3.2)))
        self.send(404,{'message':'Ruta no disponible.'})

    def do_POST(self):
        # La aplicación es local y de mismo origen; no habilita CORS.
        origin=self.headers.get('Origin')
        if origin and urlsplit(origin).netloc!=self.headers.get('Host'):
            return self.send(403,{'message':'Origen no permitido.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=MAX_BODY: raise ValueError('Carga vacía o mayor que 20 MB.')
            body=self.rfile.read(length)
            url=urlsplit(self.path)
            if url.path=='/api/import':
                query=parse_qs(url.query)
                units=query.get('units',['auto'])[0]
                tolerance=float(query.get('tolerance',['0.000001'])[0])
                geometry,report=geometry_from_dxf(body,None if units=='auto' else units,tolerance)
                return self.send(200,dict(geometry=geometry,report=report))
            payload=json.loads(body,parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Número no finito.')))
            if not isinstance(payload,dict): raise ValueError('Se requiere un objeto JSON.')
            if url.path in ('/api/aisc','/api/aisc/progress'):
                cfg=payload.get('config') or {}
                if url.path=='/api/aisc/progress':
                    return self.send(200,check_all_stages(payload['geometry'],cfg,payload.get('design') or {}))
                return self.send(200,check_stage(payload['geometry'],cfg,payload.get('stage',0),payload.get('design') or {}))
            if url.path=='/api/plan':
                return self.send(200,stage_plan(payload['geometry'],payload.get('bars_per_step',2)))
            if url.path=='/api/progress':
                return self.send(200,progress_series(payload['geometry'],payload.get('config'),payload.get('design')))
            if url.path=='/api/utilization-figures':
                data=build_figures(payload['geometry'],payload.get('config'),payload.get('design'),payload.get('milestones'),payload.get('language','en'))
                return self.send(200,figures_html(data,payload.get('model_name') or '').encode('utf-8'),'text/html; charset=utf-8')
            if url.path=='/api/report':
                report=build_report(payload['geometry'],payload.get('config'),payload.get('design'))
                return self.send(200,report_xlsx(report,payload.get('language','en')),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            if url.path=='/api/stage':
                return self.send(200,solve_stage(payload['geometry'],payload.get('config'),payload.get('stage',0)))
            if url.path=='/api/stages/batch':
                cfg = payload.get('config')
                geo = payload['geometry']
                stages = payload.get('stages')
                if stages is None:
                    plan = stage_plan(geo, (cfg or {}).get('bars_per_step', 2))
                    stages = [s['stage'] for s in plan]
                return self.send(200, [solve_stage(geo, cfg, s) for s in stages])
            self.send(404,{'message':'Ruta no disponible.'})
        except (ValueError,KeyError,TypeError,OverflowError) as exc:
            self.send(400,{'message':str(exc)})


def main():
    parser=argparse.ArgumentParser(description='Simulador de montaje con motor estructural local')
    parser.add_argument('--port',type=int,default=8503)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Simulador: http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
