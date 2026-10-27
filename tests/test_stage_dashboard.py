from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'src/domestage/app.py'


def test_dashboard_switches_stability_and_recomputes_configuration():
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception
    assert at.session_state['visited'][0]['stable']
    at.slider(key='stage_idx').set_value(1).run()
    assert not at.exception
    assert at.session_state['visited'][1]['status']=='unstable'
    assert any('Etapa sin solución' in e.value for e in at.error)
    assert any(m.value=='—' for m in at.metric)
    # Al cambiar conexiones se invalida el historial y vuelve a etapa 0.
    next(r for r in at.radio if r.label=='Conexiones').set_value('empotrada').run()
    next(r for r in at.radio if r.label=='Apoyos').set_value('empotrado').run()
    at.slider(key='stage_idx').set_value(1).run()
    assert not at.exception
    assert at.session_state['visited'][1]['stable']
    assert at.session_state['visited'][1]['worker_load_N']>0
    next(s for s in at.selectbox if s.label=='Barras por etapa').select(4).run()
    assert at.session_state['stage_idx']==0
    assert list(at.session_state['visited'])==[0]


def test_deformation_preferences_do_not_change_stage_or_results():
    import json
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.checkbox(key='show_deformed').value
    next(r for r in at.radio if r.label=='Conexiones').set_value('empotrada').run()
    next(r for r in at.radio if r.label=='Apoyos').set_value('empotrado').run()
    at.slider(key='stage_idx').set_value(1).run()
    before=json.dumps(at.session_state['visited'][1],sort_keys=True)
    at.checkbox(key='show_deformed').check().run()
    at.number_input(key='deformation_scale').set_value(10.).run()
    assert not at.exception
    assert at.session_state['stage_idx']==1
    assert json.dumps(at.session_state['visited'][1],sort_keys=True)==before
    assert any('dibujado' in c.value for c in at.caption)
    at.checkbox(key='show_deformed').uncheck().run()
    assert at.number_input(key='deformation_scale').disabled
