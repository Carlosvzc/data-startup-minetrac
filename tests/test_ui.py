from pathlib import Path
from datetime import date
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
def test_ui_real_filters_and_limits(monkeypatch):
 monkeypatch.setenv('MINETRAC_ALCANCE','flota')
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=45).run()
 assert not a.exception
 assert [m.value for m in a.metric][:4]==['257','$928,832','$12,384','26.8']
 assert len(a.metric)==12 and a.metric[4].value=='540'  # pestaña de la libreta
 assert len(a.get("plotly_chart"))==15
 assert a.date_input[0].value[0]==date(2023,8,4)
 assert a.checkbox(key='include_undated').value is True
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


def test_ui_alcance_solo_camiones():
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=45).run()
 assert not a.exception
 assert [m.value for m in a.metric][:4]==['257','$928,832','$12,384','26.8']
 assert len(a.metric)==8 and a.metric[6].value=='0.10'   # 4 tarjetas + 4 de la predicción (R² = 0.10)
 assert len(a.get("plotly_chart"))==11
 assert [t.label for t in a.tabs]==['Vista general','Alertas y reportes','Mantenimiento y refacciones','Ciclos','Flota y operación','Predicción','Calidad de datos','Explorar datos']
 a.multiselect(key='trucks').set_value(['C5']).run()
 assert not a.exception and a.metric[0].value=='57'


def test_ui_alertas_y_correo_sin_configurar(monkeypatch):
 for v in ['MINETRAC_CORREO_DE','MINETRAC_SMTP_HOST','MINETRAC_SMTP_USUARIO','MINETRAC_SMTP_CLAVE']:
  monkeypatch.delenv(v,raising=False)
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=60).run()
 assert not a.exception
 assert next(b for b in a.button if b.label=='Enviar resumen').disabled   # sin configuración no se puede enviar
 a.multiselect(key='alert_sev').set_value(['Alta']).run()
 assert not a.exception


def test_ui_acceso_privado(monkeypatch):
 import sys; sys.path.insert(0,str(ROOT/'services/tablero')); import acceso
 monkeypatch.setenv('MINETRAC_USUARIOS','carlos:'+acceso.hash_clave('clave-larga-123'))
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=60).run()
 assert not a.exception and len(a.metric)==0                      # sin sesión no se ve nada del tablero
 a.text_input(key='login_u').set_value('carlos'); a.text_input(key='login_c').set_value('mala'); a.run()
 next(b for b in a.button if b.label=='Entrar').click().run()
 assert len(a.metric)==0 and a.error
 a.text_input(key='login_c').set_value('clave-larga-123'); next(b for b in a.button if b.label=='Entrar').click().run()
 assert not a.exception and a.metric[0].value=='257'


def test_acceso_aws_sin_cuentas_no_abre(monkeypatch):
 monkeypatch.delenv('MINETRAC_USUARIOS',raising=False); monkeypatch.setenv('MINETRAC_STORAGE','s3')
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=60).run()
 assert len(a.metric)==0
