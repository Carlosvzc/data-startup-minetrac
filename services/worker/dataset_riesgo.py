"""Dataset de registros de mantenimiento de MineTrac para el análisis exploratorio y el clasificador.

Cada fila es un registro de mantenimiento de un equipo (bitácora de camiones y libreta de taller, ya limpias).
Variable objetivo `repite_30d`: 1 si el mismo sistema del mismo equipo vuelve a registrarse entre 1 y 30 días
después; 0 si no. Se calcula solo con datos hacia adelante, por lo que las variables explicativas
(`dias_desde_previo_equipo`, `registros_previos_90d`, `previos_mismo_sistema_90d`) usan únicamente el pasado.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

GRUPOS = {
    # bitácora de camiones
    'Motor': 'motor', 'Caja, frenos y suspensión neumática': 'tren_motriz_frenos', 'Transmisión y dirección': 'tren_motriz_frenos',
    'A/C y eléctrico': 'electrico_ac', 'Electrónico': 'electrico_ac', 'Estético y cabina': 'estructura_cabina',
    'Llantas': 'llantas', 'Servicio preventivo': 'servicio_preventivo',
    # libreta de taller
    'Combustible y motor': 'motor', 'Transmisión y tren motriz': 'tren_motriz_frenos', 'Frenos': 'tren_motriz_frenos',
    'Hidráulico y dirección': 'tren_motriz_frenos', 'Enfriamiento y A/C': 'electrico_ac', 'Eléctrico y electrónico': 'electrico_ac',
    'Implementos y estructura': 'estructura_cabina', 'Sin clasificar': 'sin_clasificar',
}
SIN_OBJETIVO = {'servicio_preventivo', 'sin_clasificar'}   # no son fallas que se puedan "repetir"
VENTANA = 30


def unir_registros(mant: pd.DataFrame, lib: pd.DataFrame, inventario: pd.DataFrame | None = None) -> pd.DataFrame:
    """Deja las dos fuentes en las mismas columnas. No usa texto libre ni nombres de terceros."""
    a = pd.DataFrame({
        'fuente': 'bitacora_camiones', 'equipo_id': mant.camion_id, 'tipo_equipo': 'Camión',
        'fecha': pd.to_datetime(mant.fecha, errors='coerce'), 'fecha_calidad': mant.fecha_calidad,
        'sistema_original': mant.sistema, 'monto_mxn': mant.costo_mxn,
        'pieza_declarada': mant.tipo_pieza.fillna('sin_dato').isin(['sin_dato', 'por_capturar']).map(lambda x: 0 if x else 1),
        'proveedor_declarado': (mant.proveedor_codigo.fillna('sin_dato') != 'sin_dato').astype(int),
        'es_servicio': (mant.sistema == 'Servicio preventivo').astype(int),
        'intervalo_servicio_h': mant.intervalo_servicio_h,
    })
    b = pd.DataFrame({
        'fuente': 'libreta_taller', 'equipo_id': lib.equipo_id, 'tipo_equipo': lib.categoria,
        'fecha': pd.to_datetime(lib.fecha, errors='coerce'), 'fecha_calidad': lib.fecha_calidad,
        'sistema_original': lib.sistema, 'monto_mxn': lib.monto_mxn,
        'pieza_declarada': (~lib.tipo_pieza.fillna('sin_dato').eq('sin_dato')).astype(int),
        'proveedor_declarado': (lib.proveedor_codigo.fillna('sin_dato') != 'sin_dato').astype(int),
        'es_servicio': lib.es_servicio.astype(int),
        'intervalo_servicio_h': lib.intervalo_servicio_h,
    })
    df = pd.concat([a, b], ignore_index=True)
    df.loc[df.fecha_calidad == 'solo_anio', 'fecha'] = pd.NaT       # solo se conoce el año: no se inventa día ni mes
    df['sistema'] = df.sistema_original.map(GRUPOS).fillna('sin_clasificar')
    df.loc[df.es_servicio == 1, 'sistema'] = 'servicio_preventivo'
    return df


def agregar_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Variables explicativas (solo pasado) y variable objetivo (solo futuro)."""
    df = df.copy()
    df['mes'] = df.fecha.dt.month
    df['dia_semana'] = df.fecha.dt.dayofweek
    df['monto_mxn'] = pd.to_numeric(df.monto_mxn, errors='coerce')
    n = len(df)
    previo_eq = np.full(n, np.nan); r90 = np.full(n, np.nan); r90s = np.full(n, np.nan); repite = np.full(n, np.nan)
    fin = df.fecha.max()
    for _, g in df.dropna(subset=['fecha']).groupby('equipo_id'):
        f = g.fecha.values.astype('datetime64[D]'); idx = g.index.values; sis = g.sistema.values
        for k in range(len(g)):
            d = (f[k] - f).astype(int)                       # días desde cada registro hasta este
            antes = (d > 0) & (d <= 90)
            r90[idx[k]] = antes.sum()
            r90s[idx[k]] = (antes & (sis == sis[k])).sum()
            prev = d[d > 0]
            previo_eq[idx[k]] = prev.min() if len(prev) else np.nan
            if sis[k] not in SIN_OBJETIVO and (fin - g.fecha.iloc[k]).days >= VENTANA:
                despues = (-d > 0) & (-d <= VENTANA) & (sis == sis[k])
                repite[idx[k]] = int(despues.any())
    df['dias_desde_previo_equipo'] = previo_eq
    df['registros_previos_90d'] = r90
    df['previos_mismo_sistema_90d'] = r90s
    df['repite_30d'] = repite
    return df


def construir_dataset(mant: pd.DataFrame, lib: pd.DataFrame) -> pd.DataFrame:
    return agregar_variables(unir_registros(mant, lib))
