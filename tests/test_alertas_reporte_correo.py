import sys, io
from pathlib import Path
import pandas as pd, pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/tablero'))
import alertas, correo, reporte, resumen_envio  # noqa: E402


def datos():
    return pd.read_csv(ROOT / 'data/sample/mantenimiento_muestra.csv') if False else pd.read_csv(ROOT / 'data/clean/mantenimiento.csv', encoding='utf-8-sig')


def mini():
    f = lambda i, c, d, s, comp, rep=False: dict(evento_id=i, camion_id=c, fecha=d, fecha_calidad='ok', sistema=s, componente=comp, reincidencia_30d=rep,
                                                 costo_mxn=100.0, costo_mxn_intervencion=100.0)
    return pd.DataFrame([f('A1', 'C1', '2026-01-01', 'Servicio preventivo', 'Servicio'), f('A2', 'C1', '2026-09-01', 'Motor', 'Turbo'),
                         f('A3', 'C1', '2026-09-20', 'Motor', 'Turbo', True), f('B1', 'C2', '2026-09-25', 'Llantas', 'Llanta')])


def test_alertas_reglas_basicas():
    a = alertas.calcular(mini(), corte='2026-09-30')
    tipos = set(zip(a.camion_id, a.tipo, a.severidad))
    assert ('C1', 'Servicio preventivo', 'Alta') in tipos          # 272 días sin servicio
    assert ('C1', 'Repetición reciente', 'Alta') in tipos
    assert ('C2', 'Servicio preventivo', 'Media') in tipos         # nunca se registró uno
    assert list(a.severidad) == sorted(a.severidad, key=alertas.ORDEN.get)   # ordenadas por severidad


def test_alertas_no_miran_el_futuro():
    a = alertas.calcular(mini(), corte='2026-08-15')
    assert not (a.tipo == 'Repetición reciente').any()


def test_alertas_datos_reales():
    a = alertas.calcular(datos())
    assert len(a) > 0 and set(a.camion_id) <= {f'C{i}' for i in range(1, 8)} and a.severidad.isin(alertas.ORDEN).all()


def test_destinatarios():
    assert correo.separar_destinatarios('A@x.com; b@x.com,a@x.com\n c@x.com') == ['a@x.com', 'b@x.com', 'c@x.com']
    ok, mal = correo.validos(['a@x.com', 'sin-arroba', 'a@b'])
    assert ok == ['a@x.com'] and mal == ['sin-arroba', 'a@b']


def test_mensaje_rechaza_correos_malos_y_asunto_con_salto(monkeypatch):
    with pytest.raises(ValueError):
        correo.construir_mensaje(['malo'], 'x', '<p>x</p>', 'x', remitente='de@x.com')
    with pytest.raises(ValueError):
        correo.construir_mensaje(['a@x.com'], 'x\nBcc: y@z.com', '<p>x</p>', 'x', remitente='de@x.com')


def test_sin_configuracion_no_envia(monkeypatch):
    for v in ['MINETRAC_CORREO_DE', 'MINETRAC_SMTP_HOST', 'MINETRAC_SMTP_USUARIO', 'MINETRAC_SMTP_CLAVE']:
        monkeypatch.delenv(v, raising=False)
    assert correo.configurado()[0] is False
    msg = correo.construir_mensaje(['a@x.com'], 'Hola', '<p>x</p>', 'x', remitente='de@x.com')
    with pytest.raises(RuntimeError):
        correo.enviar(msg)


def test_envio_smtp_simulado(monkeypatch):
    enviados = []
    class FakeSMTP:
        def __init__(self, h, p, timeout=0): self.h = h
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self, context=None): enviados.append('tls')
        def login(self, u, c): enviados.append('login')
        def send_message(self, m): enviados.append(m['To'])
    monkeypatch.setattr(correo.smtplib, 'SMTP', FakeSMTP)
    for k, v in {'MINETRAC_CORREO': 'smtp', 'MINETRAC_CORREO_DE': 'de@x.com', 'MINETRAC_SMTP_HOST': 'smtp.x.com', 'MINETRAC_SMTP_USUARIO': 'u', 'MINETRAC_SMTP_CLAVE': 'c'}.items():
        monkeypatch.setenv(k, v)
    msg = correo.construir_mensaje(['a@x.com'], 'Hola', '<p>x</p>', 'x', pdf=b'%PDF-1.4 x')
    assert correo.enviar(msg) == 'smtp' and enviados == ['tls', 'login', 'a@x.com']
    assert any(p.get_filename() == 'reporte_minetrac.pdf' for p in msg.iter_attachments())


def test_html_escapa_texto():
    k = {'intervenciones': 1, 'gasto_mxn': 1.0}
    h = correo.cuerpo_html('T', '<script>x</script>', k, {'Alta': 1}, [dict(severidad='Alta', camion_id='C1', tipo='<b>x</b>', detalle='"y"')], 'p')
    assert '<script>' not in h and '&lt;script&gt;' in h and '<b>x</b>' not in h


def test_pdf_y_paquete_completo():
    asunto, h, t, pdf, al = resumen_envio.paquete(datos(), ROOT)
    assert pdf[:5] == b'%PDF-' and len(pdf) > 50_000 and 'MineTrac' in asunto
    from pypdf import PdfReader
    txt = ' '.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert 'Alertas de mantenimiento' in txt and 'Qué esperar' in txt
