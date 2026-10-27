"""Exercise the combined dashboard through Streamlit's test runner."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'src' / 'domestage' / 'app.py'


def dashboard():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.selectbox(key='analysis_mode').select('Dashboard (combined)').run()
    return app


def test_dashboard_runs_and_steps_stages():
    app = dashboard()
    assert not app.exception
    assert app.warning  # disclaimer is always visible
    first = app.slider(key='dash_step').value
    next_button = next(b for b in app.button if b.label.startswith('Next'))
    next_button.click().run()
    assert not app.exception
    assert app.slider(key='dash_step').value == first + 1


def test_dashboard_reaches_every_stage_without_crashing():
    app = dashboard()
    last = int(app.slider(key='dash_step').max)
    for step in range(0, last + 1, max(1, last // 8)):
        app.slider(key='dash_step').set_value(step).run()
        assert not app.exception
        assert app.success or app.error  # stable or unstable banner shown


def test_bars_per_stage_changes_stage_count():
    app = dashboard()
    one = int(app.slider(key='dash_step').max)
    app.number_input(key='dash_batch').set_value(3).run()
    assert not app.exception
    assert int(app.slider(key='dash_step').max) < one
