"""Probar el contrato HTTP sin abrir puertos en las pruebas unitarias."""
import io
import json
from domestage.server import Handler
from test_assembly import tetrahedron,config


def post(path,payload,origin=None):
    body=json.dumps(payload).encode() if not isinstance(payload,bytes) else payload
    handler=object.__new__(Handler)
    handler.path=path;handler.headers={'Content-Length':str(len(body)),'Host':'127.0.0.1:8503'}
    if origin:handler.headers['Origin']=origin
    handler.rfile=io.BytesIO(body);output=[]
    handler.send=lambda status,result,*args:output.append((status,result))
    handler.do_POST()
    return output[0]


def test_http_stage_returns_solver_results_and_mechanisms():
    payload=dict(geometry=tetrahedron(),config=config(),stage=3)
    status,result=post('/api/stage',payload)
    assert status==200 and result['stable']
    assert result['elements'][0]['id']==101
    payload['stage']=1
    status,result=post('/api/stage',payload)
    assert status==200 and result['status']=='unstable'
    assert result['forces']=={} and result['max_compression_kn'] is None


def test_http_stages_batch_solves_multiple_stages():
    payload = dict(geometry=tetrahedron(), config=config(), stages=[1, 3])
    status, result = post('/api/stages/batch', payload)
    assert status == 200
    assert len(result) == 2
    assert result[0]['stage'] == 1 and result[0]['status'] == 'unstable'
    assert result[1]['stage'] == 3 and result[1]['stable']

    # Test batch without stages list computes all stages
    payload_all = dict(geometry=tetrahedron(), config=config())
    status_all, result_all = post('/api/stages/batch', payload_all)
    assert status_all == 200
    assert len(result_all) >= 3


def test_http_rejects_bad_json_invalid_input_and_foreign_origin():
    assert post('/api/stage',b'{invalid')[0]==400
    assert post('/api/plan',{'geometry':tetrahedron(),'bars_per_step':0})[0]==400
    assert post('/api/stage',{'geometry':tetrahedron()},origin='https://example.com')[0]==403
    assert post('/api/stage',b'{"stage": NaN}')[0]==400
