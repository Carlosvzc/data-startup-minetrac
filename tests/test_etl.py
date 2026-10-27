from pathlib import Path
import datetime as dt
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/worker'))
import etl_bitacora as e  # noqa: E402


def test_fechas_escritas_a_mano():
    assert dt.date(2026, 9, 7) in e.candidatos_fecha_texto('077sep/26')
    assert dt.date(2025, 9, 1) in e.candidatos_fecha_texto('01/se/25')
    assert dt.date(2025, 6, 11) in e.candidatos_fecha_texto('11/jun/265')
    assert dt.date(2026, 6, 10) in e.candidatos_fecha_texto('10/ju/')
    assert e.candidatos_fecha_texto('Revisar bovinas') == []


def _fila(raw):
    return {'fecha_raw': raw}


def test_resolver_fechas_corrige_anio_equivocado():
    filas = [_fila(dt.datetime(2025, 5, 6)), _fila(dt.datetime(2026, 6, 18)),   # año equivocado
             _fila(dt.datetime(2025, 7, 7)), _fila(dt.datetime(2025, 7, 20))]
    r = e.resolver_fechas(filas)
    assert r[1]['fecha'] == dt.date(2025, 6, 18) and r[1]['fecha_calidad'] == 'anio_corregido'


def test_resolver_fechas_futura_texto_sin_fecha_y_solo_anio():
    filas = [_fila(dt.datetime(2026, 5, 20)), _fila(dt.datetime(2026, 5, 27)),
             _fila(dt.datetime(2029, 5, 29)),                                    # fecha futura imposible
             _fila(None), _fila(dt.datetime(2026, 6, 10)), _fila('10/ju/'), _fila(dt.datetime(2026, 6, 17)), _fila(2022)]
    r = e.resolver_fechas(filas)
    assert r[2]['fecha'] == dt.date(2026, 5, 29) and r[2]['fecha_calidad'] == 'anio_corregido'
    assert r[3]['fecha'] == r[2]['fecha'] and r[3]['fecha_calidad'] == 'imputada_fila_anterior'
    assert r[5]['fecha'] == dt.date(2026, 6, 10) and r[5]['fecha_calidad'] == 'texto_interpretado'
    assert r[7]['fecha'] == dt.date(2022, 1, 1) and r[7]['fecha_calidad'] == 'solo_anio'


def test_costos_en_texto():
    assert e.costo_desde_texto(['cabeza del compresor se cambia $2500 (jimenez)']) == 2500
    assert e.costo_desde_texto(['Se repara clutch $20,000 reparado']) == 20000
    assert e.costo_desde_texto(['$100 y $200']) is None      # ambiguo: no se inventa
    assert e.costo_desde_texto(['sin monto']) is None


def test_clasificacion():
    assert e.clasificar_componente('Clutch reparado') == 'Clutch'
    assert e.clasificar_componente('Fan clutch nuevo') == 'Fan clutch (ventilador)'
    assert e.clasificar_componente('Se cambian 2 bolsas') == 'Muelles y bolsas de aire'
    assert e.clasificar_componente('texto sin pista', 'Llantas') == 'Llantas y rines'
    assert e.clasificar_condicion('Alternador reparado') == 'reparada'
    assert e.clasificar_condicion('Compresor nuevo') == 'nueva'
    assert e.clasificar_condicion('Servicio') == 'no_especificada'


LIBRO = next((ROOT / 'data/raw').glob('CAMIONES*.xlsx'), None)


@pytest.mark.skipif(LIBRO is None, reason='Coloca CAMIONES 12M3 Y 14M3.xlsx en data/raw/')
def test_libro_real():
    import openpyxl
    df, a, mapa = e.procesar_libro(openpyxl.load_workbook(LIBRO, data_only=True))
    assert a['intervenciones'] == 257 and a['registros_clean'] == 317
    assert df.camion_id.nunique() == 7
    assert df.drop_duplicates(['camion_id', 'evento_id']).costo_mxn_intervencion.sum() == pytest.approx(928832)
    assert df.costo_mxn.sum() == pytest.approx(928832)             # el reparto entre sistemas conserva el total
    assert a['atipicos'] == 1 and df.loc[df.atipico, 'costo_mxn_intervencion'].iloc[0] == 149000
    assert (df.fecha.str[:4].astype(int) <= 2026).all()
    assert not any(k in ' '.join(df.columns) for k in ('descripcion', 'comentario'))  # sin texto libre
