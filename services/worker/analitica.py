"""Análisis del E2: serie semanal de la libreta, descomposición, ADF, ACF/PACF y regresión lineal a mano.

La regresión usa la ecuación normal con NumPy puro (β = (XᵀX)⁻¹Xᵀy). scikit-learn solo se usa para comprobar
que el resultado coincide; no interviene en el cálculo.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from scipy import stats

INICIO_SERIE = '2024-04-01'     # primer lunes con anotaciones completas en la libreta
FIN_SERIE = '2026-10-05'        # último lunes de una semana completa (la libreta llega al 14 de octubre)


def serie_semanal(libreta: pd.DataFrame) -> pd.Series:
    """Anotaciones por semana (lunes a domingo). Las semanas sin anotaciones valen 0."""
    f = pd.to_datetime(libreta['fecha'], errors='coerce').dropna()
    f = f[(f >= INICIO_SERIE) & (f < pd.Timestamp(FIN_SERIE) + pd.Timedelta(days=7))]
    semana = f.dt.to_period('W-SUN').dt.start_time
    idx = pd.date_range(INICIO_SERIE, FIN_SERIE, freq='W-MON')
    return semana.value_counts().reindex(idx, fill_value=0).sort_index().astype(float).rename('anotaciones')


def descomponer(serie: pd.Series, periodo: int = 52) -> dict:
    """Descomposición aditiva clásica (tendencia, estacionalidad y residuo) con medias móviles centradas."""
    from statsmodels.tsa.seasonal import seasonal_decompose
    r = seasonal_decompose(serie, model='additive', period=periodo, two_sided=True)
    var = lambda x: float(np.nanvar(x))
    total = var(serie.values)
    return {'periodo': periodo, 'tendencia': r.trend, 'estacional': r.seasonal, 'residuo': r.resid,
            'fuerza_tendencia': float(max(0, 1 - var(r.resid) / var((r.trend + r.resid).dropna()))) if total else 0.0,
            'fuerza_estacional': float(max(0, 1 - var(r.resid) / var((r.seasonal + r.resid).dropna()))) if total else 0.0}


def adf(serie: pd.Series, alpha: float = 0.05) -> dict:
    """Prueba de Dickey-Fuller aumentada. H0: la serie tiene raíz unitaria (no es estacionaria)."""
    from statsmodels.tsa.stattools import adfuller
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        est, p, rezagos, n, crit, _ = adfuller(serie.dropna().values, autolag='AIC')
    return {'estadistico': float(est), 'p_valor': float(p), 'rezagos': int(rezagos), 'n': int(n),
            'criticos': {k: float(v) for k, v in crit.items()}, 'estacionaria': bool(p < alpha)}


def acf_pacf(serie: pd.Series, nlags: int = 26) -> dict:
    from statsmodels.tsa.stattools import acf, pacf
    x = serie.dropna().values
    n = len(x)
    return {'acf': acf(x, nlags=nlags, fft=False).tolist(), 'pacf': pacf(x, nlags=nlags, method='ywm').tolist(),
            'banda': float(1.96 / np.sqrt(n)), 'n': int(n)}


def matriz_diseno(serie: pd.Series) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """y = anotaciones de la semana. X = [1, tendencia (semanas), anotaciones de la semana anterior]."""
    y = serie.values[1:]
    t = np.arange(1, len(serie), dtype=float)
    rezago = serie.values[:-1]
    X = np.column_stack([np.ones_like(t), t, rezago])
    return X, y.astype(float), ['constante', 'tendencia (semanas)', 'anotaciones semana anterior']


def ols_a_mano(X: np.ndarray, y: np.ndarray) -> dict:
    """Mínimos cuadrados con la ecuación normal: β = (XᵀX)⁻¹ Xᵀ y. Sin scikit-learn."""
    XtX = X.T @ X
    beta = np.linalg.inv(XtX) @ (X.T @ y)
    ajustado = X @ beta
    res = y - ajustado
    n, k = X.shape
    sse = float(res @ res)
    sst = float(((y - y.mean()) ** 2).sum())
    s2 = sse / (n - k)
    ee = np.sqrt(np.diag(s2 * np.linalg.inv(XtX)))
    t = beta / ee
    p = 2 * (1 - stats.t.cdf(np.abs(t), df=n - k))
    dw = float((np.diff(res) ** 2).sum() / sse)
    sw = stats.shapiro(res)
    return {'beta': beta, 'error_estandar': ee, 't': t, 'p_valor': p, 'ajustado': ajustado, 'residuos': res,
            'r2': 1 - sse / sst, 'r2_ajustado': 1 - (sse / (n - k)) / (sst / (n - 1)), 'rmse': float(np.sqrt(sse / n)),
            'durbin_watson': dw, 'shapiro_p': float(sw.pvalue), 'n': int(n), 'k': int(k),
            'media_residuos': float(res.mean())}


def comparar_con_sklearn(X: np.ndarray, y: np.ndarray, beta: np.ndarray) -> dict:
    """Comprobación: los coeficientes a mano deben coincidir con scikit-learn (la constante ya viene en X)."""
    from sklearn.linear_model import LinearRegression
    m = LinearRegression(fit_intercept=False).fit(X, y)
    d = float(np.max(np.abs(m.coef_ - beta)))
    return {'sklearn_beta': m.coef_.tolist(), 'max_dif_abs': d, 'coinciden': bool(np.allclose(m.coef_, beta, atol=1e-9))}


def resultados_e2(libreta: pd.DataFrame) -> dict:
    """Todo el análisis del E2 en un diccionario serializable (lo consume el tablero)."""
    s = serie_semanal(libreta)
    dif = s.diff().dropna()
    dec = descomponer(s, 52)
    X, y, nombres = matriz_diseno(s)
    o = ols_a_mano(X, y)
    cmp = comparar_con_sklearn(X, y, o['beta'])
    fechas = [d.date().isoformat() for d in s.index]
    nn = lambda a: [None if pd.isna(v) else float(v) for v in a]
    return {
        'serie': {'fechas': fechas, 'valores': s.tolist(), 'semanas': len(s), 'total': int(s.sum()), 'semanas_en_cero': int((s == 0).sum())},
        'descomposicion': {'periodo': dec['periodo'], 'tendencia': nn(dec['tendencia']), 'estacional': nn(dec['estacional']),
                           'residuo': nn(dec['residuo']), 'fuerza_tendencia': dec['fuerza_tendencia'], 'fuerza_estacional': dec['fuerza_estacional']},
        'adf_serie': adf(s), 'adf_diferencia': adf(dif),
        'acf_pacf': acf_pacf(s), 'acf_pacf_diferencia': acf_pacf(dif),
        'regresion': {'variables': nombres, 'beta': o['beta'].tolist(), 'error_estandar': o['error_estandar'].tolist(),
                      't': o['t'].tolist(), 'p_valor': o['p_valor'].tolist(), 'r2': o['r2'], 'r2_ajustado': o['r2_ajustado'],
                      'rmse': o['rmse'], 'durbin_watson': o['durbin_watson'], 'shapiro_p': o['shapiro_p'], 'n': o['n'],
                      'media_residuos': o['media_residuos'], 'fechas': fechas[1:], 'real': y.tolist(),
                      'ajustado': o['ajustado'].tolist(), 'residuos': o['residuos'].tolist(), 'acf_residuos': acf_pacf(pd.Series(o['residuos']), 20)['acf']},
        'comparacion_sklearn': cmp,
    }
