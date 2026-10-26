
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/tablero'))
from core import clean_data,metrics,spectral
def test_clean_reconciles():
 raw=pd.read_csv(ROOT/'data/raw/operacion_simulada_raw.csv');d,a=clean_data(raw)
 assert a=={'filas_raw':8850,'filas_clean':8820,'duplicados':30,'formato':25,'nulos':40,'negativos':15,'atipicos':10}
 assert not d.duplicated(['equipo_id','fecha']).any()
 assert d.horas_trabajadas_h.notna().all()
 assert d.horas_trabajadas_h.ge(0).all()
 assert d.horas_trabajadas_h.le(d.horas_programadas_h-d.horas_paro_h).all()
 assert d.equipo_id.eq(d.equipo_id.str.strip().str.upper()).all()
 assert np.allclose(d.ingreso_mxn-d.costo_operativo_mxn-d.costo_mantenimiento_mxn,d.margen_directo_mxn)
def test_kpi_small_known_case():
 d=pd.DataFrame({'ingreso_mxn':[1000,2000],'margen_directo_mxn':[400,600],'horas_trabajadas_h':[2,8],'horas_programadas_h':[10,10],'horas_paro_h':[1,3],'costo_mantenimiento_mxn':[100,200]})
 m=metrics(d)
 assert m['ingresos_mxn']==3000 and np.isclose(m['margen_directo_pct'],100/3)
 assert m['mantenimiento_mxn_h']==30 and m['disponibilidad_pct']==80
def test_fft_known_cycles():
 d=pd.DataFrame({'fecha':pd.date_range('2025-01-01',periods=420).strftime('%Y-%m-%d'),'horas_trabajadas_h':10+2*np.cos(2*np.pi*np.arange(420)/7)+np.cos(2*np.pi*np.arange(420)/15)})
 _,p=spectral(d);assert np.isclose(p[0]['periodo_dias'],7) and np.isclose(p[1]['periodo_dias'],15)
def test_ui():
 from streamlit.testing.v1 import AppTest
 a=AppTest.from_file(str(ROOT/'services/tablero/app.py'),default_timeout=40).run()
 assert not a.exception
 assert len(a.metric)==4 and len(a.get('plotly_chart'))==6
 # Filtering must recompute metrics and charts.
 a.multiselect[0].set_value(['Camión']).run()
 assert not a.exception and len(a.get('plotly_chart'))==6
 a.multiselect[0].set_value([]).run()
 assert not a.exception and len(a.metric)==0

