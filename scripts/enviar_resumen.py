"""Envía por correo el resumen semanal de MineTrac (alertas + reporte PDF).

Sirve para programarlo (cron, EventBridge + ECS/Lambda). Por seguridad NO envía nada a menos que se pase --enviar;
sin esa bandera solo genera el PDF y muestra a quién se enviaría.

Uso (desde la raíz del repositorio):
    python scripts/enviar_resumen.py --para correo1@dominio.com,correo2@dominio.com            # prueba: guarda el PDF
    python scripts/enviar_resumen.py --para correo1@dominio.com --enviar                       # envía de verdad
Variables de entorno: ver services/tablero/correo.py. Destinatarios por defecto: MINETRAC_DESTINATARIOS.
"""
import argparse, os, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/tablero'))
import correo, resumen_envio  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--para', default=os.environ.get('MINETRAC_DESTINATARIOS', ''))
    ap.add_argument('--enviar', action='store_true', help='envía el correo de verdad')
    ap.add_argument('--salida', default=str(ROOT / 'docs/ejemplo_reporte.pdf'))
    a = ap.parse_args(argv)
    mant = pd.read_csv(ROOT / 'data/clean/mantenimiento.csv', encoding='utf-8-sig')
    asunto, html_c, texto, pdf, alertas = resumen_envio.paquete(mant, ROOT)
    Path(a.salida).write_bytes(pdf)
    dest = correo.separar_destinatarios(a.para)
    print(f'PDF guardado en {a.salida} ({len(pdf) // 1024} KB) · {len(alertas)} alertas · destinatarios: {", ".join(dest) or "ninguno"}')
    if not a.enviar:
        print('Modo prueba: no se envió nada. Agrega --enviar para mandarlo.'); return 0
    msg = correo.construir_mensaje(dest, asunto, html_c, texto, pdf, 'reporte_minetrac.pdf')
    print('Enviado por', correo.enviar(msg)); return 0


if __name__ == '__main__':
    sys.exit(main())
