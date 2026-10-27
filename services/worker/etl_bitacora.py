"""ETL de la bitácora real de camiones de Máquinas Centella.

Entrada: CAMIONES 12M3 Y 14M3.xlsx (una hoja por camión, columnas por sistema).
Salida: tabla ordenada (una fila por intervención y sistema) + auditoría cuantitativa.

Reglas importantes:
- No se inventan montos: si una intervención no trae costo, queda como faltante.
- Los nombres de personas y talleres se sustituyen por códigos (P01, P02...).
- El texto libre original NO sale de este módulo hacia el tablero.
"""
from __future__ import annotations
import re
import json
import datetime as dt
from pathlib import Path
import unicodedata
from collections import Counter
import numpy as np
import pandas as pd

SISTEMAS = [  # (palabra clave del encabezado, nombre normalizado)
    ('MOTOR', 'Motor'),
    ('ELECTRONICO', 'Electrónico'),
    ('TRANSIMISON', 'Transmisión y dirección'),
    ('CAJA', 'Caja, frenos y suspensión neumática'),
    ('AC/ELECTRICO', 'A/C y eléctrico'),
    ('ESTETICO', 'Estético y cabina'),
    ('LLANTAS', 'Llantas'),
    ('SERVICIO', 'Servicio preventivo'),
]
FECHA_CORTE = dt.date(2026, 10, 26)
MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

# Clasificación de componentes por palabras clave (orden = prioridad). Derivada del
# texto libre; debe validarse con el cliente.
COMPONENTES = [
    ('Fan clutch (ventilador)', r'fan clutch'),
    ('Clutch', r'clutch|cluth|clutc\b|collarin|clutchero'),
    ('Inyectores y bomba de diésel', r'inyector|bomba de inyeccion|bomba de diesel|bomba de la parte|bomba electrica|flotador|diesel|disel'),
    ('Cabeza, monobloc y motor mayor', r'ajusta motor|bajando el moto|se monta motor|armo la bomba|cabeza|monobloc|rectific|anillos|encamis|camisa|camias|metales|juntas|ajuste completo|motor armado|armar el camion|valvulas|valvula de la cabeza'),
    ('Compresor', r'compresor'),
    ('Motor (soportes, polea, turbo y otros)', r'bayoneta|soporte|polea|turbo|barilla|arbol de levas|bayobneta'),
    ('Marcha y arranque', r'marcha|arranque|vendix|bendix'),
    ('Alternador', r'altern|altenr'),
    ('Baterías', r'bateri'),
    ('Aire acondicionado', r'siroco|evaporador|condensador|clima|no enfria|\bac\b|a\.c'),
    ('Enfriamiento (radiador, bomba de agua)', r'radiador|termostato|calentando|calienta|anticongelante|bomba de agua|tanque de agua|pasa agua'),
    ('Gato hidráulico y levante', r'gato|levante|toma de fuerza'),
    ('Chamber y frenos', r'chamber|balata|freno|tambor|matraca'),
    ('Muelles y bolsas de aire', r'muelle|muey|amortiguador|bolsa|abrazadera|hojas'),
    ('Transmisión, flecha y diferencial', r'caja de velocidades|velicidades|transmision|tranmision|tranimision|difrencial|yugo|cruceta|flecha|cardan|diferencial|puente|eje\b|retenes|reten\b|baleros|direccion|chicote|palanca|multiple'),
    ('Computadora y sensores', r'computadora|sensor|escane|arnes|conector|electrico|falso contacto|ecm'),
    ('Llantas y rines', r'llanta|rhin|rin\b|rines'),
    ('Piso y caja de volteo', r'piso|placa|lamina'),
    ('Cabina y estética', r'asiento|tapiceria|cristal|espejo|parilla|faro|pintura|cachucha|limpiabrisas|cinturon|chapa|claxon|escalon|tanque'),
    ('Servicio preventivo', r'servic|serivcio'),
]
POR_SISTEMA = {  # respaldo cuando el texto no trae una pieza reconocible
    'Caja, frenos y suspensión neumática': [('Gato hidráulico y levante', r'bomba|bajando|se baja|baja la caja'),
                                            ('Caja y chasis (otros)', r'.*')],
    'Motor': [('Inyectores y bomba de diésel', r'bomba|rebaba|combustible|riel'), ('Motor (soportes, polea, turbo y otros)', r'.*')],
    'A/C y eléctrico': [('Aire acondicionado', r'manguera|valvula de retencion'), ('Sistema eléctrico (otros)', r'.*')],
    'Transmisión y dirección': [('Transmisión, flecha y diferencial', r'.*')],
    'Estético y cabina': [('Cabina y estética', r'.*')],
    'Llantas': [('Llantas y rines', r'.*')],
    'Servicio preventivo': [('Servicio preventivo', r'.*')],
    'Electrónico': [('Computadora y sensores', r'.*')],
}
REPARADA = re.compile(r'reparad|reman|rectific|reempaque|rempaque|empaca|empaqu|solda|soldo|ajusta|calibr', re.I)
NUEVA = re.compile(r'\bnuev[oa]s?\b|se compra|compran|se pone|se ponen|nuevamete', re.I)

# Proveedores: los alias (nombres de personas y talleres) viven en un archivo PRIVADO que no se sube a GitHub:
# data/raw/proveedores_alias_PRIVADO.json  ->  {"alias en el texto": "clave"}.
# Sin ese archivo no se detectan proveedores y la columna queda como 'sin_dato'.
RUTA_ALIAS = Path(__file__).resolve().parents[2] / 'data/raw/proveedores_alias_PRIVADO.json'


def cargar_alias(ruta=None) -> dict:
    ruta = Path(ruta or RUTA_ALIAS)
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else {}


def _norm(s) -> str:
    s = '' if s is None else str(s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


def sistema_de_encabezado(h):
    h = _norm(h).upper()
    for clave, nombre in SISTEMAS:
        if h.startswith(_norm(clave).upper()):
            return nombre
    return None


def candidatos_fecha_texto(raw: str):
    """Interpreta fechas escritas a mano ('01/se/25', '077sep/26', '11/jun/265', '10/ju/')."""
    m = re.match(r'^\s*(\d+)\s*/?\s*([a-zA-Z]+)\s*/\s*(\d*)\s*$', str(raw))
    if not m:
        return []
    dia, mes, anio = m.groups()
    dia = int(dia if int(dia) <= 31 else dia[:2])
    pref = _norm(mes)[:3]
    meses = [i + 1 for i, a in enumerate(MESES) if a.startswith(pref) or (len(pref) == 2 and a.startswith(pref))]
    if pref == 'se':
        meses = [9]
    if len(anio) == 2:
        anios = [2000 + int(anio)]
    elif len(anio) == 3:
        anios = [2000 + int(anio[:2]), 2020 + int(anio[2])]
    elif len(anio) == 4:
        anios = [int(anio)]
    else:
        anios = [2024, 2025, 2026]
    out = []
    for a in anios:
        for mm in meses:
            try:
                out.append(dt.date(a, mm, dia))
            except ValueError:
                pass
    return out


def _lis_indices(fechas):
    """Subsecuencia no decreciente más larga (anclas cronológicas). fechas: lista de (idx, date)."""
    n = len(fechas)
    if n == 0:
        return set()
    best = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if fechas[j][1] <= fechas[i][1] and best[j] + 1 > best[i]:
                best[i], prev[i] = best[j] + 1, j
    k = int(np.argmax(best))
    out = set()
    while k != -1:
        out.add(fechas[k][0])
        k = prev[k]
    return out


def resolver_fechas(filas):
    """filas: lista de dicts con 'fecha_raw'. Agrega 'fecha' y 'fecha_calidad'."""
    for f in filas:
        raw = f['fecha_raw']
        f['fecha'], f['fecha_calidad'], f['_cands'] = None, 'faltante', []
        if isinstance(raw, dt.datetime):
            f['fecha'], f['fecha_calidad'] = raw.date(), 'ok'
        elif isinstance(raw, dt.date):
            f['fecha'], f['fecha_calidad'] = raw, 'ok'
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool) and 1990 <= int(raw) <= 2100:
            f['fecha'], f['fecha_calidad'] = dt.date(int(raw), 1, 1), 'solo_anio'
        elif isinstance(raw, str):
            f['_cands'] = candidatos_fecha_texto(raw)
    # 0) Fechas imposibles (posteriores a la fecha de corte): se conserva día y mes.
    for i, f in enumerate(filas):
        if f['fecha_calidad'] == 'ok' and f['fecha'] > FECHA_CORTE:
            ref = next((g['fecha'] for g in reversed(filas[:i]) if g['fecha'] and g['fecha'] <= FECHA_CORTE), FECHA_CORTE)
            cands = []
            for y in range(FECHA_CORTE.year, FECHA_CORTE.year - 5, -1):
                try:
                    cands.append(f['fecha'].replace(year=y))
                except ValueError:
                    pass
            f['fecha'] = min([c for c in cands if c <= FECHA_CORTE], key=lambda c: abs((c - ref).days))
            f['fecha_calidad'] = 'anio_corregido'
    # 1) Anclas cronológicas entre las fechas completas.
    completas = [(i, f['fecha']) for i, f in enumerate(filas) if f['fecha_calidad'] in ('ok', 'anio_corregido')]
    anclas = _lis_indices(completas)
    for i, f in enumerate(filas):
        if f['fecha_calidad'] == 'ok' and i not in anclas:
            prev = max([filas[j]['fecha'] for j in anclas if j < i], default=dt.date.min)
            nxt = min([filas[j]['fecha'] for j in anclas if j > i], default=dt.date.max)
            d0 = f['fecha']
            for dy in (-1, 1, -2, 2, -3, 3, -4, 4):
                try:
                    cand = d0.replace(year=d0.year + dy)
                except ValueError:
                    continue
                if prev <= cand <= nxt:
                    f['fecha'], f['fecha_calidad'] = cand, 'anio_corregido'
                    break
            else:
                f['fecha_calidad'] = 'ok'  # fecha válida, solo capturada fuera de orden
                f['orden_alterado'] = True
    # 2) Fechas escritas a mano: se elige la candidata que respeta el orden de la hoja.
    for i, f in enumerate(filas):
        if f['_cands']:
            prev = max([g['fecha'] for g in filas[:i] if g['fecha'] and g['fecha_calidad'] in ('ok', 'anio_corregido')], default=dt.date.min)
            nxt = min([g['fecha'] for g in filas[i + 1:] if g['fecha'] and g['fecha_calidad'] in ('ok', 'anio_corregido')], default=dt.date.max)
            buenas = [c for c in f['_cands'] if prev <= c <= nxt]
            f['fecha'] = buenas[0] if buenas else min(f['_cands'], key=lambda c: abs((c - prev).days) if prev != dt.date.min else 0)
            f['fecha_calidad'] = 'texto_interpretado'
    # 3) Filas sin fecha: continúan la intervención anterior.
    for i, f in enumerate(filas):
        if f['fecha'] is None:
            ant = [g['fecha'] for g in filas[:i] if g['fecha'] and g['fecha_calidad'] != 'solo_anio']
            sig = [g['fecha'] for g in filas[i + 1:] if g['fecha'] and g['fecha_calidad'] != 'solo_anio']
            if ant or sig:
                f['fecha'] = ant[-1] if ant else sig[0]
                f['fecha_calidad'] = 'imputada_fila_anterior'
    return filas


def clasificar_componente(texto: str, sistema: str | None = None) -> str:
    t = _norm(texto)
    for nombre, patron in COMPONENTES:
        if re.search(patron, t):
            return nombre
    for nombre, patron in POR_SISTEMA.get(sistema, []):
        if re.search(patron, t):
            return nombre
    return 'Otro'


def clasificar_condicion(texto: str) -> str:
    t = _norm(texto)
    if REPARADA.search(t):
        return 'reparada'
    if NUEVA.search(t):
        return 'nueva'
    return 'no_especificada'


def detectar_proveedor(texto: str, alias_proveedor: dict | None = None):
    t = ' ' + _norm(texto) + ' '
    for alias, clave in (alias_proveedor or {}).items():
        if _norm(alias) in t:
            return clave
    return None


def costo_desde_texto(textos):
    montos = []
    for t in textos:
        montos += [float(x.replace(',', '')) for x in re.findall(r'\$\s?(\d[\d,]*(?:\.\d+)?)', str(t))]
    return montos[0] if len(montos) == 1 else None


def leer_hojas(ws):
    cab = [c.value for c in ws[1]]
    cols = {i: sistema_de_encabezado(h) for i, h in enumerate(cab) if sistema_de_encabezado(h)}
    i_costo = next((i for i, h in enumerate(cab) if h and _norm(h) == 'costo'), None)
    i_com = next((i for i, h in enumerate(cab) if h and _norm(h) == 'comentarios'), None)
    filas = []
    for r in ws.iter_rows(min_row=2):
        vals = [c.value for c in r]
        celdas = {cols[i]: str(vals[i]).strip() for i in cols if i < len(vals) and vals[i] not in (None, '')}
        costo_raw = vals[i_costo] if i_costo is not None and i_costo < len(vals) else None
        com = vals[i_com] if i_com is not None and i_com < len(vals) else None
        fecha_raw = vals[0]
        if not celdas and costo_raw in (None, '') and com in (None, ''):
            if isinstance(fecha_raw, str) and fecha_raw.strip():
                filas.append(dict(fecha_raw=None, celdas={}, costo_raw=None, comentario=None, nota=fecha_raw, fila=r[0].row))
            continue
        filas.append(dict(fecha_raw=fecha_raw, celdas=celdas, costo_raw=costo_raw, comentario=com, nota=None, fila=r[0].row))
    # Los textos en la columna FECHA que no son fecha son notas de la fila anterior: se descartan.
    return [f for f in filas if f['nota'] is None]


def procesar_libro(wb, alias_proveedor: dict | None = None):
    """Devuelve (DataFrame limpio, dict de auditoría)."""
    alias_proveedor = cargar_alias() if alias_proveedor is None else alias_proveedor
    registros = []
    contadores = Counter()
    menciones = Counter()
    for ws in wb.worksheets:
        m = re.search(r'CAMION\s*(\d+)', ws.title.upper())
        if not m:
            continue
        camion = f'C{int(m.group(1))}'
        filas = resolver_fechas(leer_hojas(ws))
        for f in filas:
            contadores['intervenciones_leidas'] += 1
            textos = list(f['celdas'].values()) + [f['comentario']]
            costo, origen, proveedor_txt = None, 'sin_dato', None
            raw = f['costo_raw']
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                costo, origen = float(raw), 'registrado'
            elif isinstance(raw, str) and raw.strip():
                proveedor_txt = raw
                contadores['formato_texto_en_columna_costo'] += 1
                num = re.sub(r'[^\d.]', '', raw)
                if num:
                    costo, origen = float(num), 'registrado'
            if costo is None:
                c = costo_desde_texto(textos)
                if c is not None:
                    costo, origen = c, 'extraido_de_texto'
                    contadores['formato_costo_en_texto'] += 1
            servicio = f['celdas'].get('Servicio preventivo', '')
            intervalo = None
            num_serv = re.search(r'\b(250|500|750|1000)\b', servicio)
            if num_serv:
                intervalo = int(num_serv.group(1))
            if costo is None and re.fullmatch(r'\d{3,}', servicio or '') and not intervalo and proveedor_txt:
                costo, origen = float(servicio), 'registrado'
                contadores['formato_costo_en_columna_servicio'] += 1
            sistemas = list(f['celdas']) or ['Sin clasificar']
            if f['fecha_calidad'] not in ('ok',):
                contadores['fecha_' + f['fecha_calidad']] += 1
            if f.get('orden_alterado'):
                contadores['orden_alterado'] += 1
            prov = detectar_proveedor(' '.join(str(t) for t in textos + [proveedor_txt] if t), alias_proveedor)
            if prov:
                menciones[prov] += 1
            for s in sistemas:
                texto = f['celdas'].get(s, '')
                registros.append(dict(
                    camion_id=camion, fecha=f['fecha'], fecha_calidad=f['fecha_calidad'], sistema=s,
                    componente=clasificar_componente(texto or ' '.join(str(t) for t in textos if t), s),
                    condicion_pieza=clasificar_condicion(texto), proveedor_clave=prov,
                    costo_mxn_intervencion=costo, costo_origen=origen, n_sistemas=len(sistemas),
                    costo_mxn=(costo / len(sistemas)) if costo is not None else np.nan,
                    intervalo_servicio_h=intervalo, _fila=f['fila'], _texto=_norm(texto)))
    df = pd.DataFrame(registros)
    n_raw = len(df)
    # Duplicados exactos (mismo camión, fecha, sistema y texto).
    dup = df.duplicated(['camion_id', 'fecha', 'sistema', '_texto', '_fila'], keep='first')
    contadores['duplicados'] = int(dup.sum())
    df = df.loc[~dup].copy()
    # Negativos: no se corrigen, se reportan.
    contadores['negativos'] = int((df.costo_mxn.fillna(0) < 0).sum())
    # Atípicos: regla de 3 rangos intercuartílicos sobre intervenciones con costo.
    inter = df.drop_duplicates(['camion_id', '_fila']).costo_mxn_intervencion.dropna()
    q1, q3 = inter.quantile([.25, .75])
    limite = q3 + 3 * (q3 - q1)
    df['atipico'] = df.costo_mxn_intervencion.gt(limite)
    contadores['atipicos'] = int(df.drop_duplicates(['camion_id', '_fila']).atipico.sum())
    orden = [k for k, _ in menciones.most_common()]
    codigos = {k: f'P{i + 1:02d}' for i, k in enumerate(orden)}
    df['proveedor_codigo'] = df.proveedor_clave.map(codigos).fillna('sin_dato')
    df['fecha'] = pd.to_datetime(df.fecha)
    df = df.sort_values(['camion_id', 'fecha', '_fila', 'sistema']).reset_index(drop=True)
    df['evento_id'] = df.camion_id + '-' + df.groupby('camion_id')._fila.rank(method='dense').astype(int).astype(str).str.zfill(3)
    # Vida útil observada: días entre cambios del mismo componente en el mismo camión.
    ev = df.drop_duplicates(['camion_id', 'componente', 'fecha'])
    ev = ev[~ev.componente.isin(['Servicio preventivo', 'Otro', 'Cabina y estética'])]
    ev = ev.sort_values(['camion_id', 'componente', 'fecha'])
    ev['dias_desde_cambio_anterior'] = ev.groupby(['camion_id', 'componente']).fecha.diff().dt.days
    df = df.merge(ev[['camion_id', 'componente', 'fecha', 'dias_desde_cambio_anterior']].drop_duplicates(['camion_id', 'componente', 'fecha']),
                  on=['camion_id', 'componente', 'fecha'], how='left')
    # Un nuevo trabajo en el mismo componente dentro de 30 días se trata como reincidencia (falla repetida);
    # los intervalos mayores se usan como vida útil observada entre cambios.
    df['reincidencia_30d'] = df.dias_desde_cambio_anterior.le(30)
    df['vida_util_dias'] = df.dias_desde_cambio_anterior.where(df.dias_desde_cambio_anterior.gt(30))
    inter_df = df.drop_duplicates(['camion_id', 'evento_id'])
    auditoria = {
        'intervenciones_leidas': int(contadores['intervenciones_leidas']),
        'registros_raw': n_raw, 'registros_clean': len(df),
        'duplicados': int(contadores['duplicados']),
        'negativos': int(contadores['negativos']),
        'atipicos': int(contadores['atipicos']), 'limite_atipico_mxn': float(limite),
        'nulos_costo': int(inter_df.costo_mxn_intervencion.isna().sum()),
        'intervenciones': int(len(inter_df)),
        'nulos_fecha_imputados': int(contadores['fecha_imputada_fila_anterior']),
        'formato': {
            'fechas_texto_interpretadas': int(contadores['fecha_texto_interpretado']),
            'fechas_anio_corregido': int(contadores['fecha_anio_corregido']),
            'fechas_solo_anio': int(contadores['fecha_solo_anio']),
            'filas_con_orden_alterado_conservadas': int(contadores['orden_alterado']),
            'texto_en_columna_costo': int(contadores['formato_texto_en_columna_costo']),
            'costo_extraido_de_texto': int(contadores['formato_costo_en_texto']),
            'costo_en_columna_servicio': int(contadores['formato_costo_en_columna_servicio']),
        },
        'proveedores_codificados': len(codigos),
    }
    auditoria['formato_total'] = int(sum(v for k, v in auditoria['formato'].items() if k not in ('costo_extraido_de_texto', 'filas_con_orden_alterado_conservadas'))) + int(contadores['formato_costo_en_texto'])
    cols = ['evento_id', 'camion_id', 'fecha', 'fecha_calidad', 'sistema', 'componente', 'condicion_pieza',
            'proveedor_codigo', 'costo_mxn_intervencion', 'costo_mxn', 'costo_origen', 'n_sistemas', 'intervalo_servicio_h',
            'dias_desde_cambio_anterior', 'reincidencia_30d', 'vida_util_dias', 'atipico']
    out = df[cols].copy()
    out['fecha'] = out.fecha.dt.strftime('%Y-%m-%d')
    out['tipo_pieza'] = 'por_capturar'  # OEM vs genérica: no existe en el historial actual
    out['naturaleza_dato'] = 'real'
    mapa = {v: k for k, v in codigos.items()}
    return out, auditoria, mapa
