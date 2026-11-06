"""Flujo completo: API -> cola -> worker -> base. Incluye reintentos y mensajes muertos."""
import io, os
import pytest
from fastapi.testclient import TestClient
from cola import ColaMemoria, ColaSQS
from db import motor, sesion, Job, Evento
from worker import un_ciclo
import main as ingesta

CSV = "equipo_id,fecha,sistema,tipo_evento,monto_mxn\nK1,2026-01-10,motor,falla,1500\nk-2,2026-01-11,Hidráulico,falla,\nXX,2026-01-12,motor,falla,10\n"


@pytest.fixture
def entorno(tmp_path):
    e = motor(f'sqlite:///{tmp_path}/t.db')
    cola = ColaMemoria(max_intentos=3)
    ingesta._estado.clear(); ingesta._estado.update(motor=e, cola=cola)
    return TestClient(ingesta.app), e, cola


def subir(c, texto=CSV, nombre='x.csv'):
    return c.post('/ingesta', files={'archivo': (nombre, io.BytesIO(texto.encode()), 'text/csv')})


def test_flujo_completo(entorno):
    c, e, cola = entorno
    r = subir(c); assert r.status_code == 202
    jid = r.json()['job_id']
    assert c.get(f'/jobs/{jid}').json()['estado'] == 'en_cola'
    assert un_ciclo(cola, lambda: sesion(e))
    j = c.get(f'/jobs/{jid}').json()
    assert (j['estado'], j['filas_recibidas'], j['filas_limpias'], j['filas_rechazadas']) == ('listo', 3, 2, 1)
    s = sesion(e); assert s.query(Evento).filter_by(job_id=jid).count() == 2; s.close()
    assert not cola.pendientes and not un_ciclo(cola, lambda: sesion(e))


@pytest.mark.parametrize('texto,codigo', [('', 400), ('equipo_id\nK1\n', 422), ('equipo_id,fecha,otra\nK1,2026-01-01,1\n', 422), ('equipo_id,fecha\n', 422)])
def test_validacion_rechaza(entorno, texto, codigo):
    assert subir(entorno[0], texto).status_code == codigo


def test_job_inexistente_y_openapi(entorno):
    c = entorno[0]
    assert c.get('/jobs/nada').status_code == 404
    assert '/ingesta' in c.get('/openapi.json').json()['paths'] and c.get('/salud').json() == {'estado': 'ok'}


def test_reintentos_y_mensaje_muerto(entorno):
    c, e, cola = entorno
    jid = subir(c).json()['job_id']
    def falla(msg): raise RuntimeError('base caida')
    for _ in range(3):
        assert un_ciclo(cola, lambda: sesion(e), 3, leer=falla)
    j = c.get(f'/jobs/{jid}').json()
    assert j['estado'] == 'fallido' and j['intentos'] == 3 and 'base caida' in j['error']
    assert not un_ciclo(cola, lambda: sesion(e), 3, leer=falla)   # ya no hay mensajes
    assert len(cola.muertos) == 1


def test_reintento_exitoso_no_duplica(entorno):
    c, e, cola = entorno
    jid = subir(c).json()['job_id']
    estado = {'n': 0}
    from worker import leer_csv
    def a_medias(msg):
        estado['n'] += 1
        if estado['n'] == 1: raise RuntimeError('tiempo agotado')
        return leer_csv(msg)
    un_ciclo(cola, lambda: sesion(e), 3, leer=a_medias); un_ciclo(cola, lambda: sesion(e), 3, leer=a_medias)
    j = c.get(f'/jobs/{jid}').json()
    assert j['estado'] == 'listo' and j['intentos'] == 2
    s = sesion(e); assert s.query(Evento).count() == 2; s.close()


def test_cola_sqs_con_moto():
    moto = pytest.importorskip('moto')
    os.environ.update(AWS_ACCESS_KEY_ID='x', AWS_SECRET_ACCESS_KEY='x', AWS_REGION='us-east-1')
    with moto.mock_aws():
        q = ColaSQS(nombre='prueba', max_intentos=2, visibilidad=0)
        q.enviar({'job_id': 'abc'})
        m = q.recibir(espera=0); assert m and m.cuerpo == {'job_id': 'abc'} and m.intentos == 1
        q.devolver(m.handle)
        m2 = q.recibir(espera=0); assert m2 and m2.intentos == 2
        q.borrar(m2.handle); assert q.recibir(espera=0) is None
