"""Exercise real calculations through the Streamlit form."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'src' / 'domestage' / 'app.py'


def test_frame_demo_form_and_invalid_section():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert [metric.value for metric in app.metric[:2]] == ['49', '128']
    assert len(app.dataframe[0].value) == 128
    assert len(app.dataframe[1].value) == 49
    baseline = app.session_state['frame_result']['summary']['max_displacement_m']

    app.number_input[2].set_value(100.0)
    app.button[0].click().run()
    assert not app.exception
    changed = app.session_state['frame_result']['summary']['max_displacement_m']
    assert changed == pytest.approx(2 * baseline)

    app.slider[0].set_value(1000).run()
    assert not app.exception
    assert app.session_state['frame_result']['summary']['max_displacement_m'] == changed

    app.number_input[1].set_value(60.0)
    app.button[0].click().run()
    assert not app.exception
    assert len(app.error) == 1
    assert not app.metric  # An invalid submission must not show old results.

    app.number_input[1].set_value(3.175)
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 4
