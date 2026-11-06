"""Worker asíncrono: toma un mensaje, descarga el CSV, lo limpia y lo guarda en la base.
Si falla, el mensaje vuelve a la cola; tras max_intentos pasa a la cola de mensajes muertos y el job queda 'fallido'."""
from __future__ import annotations
import datetime as dt, io, logging, os, time
import pandas as pd
from limpieza import limpiar
from db import Job, Evento, motor, sesion
from cola import crear_cola

log = logging.getLogger('worker')


def leer_csv(msg: dict) -> pd.DataFrame:
    if 'csv' in msg:                       # modo local/pruebas: el CSV viaja en el mensaje
        return pd.read_csv(io.StringIO(msg['csv']), dtype=str)
    import boto3
    obj = boto3.client('s3').get_object(Bucket=msg['bucket'], Key=msg['clave'])
    return pd.read_csv(io.BytesIO(obj['Body'].read()), dtype=str)


def procesar(msg: dict, intento: int, ses, leer=leer_csv) -> dict:
    job = ses.get(Job, msg['job_id'])
    job.estado, job.intentos = 'procesando', intento
    ses.commit()
    df = leer(msg)
    limpios, rech = limpiar(df)
    ses.query(Evento).filter(Evento.job_id == job.id).delete()      # idempotente ante reintentos
    ses.add_all([Evento(job_id=job.id, equipo_id=r.equipo_id, fecha=r.fecha.date(), sistema=r.sistema,
                        tipo_evento=r.tipo_evento, monto_mxn=None if pd.isna(r.monto_mxn) else float(r.monto_mxn))
                 for r in limpios.itertuples()])
    job.filas_recibidas, job.filas_limpias, job.filas_rechazadas = len(df), len(limpios), len(rech)
    job.estado, job.terminado = 'listo', dt.datetime.utcnow()
    ses.commit()
    return {'limpias': len(limpios), 'rechazadas': len(rech)}


def un_ciclo(cola, ses_factory, max_intentos=3, leer=leer_csv) -> bool:
    m = cola.recibir()
    if m is None:
        return False
    ses = ses_factory()
    try:
        procesar(m.cuerpo, m.intentos, ses, leer)
        cola.borrar(m.handle)
    except Exception as exc:                                   # noqa: BLE001
        ses.rollback()
        job = ses.get(Job, m.cuerpo['job_id'])
        if job is not None:
            job.intentos, job.error = m.intentos, f'{type(exc).__name__}: {exc}'[:500]
            job.estado = 'fallido' if m.intentos >= max_intentos else 'en_cola'
            if job.estado == 'fallido':
                job.terminado = dt.datetime.utcnow()
            ses.commit()
        log.warning('job %s intento %s fallo: %s', m.cuerpo.get('job_id'), m.intentos, exc)
        cola.devolver(m.handle)
    finally:
        ses.close()
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    e = motor()
    cola = crear_cola()
    log.info('worker listo')
    while True:
        if not un_ciclo(cola, lambda: sesion(e), int(os.getenv('MAX_INTENTOS', '3'))):
            time.sleep(1)


if __name__ == '__main__':
    main()
