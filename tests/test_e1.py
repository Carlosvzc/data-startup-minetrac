from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/tablero'))
from core import resumen, serie_diaria, spectral, ciclo_cercano, recomendaciones  # noqa: E402
from figures import views  # noqa: E402

CLEAN = ROOT / 'data/clean/mantenimiento.csv'
necesita_datos = pytest.mark.skipif(not CLEAN.exists(), reason='Ejecuta primero: python scripts/pipeline_e1.py')


def _m():
    return pd.DataFrame({
        'evento_id': ['A-1', 'A-2', 'A-2', 'B-1'], 'camion_id': ['A', 'A', 'A', 'B'], 'fecha': ['2025-01-01', '2025-01-10', '2025-01-10', '2025-02-01'],
        'costo_mxn_intervencion': [1000, 500, 500, np.nan], 'costo_mxn': [1000, 250, 250, np.nan],
        'componente': ['Clutch', 'Clutch', 'Motor', 'Clutch'], 'reincidencia_30d': [False, True, False, False]})


def test_resumen_caso_conocido():
    r = resumen(_m())
    assert r['intervenciones'] == 3 and r['con_monto'] == 2 and r['gasto_mxn'] == 1500
    assert np.isclose(r['pct_con_monto'], 200 / 3) and r['promedio_mxn'] == 750 and r['reincidencias'] == 1


def test_serie_diaria_calendario_completo():
    s = serie_diaria(_m())
    assert len(s) == 32 and s.sum() == 3 and s.index.is_monotonic_increasing


def test_fft_recupera_ciclos_conocidos():
    idx = pd.date_range('2025-01-01', periods=420)
    s = pd.Series(10 + 2 * np.cos(2 * np.pi * np.arange(420) / 7) + np.cos(2 * np.pi * np.arange(420) / 15), index=idx)
    spec, p = spectral(s)
    assert abs(p[0]['periodo_dias'] - 7) < .2 and any(abs(x['periodo_dias'] - 15) < .6 for x in p[:3])
    assert ciclo_cercano(spec, 7)['veces_mediana'] > 5


def test_fft_rechaza_serie_corta_o_con_huecos():
    with pytest.raises(ValueError):
        spectral(pd.Series(1.0, index=pd.date_range('2025-01-01', periods=10)))
    with pytest.raises(ValueError):
        spectral(pd.Series(1.0, index=pd.date_range('2025-01-01', periods=60, freq='2D')))


@necesita_datos
def test_datos_reales_cuadran():
    m = pd.read_csv(CLEAN)
    assert not m.naturaleza_dato.ne('real').any()
    r = resumen(m)
    assert r['intervenciones'] == 257 and r['con_monto'] == 75 and r['gasto_mxn'] == 928832
    # El monto repartido entre sistemas suma el monto de la intervención.
    ev = m.drop_duplicates(['camion_id', 'evento_id'])
    assert np.isclose(m.costo_mxn.sum(), ev.costo_mxn_intervencion.sum())
    figs, aux = views(m)
    assert len(figs) == 6 and all(f is not None for _, f in figs)
    assert len(recomendaciones(m, aux)) == 3


@necesita_datos
def test_fecha_con_solo_anio_no_amplia_periodo_ni_ejes():
    from core import tiene_dia, rango_periodo, filtrar_periodo
    m = pd.read_csv(CLEAN)
    inicio, fin = rango_periodo(m)
    assert str(inicio) == '2023-08-04'
    seleccion = filtrar_periodo(m, inicio, fin)
    k = resumen(seleccion)
    assert k['intervenciones'] == 257 and k['con_monto'] == 75
    assert k['gasto_mxn'] == 928832 and k['intervenciones'] - k['con_monto'] == 182
    assert len(pd.read_csv(ROOT / 'data/clean/inventario.csv')) == 21
    figs, aux = views(seleccion)
    assert len(aux['eventos_con_dia']) == 256
    assert aux['por_mes'].index.min().year == 2023
    assert int(aux['por_mes'].sum()) == 256
    for trace in figs[2][1].data:
        assert all(pd.Timestamp(x).year >= 2023 for x in trace.x)
    unknown = m.loc[~tiene_dia(m)]
    assert resumen(unknown)['intervenciones'] == 1
    assert len(serie_diaria(unknown)) == 0


@necesita_datos
def test_seleccion_con_solo_anio_explica_la_falta_de_graficas_temporales():
    m = pd.read_csv(CLEAN)
    unknown = m[m.fecha_calidad.eq('solo_anio')]
    figs, aux = views(unknown)
    assert figs[2][1] is None and figs[3][1] is None and figs[5][1] is None
    assert aux['por_mes'].empty
