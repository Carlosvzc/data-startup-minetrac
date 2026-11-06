import numpy as np, pandas as pd
from analitica import ols_a_mano, comparar_con_sklearn, serie_semanal, adf, matriz_diseno


def test_ols_recupera_coeficientes_conocidos():
    rng = np.random.default_rng(1)
    X = np.column_stack([np.ones(200), rng.normal(size=200), rng.normal(size=200)])
    y = X @ np.array([2.0, -1.5, 0.7]) + rng.normal(scale=.01, size=200)
    o = ols_a_mano(X, y)
    assert np.allclose(o['beta'], [2.0, -1.5, 0.7], atol=.01) and o['r2'] > .999
    assert abs(o['media_residuos']) < 1e-9


def test_ols_coincide_con_sklearn_en_datos_reales():
    lib = pd.read_csv('data/clean/libreta_eventos.csv')
    X, y, _ = matriz_diseno(serie_semanal(lib))
    o = ols_a_mano(X, y)
    assert comparar_con_sklearn(X, y, o['beta'])['coinciden']


def test_serie_semanal_completa_y_suma():
    lib = pd.read_csv('data/clean/libreta_eventos.csv')
    s = serie_semanal(lib)
    assert len(s) == 132 and (s >= 0).all() and s.index.freqstr in ('W-MON', None) and s.sum() == 516


def test_adf_detecta_ruido_blanco_y_caminata():
    rng = np.random.default_rng(0)
    assert adf(pd.Series(rng.normal(size=300)))['estacionaria']
    assert not adf(pd.Series(np.cumsum(rng.normal(size=300))))['estacionaria']
