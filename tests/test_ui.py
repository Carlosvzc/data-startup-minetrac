from pathlib import Path
from datetime import date
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
def test_ui_real_filters_and_limits():
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=45).run()
 assert not a.exception
 assert [m.value for m in a.metric][:4]==['257','$928,832','$12,384','26.8']
 assert len(a.metric)==8 and a.metric[4].value=='540'  # pestaña de la libreta
 assert len(a.get('plotly_chart'))==10
 assert a.date_input[0].value[0]==date(2023,8,4)
 assert a.checkbox[0].value is True
 a.multiselect(key='trucks').set_value(['C5']).run()
 assert not a.exception and a.metric[0].value=='57'
 a.date_input[0].set_value((date(2026,10,1),date(2026,10,14))).run()
 assert not a.exception
 a.multiselect(key='trucks').set_value(['C2']).run()
 assert not a.exception
 next(b for b in a.button if b.label=='Restablecer filtros').click().run()
 assert not a.exception and a.metric[0].value=='257'
 # la pestaña de la libreta no depende de los filtros de camiones y se puede filtrar por equipo
 a.multiselect(key='lib_equipos').set_value(['K8']).run()
 assert not a.exception and a.metric[4].value=='53'
