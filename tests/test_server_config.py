"""Server host/port configuration and the Render deployment files."""
import pytest

from domestage.server import DEFAULT_HOST, DEFAULT_PORT, ROOT, parse_args


def test_defaults_stay_local():
    args = parse_args([], env={})
    assert (args.host, args.port) == (DEFAULT_HOST, DEFAULT_PORT) == ('127.0.0.1', 8503)


def test_environment_variables_used_by_hosting_platforms():
    args = parse_args([], env={'PORT': '10000', 'HOST': '0.0.0.0'})
    assert (args.host, args.port) == ('0.0.0.0', 10000)


def test_command_line_overrides_environment():
    args = parse_args(['--host', '127.0.0.1', '--port', '8600'], env={'PORT': '10000', 'HOST': '0.0.0.0'})
    assert (args.host, args.port) == ('127.0.0.1', 8600)


@pytest.mark.parametrize('argv', [['--port', '0'], ['--port', '70000'], ['--port', 'abc']])
def test_invalid_port_is_rejected(argv):
    with pytest.raises(SystemExit):
        parse_args(argv, env={})


def test_render_blueprint_and_python_version():
    blueprint = (ROOT / 'render.yaml').read_text()
    assert 'type: web' in blueprint and 'runtime: python' in blueprint and 'branch: main' in blueprint
    assert 'buildCommand: pip install -r requirements.txt' in blueprint
    assert 'startCommand: PYTHONPATH=src python -m domestage.server --host 0.0.0.0 --port $PORT' in blueprint
    assert (ROOT / '.python-version').read_text().strip() == '3.12'
    assert (ROOT / 'docs' / 'DEPLOY_RENDER.md').exists()
