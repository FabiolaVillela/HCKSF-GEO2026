"""The local server must not read or write arbitrary files.

Regression tests for the frame-recording routes added in #26 (`/api/save-frame`, `/gifs/`,
`/docs/gifs/`, `/presentacion.html`): they wrote and served files from paths taken from the request,
so `../` could reach outside the repository. They were removed; these tests keep them out.
The tests are written so that, even against the vulnerable code, nothing is written outside
pytest's temporary directory.
"""
import shutil

import pytest

from domestage.server import ROOT, Handler
from test_server import post


def get(path):
    handler = object.__new__(Handler)
    handler.path = path
    output = []
    handler.send = lambda status, result, *args: output.append((status, result))
    handler.do_GET()
    return output[0]


@pytest.fixture
def gif_folders():
    """Create the folders the removed routes read from, so a traversal would actually work."""
    created = [d for d in (ROOT / 'gifs', ROOT / 'docs' / 'gifs') if not d.exists()]
    for d in created:
        d.mkdir(parents=True)
    yield
    for d in created:
        shutil.rmtree(d)


@pytest.mark.parametrize('path', ['/gifs/../README.md', '/docs/gifs/../../README.md', '/gifs/../src/domestage/server.py'])
def test_get_cannot_read_files_through_traversal(gif_folders, path):
    status, body = get(path)
    assert status == 404 and isinstance(body, dict)


@pytest.mark.parametrize('path', ['/presentacion.html', '/presentation.html', '/README.md', '/src/domestage/server.py'])
def test_get_does_not_serve_other_files(path):
    status, body = get(path)
    assert status == 404 and isinstance(body, dict)


def test_save_frame_endpoint_is_gone_and_writes_nothing(tmp_path):
    # Absolute folder inside pytest's tmp dir: even a vulnerable server could only write there.
    had_gifs = (ROOT / 'docs' / 'gifs').exists()
    payload = dict(folder=str(tmp_path), filename='frame.png', data='data:text/plain;base64,cHduZWQ=')
    status, _ = post('/api/save-frame', payload)
    assert status == 404
    assert not list(tmp_path.iterdir())
    assert (ROOT / 'docs' / 'gifs').exists() == had_gifs


def test_only_known_static_files_are_served():
    for path in ('/', '/simulador.html', '/simulator.js', '/deformation.js', '/reactions.js', '/aisc-view.js'):
        assert get(path)[0] == 200, path
