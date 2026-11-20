"""Modelos del E3: pronóstico ARIMA de las intervenciones semanales y clasificador de repetición de fallas.

El pronóstico usa la serie semanal de los 7 camiones (la misma del E2). El clasificador usa el dataset del Avance 1:
cada fila es un registro de mantenimiento y la variable objetivo `repite_30d` indica si el mismo sistema del mismo camión
vuelve a registrarse entre 1 y 30 días después.
"""
from __future__ import annotations
import itertools
import warnings
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- pronóstico (ARIMA)
ORDEN_ARIMA = (0, 1, 1)          # elegido por AIC, BIC y diagnóstico de residuos (ver docs/E3-modelos.md)
SEMANAS_7D, SEMANAS_30D = 1, 4   # 7 y 30 días sobre una serie semanal (30 días ≈ 4.3 semanas)


def buscar_arima(serie: pd.Series, p_max: int = 3, q_max: int = 3, d_opciones=(0, 1)) -> pd.DataFrame:
    """Prueba una rejilla de (p, d, q) y devuelve AIC, BIC y la prueba de Ljung-Box de los residuos."""
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.stats.diagnostic import acorr_ljungbox
    filas = []
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for p, d, q in itertools.product(range(p_max + 1), d_opciones, range(q_max + 1)):
            try:
                m = ARIMA(serie, order=(p, d, q), trend='c' if d == 0 else 'n').fit()
                lb = float(acorr_ljungbox(m.resid, lags=[10]).iloc[0, 1])
                filas.append({'p': p, 'd': d, 'q': q, 'aic': float(m.aic), 'bic': float(m.bic), 'ljung_box_p': lb,
                              'converge': bool(m.mle_retvals.get('converged', True))})
            except Exception:
                continue
    return pd.DataFrame(filas).sort_values('aic').reset_index(drop=True)


def ajustar_arima(serie: pd.Series, orden=ORDEN_ARIMA):
    from statsmodels.tsa.arima.model import ARIMA
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return ARIMA(serie, order=orden, trend='c' if orden[1] == 0 else 'n').fit()


def pronosticar(serie: pd.Series, semanas: int, nivel: float = 0.95, orden=ORDEN_ARIMA, ajuste=None) -> pd.DataFrame:
    """Pronóstico de intervenciones por semana con banda de confianza. Los conteos no pueden ser negativos."""
    if not 1 <= semanas <= 12:
        raise ValueError('semanas debe estar entre 1 y 12')
    if not 0.5 <= nivel < 1:
        raise ValueError('nivel debe estar entre 0.5 y 1')
    res = ajuste if ajuste is not None else ajustar_arima(serie, orden)   # la API pasa el ajuste ya hecho
    f = res.get_forecast(semanas)
    ic = f.conf_int(alpha=1 - nivel)
    fechas = pd.date_range(serie.index[-1] + pd.Timedelta(days=7), periods=semanas, freq='W-MON')
    return pd.DataFrame({'semana': [d.date().isoformat() for d in fechas], 'pronostico': np.clip(f.predicted_mean.values, 0, None),
                         'inferior': np.clip(ic.iloc[:, 0].values, 0, None), 'superior': np.clip(ic.iloc[:, 1].values, 0, None)})


def validar_arima(serie: pd.Series, semanas_prueba: int = 12, orden=ORDEN_ARIMA) -> dict:
    """Prueba sencilla: se ajusta con todo menos las últimas semanas y se predice hacia adelante.
    Se compara con un modelo ingenuo (repetir el promedio de las últimas 4 semanas). Es una revisión de sensatez,
    no el backtesting completo, que corresponde al E4."""
    entrena, prueba = serie.iloc[:-semanas_prueba], serie.iloc[-semanas_prueba:]
    pred = pronosticar(entrena, semanas_prueba, 0.95, orden)
    p = pred['pronostico'].values
    ingenuo = np.full(semanas_prueba, entrena.iloc[-4:].mean())
    mae = lambda a, b: float(np.mean(np.abs(a - b)))
    cobertura = float(np.mean((prueba.values >= pred['inferior'].values) & (prueba.values <= pred['superior'].values)))
    return {'semanas_prueba': semanas_prueba, 'mae_arima': mae(prueba.values, p), 'mae_ingenuo': mae(prueba.values, ingenuo),
            'cobertura_95': cobertura}


# ---------------------------------------------------------------- clasificador
NUMERICAS = ['mes', 'dia_semana', 'dias_desde_previo_equipo', 'registros_previos_90d', 'previos_mismo_sistema_90d',
             'pieza_declarada', 'proveedor_declarado']
CATEGORICAS = ['sistema']
SISTEMAS = ['motor', 'tren_motriz_frenos', 'electrico_ac', 'estructura_cabina', 'llantas']   # los sistemas con objetivo
OBJETIVO = 'repite_30d'


def cargar_dataset(ruta) -> pd.DataFrame:
    d = pd.read_csv(ruta, parse_dates=['fecha'])
    d = d.dropna(subset=[OBJETIVO, 'fecha']).sort_values('fecha').reset_index(drop=True)
    d[OBJETIVO] = d[OBJETIVO].astype(int)
    return d


def _preproceso():
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    num = Pipeline([('imputar', SimpleImputer(strategy='median')), ('escalar', StandardScaler())])
    cat = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    return ColumnTransformer([('num', num, NUMERICAS), ('cat', cat, CATEGORICAS)])


def candidatos() -> dict:
    from sklearn.dummy import DummyClassifier
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier
    modelos = {
        'Referencia: clase más frecuente': DummyClassifier(strategy='most_frequent'),
        'Referencia: siempre "repite"': DummyClassifier(strategy='constant', constant=1),
        'Naive Bayes': GaussianNB(),
        'KNN (k=7)': KNeighborsClassifier(n_neighbors=7),
        'SVM (núcleo RBF)': SVC(kernel='rbf', C=1.0, probability=True, random_state=0),
        'Árbol de decisión (profundidad 3)': DecisionTreeClassifier(max_depth=3, min_samples_leaf=10, random_state=0),
    }
    return {n: Pipeline([('prep', _preproceso()), ('modelo', m)]) for n, m in modelos.items()}


def evaluar(df: pd.DataFrame, prop_prueba: float = 0.2) -> dict:
    """Corte temporal: se entrena con lo más antiguo y se prueba con lo más reciente (así no se usa el futuro).
    Además se reporta una validación cruzada temporal (TimeSeriesSplit) sobre el conjunto de entrenamiento."""
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    n_ent = int(len(df) * (1 - prop_prueba))
    ent, prueba = df.iloc[:n_ent], df.iloc[n_ent:]
    X_e, y_e, X_p, y_p = ent[NUMERICAS + CATEGORICAS], ent[OBJETIVO], prueba[NUMERICAS + CATEGORICAS], prueba[OBJETIVO]
    resultados = {}
    for nombre, pipe in candidatos().items():
        cv = cross_val_score(pipe, X_e, y_e, cv=TimeSeriesSplit(n_splits=5), scoring='f1')
        pipe.fit(X_e, y_e)
        pred = pipe.predict(X_p)
        prob = pipe.predict_proba(X_p)[:, 1]
        tn, fp, fn, tp = confusion_matrix(y_p, pred, labels=[0, 1]).ravel()
        resultados[nombre] = {'accuracy': float(accuracy_score(y_p, pred)), 'precision': float(precision_score(y_p, pred, zero_division=0)),
                              'recall': float(recall_score(y_p, pred, zero_division=0)), 'f1': float(f1_score(y_p, pred, zero_division=0)),
                              'auc': float(roc_auc_score(y_p, prob)) if len(set(prob)) > 1 else 0.5,
                              'f1_cv_media': float(cv.mean()), 'f1_cv_desv': float(cv.std()),
                              'matriz_confusion': [[int(tn), int(fp)], [int(fn), int(tp)]]}
    return {'n_total': int(len(df)), 'n_entrenamiento': int(len(ent)), 'n_prueba': int(len(prueba)),
            'periodo_entrenamiento': [str(ent.fecha.min().date()), str(ent.fecha.max().date())],
            'periodo_prueba': [str(prueba.fecha.min().date()), str(prueba.fecha.max().date())],
            'positivos_entrenamiento': float(y_e.mean()), 'positivos_prueba': float(y_p.mean()), 'modelos': resultados}


def entrenar_final(df: pd.DataFrame, nombre: str):
    """Entrena el modelo elegido con todos los registros con objetivo conocido."""
    pipe = candidatos()[nombre]
    pipe.fit(df[NUMERICAS + CATEGORICAS], df[OBJETIVO])
    return pipe


# ---------------------------------------------------------------- exportar Naive Bayes (para la función serverless)
def exportar_naive_bayes(pipe) -> dict:
    """Guarda en un diccionario todo lo necesario para clasificar sin scikit-learn: imputación por mediana, escalado,
    codificación del sistema y los parámetros del Naive Bayes gaussiano (medias, varianzas y probabilidades previas)."""
    prep, nb = pipe.named_steps['prep'], pipe.named_steps['modelo']
    num = prep.named_transformers_['num']
    return {'numericas': NUMERICAS, 'sistemas': [str(c) for c in prep.named_transformers_['cat'].categories_[0]],
            'mediana': num.named_steps['imputar'].statistics_.tolist(), 'media': num.named_steps['escalar'].mean_.tolist(),
            'escala': num.named_steps['escalar'].scale_.tolist(), 'clases': [int(c) for c in nb.classes_],
            'previa': nb.class_prior_.tolist(), 'theta': nb.theta_.tolist(), 'var': nb.var_.tolist()}


def probabilidad_naive_bayes(par: dict, fila: dict) -> float:
    """Misma cuenta que scikit-learn, en Python puro: log P(clase) + suma de log-verosimilitudes gaussianas."""
    import math
    x = []
    for k, (med, mu, sd) in enumerate(zip(par['mediana'], par['media'], par['escala'])):
        v = fila.get(par['numericas'][k])
        v = med if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
        x.append((v - mu) / sd)
    x += [1.0 if fila['sistema'] == s else 0.0 for s in par['sistemas']]
    logs = []
    for c in range(len(par['clases'])):
        lp = math.log(par['previa'][c])
        for j, xj in enumerate(x):
            var = par['var'][c][j]
            lp += -0.5 * math.log(2 * math.pi * var) - (xj - par['theta'][c][j]) ** 2 / (2 * var)
        logs.append(lp)
    mx = max(logs)
    e = [math.exp(l - mx) for l in logs]
    return e[par['clases'].index(1)] / sum(e)
