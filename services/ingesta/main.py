"""Microservicio de ingesta (FastAPI). Valida el archivo, lo deja en S3 (o en el mensaje) y encola el trabajo.
OpenAPI en /docs y /openapi.json."""
from __future__ import annotations
import io, os, sys, uuid
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worker'))
from db import Job, Evento, motor, sesion          # noqa: E402
from cola import crear_cola                        # noqa: E402

MAX_BYTES = 5 * 1024 * 1024
REQUERIDAS = {'equipo_id', 'fecha'}
PERMITIDAS = {'equipo_id', 'fecha', 'sistema', 'tipo_evento', 'monto_mxn'}

app = FastAPI(title='MineTrac · Ingesta', version='2.0',
              description='Recibe CSV de mantenimiento de Máquinas Centella, lo valida y lo encola para su limpieza.')
_estado: dict = {}


class JobOut(BaseModel):
    job_id: str
    estado: str
    filas_recibidas: int = 0
    filas_limpias: int = 0
    filas_rechazadas: int = 0
    intentos: int = 0
    error: str | None = None


def recursos():
    if 'cola' not in _estado:
        _estado['motor'], _estado['cola'] = motor(), crear_cola()
    return _estado


def validar_csv(contenido: bytes) -> pd.DataFrame:
    if not contenido:
        raise HTTPException(400, 'El archivo está vacío.')
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, 'El archivo supera 5 MB.')
    try:
        df = pd.read_csv(io.BytesIO(contenido), dtype=str)
    except Exception as exc:                       # noqa: BLE001
        raise HTTPException(400, f'No se pudo leer como CSV: {exc}')
    cols = {c.strip().lower() for c in df.columns}
    faltan = REQUERIDAS - cols
    if faltan:
        raise HTTPException(422, f'Faltan columnas obligatorias: {sorted(faltan)}')
    extra = cols - PERMITIDAS
    if extra:
        raise HTTPException(422, f'Columnas no permitidas: {sorted(extra)}')
    if df.empty:
        raise HTTPException(422, 'El CSV no tiene filas.')
    return df


@app.get('/salud', tags=['operación'])
def salud():
    return {'estado': 'ok'}


@app.post('/ingesta', response_model=JobOut, status_code=202, tags=['ingesta'])
async def ingesta(archivo: UploadFile = File(...), r: dict = Depends(recursos)):
    contenido = await archivo.read()
    df = validar_csv(contenido)
    job_id = uuid.uuid4().hex
    ses = sesion(r['motor'])
    ses.add(Job(id=job_id, archivo=(archivo.filename or 'sin_nombre')[:200], filas_recibidas=len(df)))
    ses.commit(); ses.close()
    msg = {'job_id': job_id}
    bucket = os.getenv('S3_BUCKET')
    if bucket:
        import boto3
        clave = f'ingesta/{job_id}.csv'
        boto3.client('s3').put_object(Bucket=bucket, Key=clave, Body=contenido)
        msg.update(bucket=bucket, clave=clave)
    else:
        msg['csv'] = contenido.decode('utf-8-sig')
    r['cola'].enviar(msg)
    return JobOut(job_id=job_id, estado='en_cola', filas_recibidas=len(df))


@app.get('/jobs/{job_id}', response_model=JobOut, tags=['ingesta'])
def estado_job(job_id: str, r: dict = Depends(recursos)):
    ses = sesion(r['motor'])
    j = ses.get(Job, job_id)
    ses.close()
    if j is None:
        raise HTTPException(404, 'Job no encontrado.')
    return JobOut(job_id=j.id, estado=j.estado, filas_recibidas=j.filas_recibidas or 0, filas_limpias=j.filas_limpias or 0,
                  filas_rechazadas=j.filas_rechazadas or 0, intentos=j.intentos or 0, error=j.error)
