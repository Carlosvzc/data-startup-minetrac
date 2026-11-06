"""Pruebas de la limpieza automatizada (módulo que ejecuta el worker)."""
import pandas as pd
import pytest
from limpieza import limpiar, normalizar_id, normalizar_fecha, normalizar_sistema, normalizar_monto

HOY = '2026-11-06'


@pytest.mark.parametrize('x,esperado', [('k-1', 'K1'), (' m 2 ', 'M2'), ('C07', 'C7'.replace('C7', 'C07')), ('XYZ', None), (None, None), ('', None)])
def test_normalizar_id(x, esperado):
    assert normalizar_id(x) == esperado


def test_fecha_formatos_y_rangos():
    assert normalizar_fecha('2026-03-05', HOY) == pd.Timestamp('2026-03-05')
    assert normalizar_fecha('25/03/2026', HOY) == pd.Timestamp('2026-03-25')
    assert pd.isna(normalizar_fecha('2027-01-01', HOY))       # futura
    assert pd.isna(normalizar_fecha('1999-01-01', HOY))       # fuera de rango
    assert pd.isna(normalizar_fecha('no-es-fecha', HOY))


def test_sistema():
    assert normalizar_sistema('Hidráulico') == 'hidraulico'
    assert normalizar_sistema('tren de rodaje') == 'tren_rodaje'
    assert normalizar_sistema('algo raro') == 'otro'
    assert normalizar_sistema(None) == 'otro'


def test_monto():
    assert normalizar_monto('$1,500.50') == 1500.5
    assert normalizar_monto('-20') is None
    assert normalizar_monto('abc') is None
    assert normalizar_monto('99999999') is None
    assert normalizar_monto(None) is None


def test_limpiar_rechaza_y_deduplica():
    df = pd.DataFrame({'equipo_id': ['k1', 'K1', 'K1', 'ZZ', 'M2'],
                       'fecha': ['2026-01-10', '2026-01-10', '2026-01-11', '2026-01-12', 'mañana'],
                       'sistema': ['motor', 'Motor', 'motor', 'motor', 'motor'],
                       'tipo_evento': ['falla'] * 5, 'monto_mxn': ['100', '100', '$2,000', '5', '5']})
    ok, mal = limpiar(df, HOY)
    assert len(ok) == 2 and len(mal) == 3
    assert sorted(mal.motivo) == ['duplicado', 'equipo_id invalido', 'fecha invalida o fuera de rango']
    assert ok.monto_mxn.tolist() == [100.0, 2000.0]


def test_limpiar_columnas_opcionales_ausentes():
    ok, mal = limpiar(pd.DataFrame({'equipo_id': ['R1'], 'fecha': ['2026-02-01']}), HOY)
    assert len(ok) == 1 and ok.sistema[0] == 'otro' and pd.isna(ok.monto_mxn[0])
