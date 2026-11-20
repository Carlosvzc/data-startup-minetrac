import warnings
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from services.modelos import modelos as m
from services.modelos.main import app

warnings.filterwarnings('ignore')
cli = TestClient(app)


def serie_sintetica(n=80, seed=0):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.poisson(2, n).astype(float), index=pd.date_range('2025-01-06', periods=n, freq='W-MON'))


def test_pronostico_tiene_banda_ordenada_y_sin_negativos():
    df = m.pronosticar(serie_sintetica(), 4)
    assert len(df) == 4 and (df.inferior <= df.pronostico).all() and (df.pronostico <= df.superior).all() and (df.inferior >= 0).all()


def test_pronostico_banda_mas_ancha_con_mayor_nivel():
    s = serie_sintetica()
    a, b = m.pronosticar(s, 4, 0.8), m.pronosticar(s, 4, 0.95)
    assert ((b.superior - b.inferior) > (a.superior - a.inferior)).all()


def test_pronostico_rechaza_horizonte_y_nivel_invalidos():
    with pytest.raises(ValueError):
        m.pronosticar(serie_sintetica(), 0)
    with pytest.raises(ValueError):
        m.pronosticar(serie_sintetica(), 4, 1.2)


def test_busqueda_arima_ordena_por_aic():
    t = m.buscar_arima(serie_sintetica(), p_max=1, q_max=1)
    assert t.aic.is_monotonic_increasing and {'p', 'd', 'q', 'bic', 'ljung_box_p'} <= set(t.columns)


def test_evaluar_usa_corte_temporal_sin_mezclar_futuro():
    rng = np.random.default_rng(1)
    n = 120
    d = pd.DataFrame({'fecha': pd.date_range('2025-01-01', periods=n, freq='3D'), 'mes': rng.integers(1, 13, n), 'dia_semana': rng.integers(0, 7, n),
                      'dias_desde_previo_equipo': rng.integers(1, 60, n).astype(float), 'registros_previos_90d': rng.integers(0, 9, n),
                      'previos_mismo_sistema_90d': rng.integers(0, 4, n), 'pieza_declarada': 0, 'proveedor_declarado': 0,
                      'sistema': rng.choice(m.SISTEMAS, n), m.OBJETIVO: rng.integers(0, 2, n)})
    r = m.evaluar(d)
    assert r['n_entrenamiento'] + r['n_prueba'] == n
    assert r['periodo_entrenamiento'][1] <= r['periodo_prueba'][0]
    assert {'Naive Bayes', 'KNN (k=7)', 'SVM (núcleo RBF)'} <= set(r['modelos'])
    for v in r['modelos'].values():
        assert np.array(v['matriz_confusion']).sum() == r['n_prueba'] and 0 <= v['f1'] <= 1


def test_api_salud():
    r = cli.get('/salud')
    assert r.status_code == 200 and r.json()['estado'] == 'ok'


@pytest.mark.parametrize('dias,semanas', [(7, 1), (30, 4)])
def test_api_pronostico_7_y_30_dias(dias, semanas):
    r = cli.post('/pronostico', json={'horizonte_dias': dias})
    assert r.status_code == 200
    j = r.json()
    assert j['semanas'] == semanas and len(j['pronostico']) == semanas and j['nivel'] == 0.95
    assert all(f['inferior'] <= f['pronostico'] <= f['superior'] for f in j['pronostico'])


def test_api_pronostico_rechaza_horizonte_largo():
    assert cli.post('/pronostico', json={'horizonte_dias': 200}).status_code == 422


def test_api_clasificar():
    cuerpo = {'sistema': 'motor', 'mes': 3, 'dia_semana': 2, 'dias_desde_previo_equipo': 12, 'registros_previos_90d': 4, 'previos_mismo_sistema_90d': 1}
    r = cli.post('/clasificar', json=cuerpo)
    assert r.status_code == 200 and 0 <= r.json()['probabilidad'] <= 1 and isinstance(r.json()['repite_30d'], bool)


def test_api_clasificar_acepta_primer_registro_sin_dias_previos():
    cuerpo = {'sistema': 'llantas', 'mes': 1, 'dia_semana': 0}
    assert cli.post('/clasificar', json=cuerpo).status_code == 200


@pytest.mark.parametrize('cambio', [{'sistema': 'otro'}, {'mes': 13}, {'dia_semana': 9}, {'registros_previos_90d': -1}])
def test_api_clasificar_valida_entradas(cambio):
    base = {'sistema': 'motor', 'mes': 3, 'dia_semana': 2}
    assert cli.post('/clasificar', json={**base, **cambio}).status_code == 422


def test_naive_bayes_exportado_coincide_con_scikit_learn():
    import joblib, json
    from services.modelos.main import ARTEFACTOS
    pipe = joblib.load(ARTEFACTOS / 'clasificador.joblib')
    par = json.loads((ARTEFACTOS / 'naive_bayes.json').read_text())
    casos = [{'sistema': s, 'mes': mes, 'dia_semana': dia, 'dias_desde_previo_equipo': dd, 'registros_previos_90d': r, 'previos_mismo_sistema_90d': ps,
              'pieza_declarada': 0, 'proveedor_declarado': 0}
             for s in m.SISTEMAS for mes, dia, dd, r, ps in [(1, 0, None, 0, 0), (6, 3, 12.0, 4, 1), (11, 5, 300.0, 9, 3)]]
    for c in casos:
        esperado = float(pipe.predict_proba(pd.DataFrame([c])[m.NUMERICAS + m.CATEGORICAS])[0, 1])
        assert abs(m.probabilidad_naive_bayes(par, c) - esperado) < 1e-9


def test_funcion_serverless_coincide_con_la_api(tmp_path, monkeypatch):
    import importlib.util, json, shutil
    from services.modelos.main import ARTEFACTOS
    shutil.copy(ARTEFACTOS / 'naive_bayes.json', tmp_path / 'naive_bayes.json')
    monkeypatch.setenv('LAMBDA_TASK_ROOT', str(tmp_path))
    spec = importlib.util.spec_from_file_location('handler', 'infra/serverless/handler.py')
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    cuerpo = {'sistema': 'motor', 'mes': 3, 'dia_semana': 2, 'dias_desde_previo_equipo': 12, 'registros_previos_90d': 4, 'previos_mismo_sistema_90d': 1}
    lam = json.loads(h.lambda_handler({'body': json.dumps(cuerpo)}, None)['body'])
    api = cli.post('/clasificar', json=cuerpo).json()
    assert abs(lam['probabilidad'] - api['probabilidad']) < 1e-4 and lam['repite_30d'] == api['repite_30d']
    assert h.lambda_handler({'body': json.dumps({**cuerpo, 'sistema': 'x'})}, None)['statusCode'] == 422


def test_pronostico_con_ajuste_precalculado_da_lo_mismo():
    s = serie_sintetica()
    a = m.pronosticar(s, 4)
    b = m.pronosticar(s, 4, ajuste=m.ajustar_arima(s))
    pd.testing.assert_frame_equal(a, b)
