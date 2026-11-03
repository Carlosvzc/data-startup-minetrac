"""Pipeline de la libreta manuscrita de Máquinas Centella (equipos que no son camiones).

Lee la transcripción (data/raw/libreta_transcripcion_PRIVADO.md, no se sube a GitHub porque trae nombres de terceros)
y genera:
  data/clean/libreta_eventos.csv    un evento por anotación, sin texto libre y con proveedores anonimizados
  data/clean/libreta_resumen.json   indicadores y auditoría de la libreta
  data/raw/libreta_proveedores_PRIVADO.json   equivalencia código -> proveedor (privado)
  data/sample/libreta_muestra.csv   muestra pública (primeras 40 filas)

Uso (desde la raíz del repositorio):
    python scripts/pipeline_libreta.py
"""
from pathlib import Path
import json, sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/worker'))
from etl_libreta import parsear   # noqa: E402

FUENTE = ROOT / 'data/raw/libreta_transcripcion_PRIVADO.md'


def resumen_libreta(df, aud, catalogo_ids):
    """Indicadores descriptivos de la libreta. Solo usamos montos únicos en pesos; los demás quedan fuera."""
    ev = df.copy()
    fechas = pd.to_datetime(ev.fecha)
    ev['mes'] = fechas.dt.to_period('M').astype(str)
    no_serv = ev[~ev.es_servicio]
    # repeticiones: mismo equipo y mismo sistema en menos de 30 días (excluye servicios preventivos)
    rep = 0
    for _, g in no_serv.dropna(subset=['fecha']).groupby(['equipo_id', 'sistema']):
        d = pd.to_datetime(g.fecha).sort_values()
        rep += int((d.diff().dt.days.between(0, 30)).sum())
    montos = ev.monto_mxn.dropna()
    por_equipo = ev.groupby('equipo_id').agg(
        anotaciones=('evento_id', 'size'), servicios=('es_servicio', 'sum'),
        gasto_mxn=('monto_mxn', 'sum'), con_monto=('monto_mxn', 'count'),
        desforzado=('desforzado', 'sum'), garantias=('garantia', 'sum'), canibalizaciones=('canibalizacion', 'sum')).reset_index()
    prov = ev[ev.proveedor_codigo != 'sin_dato'].groupby('proveedor_codigo').agg(
        anotaciones=('evento_id', 'size'), gasto_mxn=('monto_mxn', 'sum'), equipos=('equipo_id', 'nunique')).reset_index()
    sistemas = no_serv.groupby('sistema').agg(anotaciones=('evento_id', 'size'), gasto_mxn=('monto_mxn', 'sum'),
                                              equipos=('equipo_id', 'nunique')).reset_index().sort_values('anotaciones', ascending=False)
    canib = []
    for _, r in ev[ev.canibalizacion].iterrows():
        canib.append({'equipo': r.equipo_id, 'fecha': r.fecha, 'otros_equipos': r.equipos_mencionados})
    serv = ev[ev.intervalo_servicio_h.notna()]
    en_libreta = set(ev.equipo_id)
    return {
        'auditoria': aud,
        'kpis': {
            'anotaciones': int(len(ev)), 'equipos': int(ev.equipo_id.nunique()),
            'servicios_preventivos': int(ev.es_servicio.sum()),
            'servicios_con_intervalo': int(len(serv)),
            'gasto_mxn_monto_unico': float(montos.sum()), 'anotaciones_con_monto_unico': int(len(montos)),
            'anotaciones_con_varios_montos': int((ev.n_montos > 1).sum()),
            'anotaciones_con_monto_usd': int(ev.monto_usd.notna().sum()), 'gasto_usd_monto_unico': float(ev.monto_usd.dropna().sum()),
            'repeticiones_mismo_sistema_30d': rep,
            'pct_repeticion': 100 * rep / max(len(no_serv), 1),
            'desforzado': int(ev.desforzado.sum()), 'garantias': int(ev.garantia.sum()),
            'canibalizaciones': int(ev.canibalizacion.sum()),
            'tipo_pieza_declarado': int((ev.tipo_pieza != 'sin_dato').sum()),
            'horometro_anotado': int(ev.horometro.notna().sum()),
        },
        'periodo': {'inicio': str(fechas.min().date()), 'fin': str(fechas.max().date())},
        'servicios_por_intervalo': serv.intervalo_servicio_h.astype(int).value_counts().sort_index().to_dict(),
        'por_equipo': por_equipo.to_dict('records'), 'por_proveedor': prov.to_dict('records'),
        'por_sistema': sistemas.to_dict('records'), 'canibalizaciones': canib,
        'cruce_catalogo': {
            'en_libreta_y_catalogo': sorted(en_libreta & set(catalogo_ids)),
            'en_libreta_no_catalogo': sorted(en_libreta - set(catalogo_ids)),
            'catalogo_sin_libreta_no_camion': sorted(i for i in set(catalogo_ids) - en_libreta if not i.startswith('C')),
        },
    }


def main():
    if not FUENTE.exists():
        print('No existe', FUENTE, '- se omite la libreta.')
        return None
    mapa_path = ROOT / 'data/raw/libreta_proveedores_PRIVADO.json'
    mapa_ant = json.loads(mapa_path.read_text(encoding='utf-8')) if mapa_path.exists() else {}
    df, aud, mapa = parsear(FUENTE.read_text(encoding='utf-8'), mapa_ant)
    for f in ['data/raw', 'data/clean', 'data/sample']:
        (ROOT / f).mkdir(parents=True, exist_ok=True)
    mapa_path.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding='utf-8')
    df.to_csv(ROOT / 'data/clean/libreta_eventos.csv', index=False, encoding='utf-8-sig')
    cat_path = ROOT / 'data/clean/inventario.csv'
    ids = pd.read_csv(cat_path).equipo_id.tolist() if cat_path.exists() else []
    res = resumen_libreta(df, aud, ids)
    (ROOT / 'data/clean/libreta_resumen.json').write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    df.head(40).to_csv(ROOT / 'data/sample/libreta_muestra.csv', index=False)
    print(json.dumps({k: res[k] for k in ['kpis', 'periodo', 'cruce_catalogo']}, ensure_ascii=False, indent=1))
    return res


if __name__ == '__main__':
    main()
