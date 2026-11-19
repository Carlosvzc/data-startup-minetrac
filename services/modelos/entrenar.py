"""Entrena los modelos del E3 y guarda los artefactos que usa la API (services/modelos/artefactos/).

Uso:  python -m services.modelos.entrenar
No se guarda texto libre ni nombres: solo la serie semanal de conteos, el clasificador entrenado y las métricas.
"""
from __future__ import annotations
import json
from pathlib import Path
import joblib
import pandas as pd
from services.worker.analitica import serie_semanal
from services.modelos import modelos as m

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent / 'artefactos'


def main() -> dict:
    SALIDA.mkdir(exist_ok=True)
    bitacora = pd.read_csv(RAIZ / 'data/clean/mantenimiento.csv', encoding='utf-8-sig')
    serie = serie_semanal(bitacora)
    serie.rename_axis('semana').to_csv(SALIDA / 'serie_semanal.csv')

    busqueda = m.buscar_arima(serie)
    busqueda.to_csv(SALIDA / 'seleccion_arima.csv', index=False)
    ajuste = m.ajustar_arima(serie)
    arima = {'orden': list(m.ORDEN_ARIMA), 'aic': float(ajuste.aic), 'bic': float(ajuste.bic), 'sigma2': float(ajuste.params['sigma2']),
             'theta1': float(ajuste.params['ma.L1']), 'validacion': m.validar_arima(serie),
             'pronostico_7d': m.pronosticar(serie, m.SEMANAS_7D).round(3).to_dict('records'),
             'pronostico_30d': m.pronosticar(serie, m.SEMANAS_30D).round(3).to_dict('records')}

    df = m.cargar_dataset(RAIZ / 'data/clean/dataset_avance1.csv')
    clasif = m.evaluar(df)
    reales = {k: v for k, v in clasif['modelos'].items() if not k.startswith('Referencia')}
    mejor = max(reales, key=lambda k: reales[k]['f1_cv_media'])
    clasif['modelo_elegido'] = mejor
    clasif['criterio'] = 'mayor F1 medio en validación cruzada temporal del conjunto de entrenamiento'
    final = m.entrenar_final(df, mejor)
    joblib.dump(final, SALIDA / 'clasificador.joblib')
    if mejor == 'Naive Bayes':
        (SALIDA / 'naive_bayes.json').write_text(json.dumps(m.exportar_naive_bayes(final)), encoding='utf-8')

    out = {'arima': arima, 'clasificador': clasif, 'busqueda_arima': busqueda.head(8).round(4).to_dict('records')}
    (SALIDA / 'metricas_e3.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


if __name__ == '__main__':
    r = main()
    print('ARIMA', r['arima']['orden'], 'AIC', round(r['arima']['aic'], 1), '| clasificador elegido:', r['clasificador']['modelo_elegido'])
