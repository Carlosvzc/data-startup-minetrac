"""Limpieza automatizada de eventos de mantenimiento recibidos por la API (E2).
Cada regla es una función pequeña con prueba en tests/test_limpieza.py."""
from __future__ import annotations
import re
import pandas as pd

COLUMNAS = ['equipo_id', 'fecha', 'sistema', 'tipo_evento', 'monto_mxn']
OBLIGATORIAS = ['equipo_id', 'fecha']
SISTEMAS = {'motor', 'hidraulico', 'transmision', 'tren_rodaje', 'electrico', 'frenos', 'enfriamiento', 'llantas', 'estructura', 'servicio', 'otro'}
SINONIMOS = {'hidráulico': 'hidraulico', 'hidraulica': 'hidraulico', 'transmisión': 'transmision', 'eléctrico': 'electrico',
             'electrica': 'electrico', 'tren de rodaje': 'tren_rodaje', 'rodaje': 'tren_rodaje', 'radiador': 'enfriamiento'}
ID_VALIDO = re.compile(r'^[A-Z]{1,2}\d{1,2}$')
MONTO_MAX = 5_000_000.0


def normalizar_id(x) -> str | None:
    if pd.isna(x):
        return None
    s = re.sub(r'[\s\-_]', '', str(x)).upper()
    return s if ID_VALIDO.match(s) else None


def normalizar_fecha(x, hoy=None):
    hoy = pd.Timestamp(hoy) if hoy is not None else pd.Timestamp.today().normalize()
    d = pd.to_datetime(x, errors='coerce', dayfirst=False)
    if pd.isna(d):
        d = pd.to_datetime(x, errors='coerce', dayfirst=True)
    if pd.isna(d) or d > hoy or d < pd.Timestamp('2015-01-01'):
        return pd.NaT
    return d.normalize()


def normalizar_sistema(x) -> str:
    if pd.isna(x) or not str(x).strip():
        return 'otro'
    s = str(x).strip().lower()
    s = SINONIMOS.get(s, s).replace(' ', '_')
    return s if s in SISTEMAS else 'otro'


def normalizar_monto(x):
    if pd.isna(x):
        return None
    s = re.sub(r'[\$,\s]', '', str(x))
    try:
        v = float(s)
    except ValueError:
        return None
    return v if 0 <= v <= MONTO_MAX else None


def limpiar(df: pd.DataFrame, hoy=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (limpios, rechazados). Un rechazado conserva la fila original y el motivo."""
    df = df.copy()
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    orig = df[COLUMNAS].copy()
    out = pd.DataFrame({
        'equipo_id': df['equipo_id'].map(normalizar_id),
        'fecha': df['fecha'].map(lambda v: normalizar_fecha(v, hoy)),
        'sistema': df['sistema'].map(normalizar_sistema),
        'tipo_evento': df['tipo_evento'].fillna('').astype(str).str.strip().str.lower().replace('', 'sin_dato'),
        'monto_mxn': df['monto_mxn'].map(normalizar_monto),
    })
    motivo = pd.Series('', index=out.index)
    motivo[out.equipo_id.isna()] = 'equipo_id invalido'
    motivo[(motivo == '') & out.fecha.isna()] = 'fecha invalida o fuera de rango'
    dup = out.duplicated(subset=['equipo_id', 'fecha', 'sistema', 'tipo_evento'], keep='first') & (motivo == '')
    motivo[dup] = 'duplicado'
    limpios = out[motivo == ''].reset_index(drop=True)
    limpios['monto_mxn'] = pd.to_numeric(limpios['monto_mxn'])
    rech = orig[motivo != ''].copy()
    rech['motivo'] = motivo[motivo != '']
    return limpios, rech.reset_index(drop=True)
