import pandas as pd
from dataset_riesgo import agregar_variables, unir_registros, construir_dataset


def _base(filas):
    return pd.DataFrame(filas, columns=['equipo_id', 'fecha', 'sistema']).assign(
        fuente='x', tipo_equipo='Camión', fecha_calidad='ok', monto_mxn=None, es_servicio=0)


def test_objetivo_mira_solo_hacia_adelante_y_respeta_la_ventana():
    df = _base([('K1', '2026-01-01', 'motor'), ('K1', '2026-01-20', 'motor'),        # repite en 19 días
                ('K1', '2026-03-01', 'motor'), ('K2', '2026-01-01', 'motor'),         # K2 no repite
                ('K1', '2026-10-01', 'motor')])                                       # al final: sin ventana completa
    df['fecha'] = pd.to_datetime(df.fecha)
    r = agregar_variables(df)
    assert r.repite_30d.tolist()[:4] == [1, 0, 0, 0] and pd.isna(r.repite_30d.iloc[4])


def test_variables_explicativas_usan_solo_el_pasado():
    df = _base([('K1', '2026-01-01', 'motor'), ('K1', '2026-01-11', 'motor'), ('K1', '2026-01-21', 'llantas')])
    df['fecha'] = pd.to_datetime(df.fecha)
    r = agregar_variables(df)
    assert r.dias_desde_previo_equipo.tolist()[1:] == [10, 10] and pd.isna(r.dias_desde_previo_equipo.iloc[0])
    assert r.registros_previos_90d.tolist() == [0, 1, 2] and r.previos_mismo_sistema_90d.tolist() == [0, 1, 0]


def test_servicios_y_sin_clasificar_no_tienen_objetivo():
    df = _base([('K1', '2026-01-01', 'servicio_preventivo'), ('K1', '2026-01-05', 'servicio_preventivo'),
                ('K1', '2026-01-02', 'sin_clasificar'), ('K1', '2026-12-01', 'motor')])
    df['fecha'] = pd.to_datetime(df.fecha)
    r = agregar_variables(df)
    assert r.repite_30d.iloc[:3].isna().all()


def test_dataset_real_cumple_el_minimo_de_la_materia():
    d = construir_dataset(pd.read_csv('data/clean/mantenimiento.csv'), pd.read_csv('data/clean/libreta_eventos.csv'))
    assert len(d) >= 500 and d.repite_30d.notna().sum() >= 500
    assert d.fecha.min() >= pd.Timestamp('2023-01-01')          # el año suelto ya no inventa una fecha de 2022
    assert set(d.fuente) == {'bitacora_camiones', 'libreta_taller'}
    assert d.repite_30d.dropna().isin([0, 1]).all()
