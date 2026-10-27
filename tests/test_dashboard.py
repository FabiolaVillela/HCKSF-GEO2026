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


def press_play(app):
    app.button(key='dash_play_button').click().run()


def test_play_advances_one_stage_per_run_and_pause_stops_it():
    app = dashboard()
    assert app.session_state['dash_step'] == 0 and not app.session_state['dash_playing']
    assert app.button(key='dash_play_button').label == '▶ Play'
    press_play(app)
    assert not app.exception and app.session_state['dash_playing']
    assert app.button(key='dash_play_button').label == '⏸ Pause'
    start = app.session_state['dash_step']
    assert start == 1  # pressing Play already shows the next stage
    for tick in range(1, 4):  # each timer tick is one more run of the stage view
        app.run()
        assert app.session_state['dash_step'] == start + tick
    press_play(app)  # the same button now pauses
    paused = app.session_state['dash_step']
    assert not app.session_state['dash_playing']
    app.run()
    assert app.session_state['dash_step'] == paused and not app.exception


def test_play_stops_at_the_last_stage_and_replays_from_the_start():
    app = dashboard()
    last = int(app.slider(key='dash_step').max)
    app.slider(key='dash_step').set_value(last - 2).run()
    press_play(app)
    for _ in range(5):
        app.run()
    assert app.session_state['dash_step'] == last and not app.session_state['dash_playing']
    assert not app.exception and app.button(key='dash_play_button').label == '▶ Play'
    press_play(app)  # at the end, Play starts over
    assert app.session_state['dash_playing'] and app.session_state['dash_step'] == 1


def test_changing_speed_does_not_start_or_move_playback():
    app = dashboard()
    app.select_slider(key='dash_speed').set_value('4×').run()
    assert not app.exception
    assert not app.session_state['dash_playing'] and app.session_state['dash_step'] == 0
    press_play(app)
    assert app.session_state['dash_playing'] and not app.exception


def test_playing_through_an_unstable_stage_does_not_crash():
    app = dashboard()
    press_play(app)
    seen_unstable = False
    for _ in range(12):
        app.run()
        assert not app.exception
        seen_unstable |= bool(app.error)
    assert seen_unstable  # the default dome has unstable early stages; playback just shows them
