"""API de modelos de MineTrac (E3). Endpoints: GET /salud, POST /pronostico, POST /clasificar. Documentación en /docs."""
from __future__ import annotations
import json
import os
from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from services.modelos import modelos as m

ARTEFACTOS = Path(os.environ.get('MODELOS_ARTEFACTOS', Path(__file__).resolve().parent / 'artefactos'))
app = FastAPI(title='MineTrac · API de modelos', version='1.0',
              description='Pronóstico semanal de intervenciones de los camiones (ARIMA) y clasificador de repetición de fallas.')
_estado: dict = {}


def _cargar():
    if not _estado:
        serie = pd.read_csv(ARTEFACTOS / 'serie_semanal.csv', index_col=0, parse_dates=True).iloc[:, 0]
        serie.index = pd.DatetimeIndex(serie.index, freq='W-MON')
        _estado['serie'] = serie
        _estado['clasificador'] = joblib.load(ARTEFACTOS / 'clasificador.joblib')
        _estado['metricas'] = json.loads((ARTEFACTOS / 'metricas_e3.json').read_text(encoding='utf-8'))
    return _estado


class PeticionPronostico(BaseModel):
    horizonte_dias: int = Field(7, description='7 o 30 días; se convierte a semanas (1 o 4)', ge=1, le=84)
    nivel: float = Field(0.95, ge=0.5, lt=1, description='Nivel de la banda de confianza')


class PeticionClasificar(BaseModel):
    sistema: str = Field(..., description='motor, tren_motriz_frenos, electrico_ac, estructura_cabina o llantas')
    mes: int = Field(..., ge=1, le=12)
    dia_semana: int = Field(..., ge=0, le=6, description='0 = lunes')
    dias_desde_previo_equipo: float | None = Field(None, ge=0, description='Días desde el registro anterior del camión (vacío si es el primero)')
    registros_previos_90d: int = Field(0, ge=0)
    previos_mismo_sistema_90d: int = Field(0, ge=0)
    pieza_declarada: int = Field(0, ge=0, le=1)
    proveedor_declarado: int = Field(0, ge=0, le=1)


@app.get('/salud')
def salud():
    e = _cargar()
    return {'estado': 'ok', 'semanas_en_serie': int(len(e['serie'])), 'modelo_clasificador': e['metricas']['clasificador']['modelo_elegido'],
            'orden_arima': e['metricas']['arima']['orden']}


@app.post('/pronostico')
def pronostico(p: PeticionPronostico):
    """Pronóstico de intervenciones por semana (ARIMA) con banda de confianza. La serie es semanal: 30 días equivalen a 4 semanas."""
    semanas = max(1, round(p.horizonte_dias / 7))
    if semanas > 12:
        raise HTTPException(status_code=422, detail='El horizonte máximo es de 84 días (12 semanas).')
    df = m.pronosticar(_cargar()['serie'], semanas, p.nivel)
    return {'modelo': f'ARIMA{tuple(m.ORDEN_ARIMA)}', 'nivel': p.nivel, 'semanas': semanas,
            'intervenciones_esperadas_total': round(float(df['pronostico'].sum()), 2),
            'pronostico': df.round(3).to_dict('records'),
            'aviso': 'Serie corta (132 semanas) y conteos pequeños: sirve como referencia para planear, no como promesa.'}


@app.post('/clasificar')
def clasificar(p: PeticionClasificar):
    """Probabilidad de que el mismo sistema del mismo camión vuelva a registrarse en los próximos 30 días."""
    if p.sistema not in m.SISTEMAS:
        raise HTTPException(status_code=422, detail=f'sistema debe ser uno de: {", ".join(m.SISTEMAS)}')
    e = _cargar()
    fila = pd.DataFrame([p.model_dump()])[m.NUMERICAS + m.CATEGORICAS]
    prob = float(e['clasificador'].predict_proba(fila)[0, 1])
    c = e['metricas']['clasificador']
    return {'repite_30d': bool(prob >= 0.5), 'probabilidad': round(prob, 4), 'modelo': c['modelo_elegido'],
            'f1_en_prueba': round(c['modelos'][c['modelo_elegido']]['f1'], 3),
            'aviso': 'La probabilidad no está calibrada: úsala para ordenar casos, no como porcentaje exacto.'}
