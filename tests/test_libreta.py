from pathlib import Path
import sys
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/worker'))
sys.path.insert(0, str(ROOT / 'services/tablero'))
from etl_libreta import parsear   # noqa: E402

MUESTRA = """## K9 (Cargador 9) · 1 foto

- 15/jul/24: Servicio 250.
- 20/nov/24: Joystick nuevo, compra con Eudave a $12,000 / Tracsa $1,100 USD.
- 06/ene/24 [así escrito]: Chumacera trabada.
- 10/feb/25: Bomba de diesel nueva Tracsa $9,000. Está desforzado.
- 21/sep/25: Le quitan el control para ponérselo al T1.
- Necesita sprock derecho.

## T1 (Tractor 1) · 1 foto

- 03/abr/24: 2 puntas, $2,500 c/u.
"""


def test_parser_fechas_montos_y_proveedores():
    df, aud, mapa = parsear(MUESTRA)
    assert len(df) == 7 and aud['equipos'] == 2
    assert df.loc[0, 'fecha'] == '2024-07-15' and df.loc[0, 'es_servicio'] and df.loc[0, 'intervalo_servicio_h'] == 250
    # varias cifras en el mismo renglón: no se toma ninguna como gasto
    assert df.loc[1, 'n_montos'] == 2 and pd.isna(df.loc[1, 'monto_mxn'])
    # año escrito al revés se corrige por el orden de la libreta
    assert df.loc[2, 'fecha'] == '2025-01-06' and df.loc[2, 'fecha_calidad'] == 'anio_corregido'
    assert df.loc[3, 'monto_mxn'] == 9000 and df.loc[3, 'desforzado'] and df.loc[3, 'proveedor_codigo'] in set(mapa.values())
    assert df.loc[4, 'canibalizacion'] and df.loc[4, 'equipos_mencionados'] == 'T1'
    assert df.loc[5, 'fecha'] is None or pd.isna(df.loc[5, 'fecha'])
    assert df.loc[6, 'categoria'] == 'Tractor' and df.loc[6, 'monto_mxn'] == 2500


def test_parser_no_expone_nombres_de_proveedores():
    df, _, mapa = parsear(MUESTRA)
    assert 'Tracsa' not in df.to_csv() and 'Eudave' not in df.to_csv()
    assert set(mapa) == {'Tracsa', 'Eudave'}


LIB = ROOT / 'data/clean/libreta_eventos.csv'


@pytest.mark.skipif(not LIB.exists(), reason='Ejecuta primero: python scripts/pipeline_libreta.py')
def test_libreta_real_consistente():
    d = pd.read_csv(LIB)
    assert d.evento_id.is_unique and d.equipo_id.nunique() == 14 and len(d) == 540
    assert (d.monto_mxn.dropna() > 0).all() and d.loc[d.n_montos > 1, 'monto_mxn'].isna().all()
    assert (d.naturaleza_dato == 'real').all()
    from libreta import graficas, kpis
    assert kpis(d)['anotaciones'] == 540 and all(f is not None for f in graficas(d))
    assert graficas(d.iloc[0:0]) == [None] * 4
