"""ETL de la libreta manuscrita de Máquinas Centella.

Entrada: la transcripción en Markdown (un renglón por anotación, equipos con encabezado «## K2 (...)»).
Salida: una tabla con un evento por renglón, sin texto libre, con proveedores anonimizados.

Reglas:
- No inventamos datos. Lo que no se puede leer o interpretar queda vacío y se marca en una columna de calidad.
- El año de una fecha sin año se infiere por el orden de la libreta (cronológico dentro de cada equipo).
- El monto solo se toma cuando el renglón trae una sola cifra en pesos; si trae varias (cotizaciones, desglose) queda
  vacío y se cuenta en `n_montos`, para no sumar alternativas como si fueran gastos.
"""
import re
import unicodedata
import pandas as pd

MESES = {'ene': 1, 'enero': 1, 'feb': 2, 'febrero': 2, 'mar': 3, 'marzo': 3, 'abr': 4, 'abril': 4, 'may': 5, 'mayo': 5,
         'jun': 6, 'junio': 6, 'jul': 7, 'julio': 7, 'ago': 8, 'agosto': 8, 'sep': 9, 'sept': 9, 'septiembre': 9,
         'oct': 10, 'octubre': 10, 'nov': 11, 'noviembre': 11, 'dic': 12, 'diciembre': 12}
CATEGORIAS = {'K': 'Cargador', 'M': 'Minicargador', 'R': 'Retroexcavadora', 'T': 'Tractor'}

PROVEEDORES = ['Tracsa', 'Cudave', 'Cadeco', 'Lypasa', 'Apymsa', 'Retromack', 'Potencia Fluida', 'Binosa', 'Caterpillar']
SISTEMAS = [  # el orden importa: se toma el primero que coincida
    ('Servicio preventivo', r'\bservicio\b(?!.*(de|del) (bomba|diferencial))|filtros? (nuevos|de aceite)|cambio de aceite'),
    ('Llantas', r'llanta|neum[aá]tic|rin\b'),
    ('Frenos', r'freno|chamber|balata|discos'),
    ('Enfriamiento y A/C', r'radiador|termostato|bomba de agua|postenfriador|enfriador|evaporador|compresor|a/c|clima|condensador|siroco|calent[oó]n|ventilador'),
    ('Combustible y motor', r'diesel|inyector|riel|turbo|motor|cabeza|pistones|[aá]rbol de levas|egr|escape|silenciador|cig[uü]e[nñ]al|cilindro|desforzad|compresi[oó]n|rectificaci'),
    ('Transmisión y tren motriz', r'transmisi[oó]n|diferencial|yugo|cruceta|flecha|cardan|cardán|cople|convertidor|eje trasero|balanc[ií]n|sprock|rueda guía|rodillo|cadena|zapata'),
    ('Hidráulico y dirección', r'hidr[aá]ulic|bote|gato|dirección|manguera|cucharón|bomba de levante|fuga de aceite|sellos?|ret[eé]n|liga de bomba'),
    ('Eléctrico y electrónico', r'alternador|bater[ií]a|rel[eé]|joystick|sensor|display|bobina|selenoide|solenoide|electrov|fusible|switch|interruptor|computadora|software|monitor|cable|foco|faro|luces|limpiabrisas|acumulador|arranque|marcha'),
    ('Implementos y estructura', r'cuchilla|gavil[aá]n|punta|bayoneta|cucharón|soldad|refuerz|placa|bujes?|pernos?|chumacera|puerta|capó|asiento|cristal|cabina|pintura|vidrio|protector|ripper'),
]
TIPOS_EVENTO = [
    ('Servicio preventivo', r'\bservicio\b(?! (de )?(bomba|diferencial))|cambio de filtros|cambio de aceite'),
    ('Diagnóstico o revisión', r'revis|diagn[oó]stic|prueba|cotiz|checar|verific|descubrir|detect|calibr'),
    ('Compra de refacción', r'compra|se compr|nuevo|nueva|se pone|se le pone|se cambi|cambio|ponen|pusieron|instal'),
    ('Reparación', r'repar|solda|rectific|arregl|rellen|maquin|armó|arm[oó]|sell[oó]|lav[óo]|lavad'),
    ('Falla reportada', r'falla|fuga|roto|rota|tron[oó]|truena|ruido|no funciona|no sirve|se trab|trababa|tira|tirando|desforzad|humo|sobrecalent|se calent|se paró|se par[oó]'),
]
RE_FECHA = re.compile(r'^(?P<d>\d{1,2}|\?{1,2}|\d\?)\s*/\s*(?P<m>[A-Za-zñáéíóú]+|\d{1,2}|\?|\[[^\]]*\])(?:\s*/\s*(?P<y>\d{2,4}))?')
RE_MONTO = re.compile(r'\$\s*([0-9][0-9,]*(?:\.\d+)?)(?:\s*(usd|dls|dlls))?|([0-9][0-9,]*(?:\.\d+)?)\s*(usd|dls|dlls)\b', re.I)
RE_NO_MONTO = re.compile(r'\$\s*\[\?\]')


def _norm(s):
    return unicodedata.normalize('NFC', s)


def _anio(y):
    if y is None:
        return None
    y = int(y)
    return 2000 + y if y < 100 else y


def _primer(patrones, texto, default):
    for etiqueta, pat in patrones:
        if re.search(pat, texto, re.I):
            return etiqueta
    return default


def _montos(texto):
    t = re.sub(r'\[\s*[^\]]*\]', lambda m: m.group(0) if '$' in m.group(0) else '', texto)  # quita notas, deja [$...]
    pesos, usd = [], []
    for m in RE_MONTO.finditer(t):
        v = float((m.group(1) or m.group(3)).replace(',', ''))
        if (m.group(2) or m.group(4)):
            usd.append(v)
        else:
            pesos.append(v)
    return pesos, usd


def _intervalo_servicio(texto):
    m = re.search(r'servicio\s*(?:\[[^\]]*\]\s*)?(\d[\d,]{2,5})(?!\s*\$)', texto, re.I)
    if m:
        v = int(m.group(1).replace(',', ''))
        if v in (250, 500, 750, 1000, 1500, 2000, 3000):
            return v
    return None


def _tipo_pieza(texto):
    t = texto.lower()
    if 'mercado negro' in t:
        return 'mercado_negro'
    if re.search(r'\breman', t):
        return 'remanufacturada'
    if re.search(r'original', t):
        return 'original'
    if re.search(r'\busad[ao]|del inventario|de inventario', t):
        return 'usada_o_inventario'
    if re.search(r'\bnuev[oa]s?\b', t):
        return 'nueva_sin_especificar'
    return 'sin_dato'


def _anio_inicial(texto):
    """Año con el que empieza cada libreta: el primer año escrito entre sus primeras anotaciones."""
    out, eq, n = {}, None, 0
    for linea in texto.splitlines():
        m = re.match(r'##\s+([KMRT]\d+)\b', linea)
        if m:
            eq, n = m.group(1), 0
            continue
        if eq and eq not in out and linea.startswith('- '):
            n += 1
            f = RE_FECHA.match(linea[2:].strip())
            if f and f.group('y') and 'así escrito' not in linea:
                out[eq] = _anio(f.group('y'))
            elif n >= 10:
                out[eq] = 2024
    return out


def parsear(texto, mapa_proveedores=None):
    """Devuelve (DataFrame de eventos, dict de auditoría, mapa de proveedores usado)."""
    mapa = dict(mapa_proveedores or {})
    filas, equipo, previo, sec = [], None, None, {}
    texto = _norm(texto)
    inicio = _anio_inicial(texto)
    for linea in texto.splitlines():
        m_eq = re.match(r'##\s+([KMRT]\d+)\b', linea)
        if m_eq:
            equipo, previo = m_eq.group(1), None
            continue
        if equipo is None or not linea.startswith('- '):
            continue
        cuerpo = linea[2:].strip()
        if cuerpo.startswith('*(') and 'Horómetro' not in cuerpo:
            continue
        sec[equipo] = sec.get(equipo, 0) + 1
        m = RE_FECHA.match(cuerpo)
        dia = mes = anio_esc = None
        calidad = 'sin_fecha'
        resto = cuerpo
        if m:
            resto = cuerpo[m.end():].lstrip(' :')
            resto = re.sub(r'^\[[^\]]*\]\s*(?:\([^)]*\)\s*)?:?\s*', '', resto) if resto.startswith('[') and ']' in resto[:60] and ':' in resto[:80] else resto
            d, mm, y = m.group('d'), m.group('m'), m.group('y')
            dia = int(d) if d.isdigit() else None
            if mm.isdigit():
                mes = int(mm)
            else:
                mes = MESES.get(mm.lower().strip('[]'))
            anio_esc = _anio(y)
            calidad = 'ok'
        elif re.match(r'^[a-záéíóú]+ \[de \d{4}', cuerpo, re.I):
            mm = re.match(r'^([a-záéíóú]+) \[de (\d{4})', cuerpo, re.I)
            mes, anio_esc, calidad = MESES.get(mm.group(1).lower()), int(mm.group(2)), 'mes_sin_dia'
            resto = cuerpo.split(']', 1)[-1].lstrip(' :')
        if mes is None and calidad != 'sin_fecha':
            calidad = 'mes_ilegible'
        # año: explícito o inferido por el orden de la libreta
        anio = None
        if mes is not None:
            if previo is None:
                anio = anio_esc or inicio.get(equipo, 2024)
                if anio_esc is None:
                    calidad = 'anio_inferido'
            else:
                py, pm = previo
                inferido = py + (1 if mes < pm - 2 else 0)
                pista = re.search(r'(?:probablemente|sugiere)\s+(20\d\d)', cuerpo)
                if pista:
                    anio, calidad = int(pista.group(1)), 'anio_corregido'
                elif 'así escrito' in cuerpo and anio_esc is not None:
                    anio, calidad = inferido, 'anio_corregido'
                elif anio_esc is None:
                    anio, calidad = inferido, ('anio_inferido' if calidad == 'ok' else calidad)
                elif anio_esc + 1 < py or anio_esc < py:   # año hacia atrás: error de escritura, usamos el orden
                    anio, calidad = inferido, 'anio_corregido'
                elif anio_esc > inferido + 1:
                    anio, calidad = inferido, 'anio_corregido'
                else:
                    anio = anio_esc
            previo = (anio, mes)
        fecha = None
        if anio and mes:
            try:
                fecha = pd.Timestamp(anio, mes, dia if dia else 1).date().isoformat()
            except ValueError:
                fecha = pd.Timestamp(anio, mes, 1).date().isoformat()
                calidad = 'dia_corregido'
            if dia is None and calidad == 'ok':
                calidad = 'dia_desconocido'
        texto_e = resto
        pesos, usd = _montos(texto_e)
        prov = [p for p in PROVEEDORES if re.search(re.escape(p), texto_e, re.I)]
        for p in prov:
            mapa.setdefault(p, f'P{len(mapa) + 1:02d}')
        sistema = _primer(SISTEMAS, texto_e, 'Sin clasificar')
        tipo = _primer(TIPOS_EVENTO, texto_e, 'Otro')
        if re.search(r'^\s*(servicio)\b', texto_e, re.I) or re.search(r'\bservicio\s*\d', texto_e, re.I):
            tipo, sistema = 'Servicio preventivo', 'Servicio preventivo'
        mencion_equipos = sorted({e for e in re.findall(r'\b([KMRT]\d{1,2})\b', texto_e) if e != equipo})
        t = texto_e.lower()
        filas.append(dict(
            equipo_id=equipo, categoria=CATEGORIAS[equipo[0]], orden_en_libreta=sec[equipo], fecha=fecha, fecha_calidad=calidad,
            tipo_evento=tipo, sistema=sistema,
            intervalo_servicio_h=_intervalo_servicio(texto_e),
            n_montos=len(pesos) + len(usd),
            monto_mxn=pesos[0] if len(pesos) == 1 and not usd else None,
            monto_usd=usd[0] if len(usd) == 1 and not pesos else None,
            proveedor_codigo=mapa[prov[0]] if prov else 'sin_dato',
            tipo_pieza=_tipo_pieza(texto_e),
            es_servicio=tipo == 'Servicio preventivo',
            desforzado=bool(re.search(r'desforzad', t)),
            garantia=bool(re.search(r'garant[ií]a', t)),
            urgencia=bool(re.search(r'urgencia|urgente', t)),
            canibalizacion=bool(re.search(r'(del|al|de|para|a) (el )?[KMRT]\d{1,2}\b', texto_e) and re.search(r'quit|pas[óo]|pasaron|pusieron|puso|pone|ponerl|prest|cambio|canibal|se le pone|ponerselo', t)),
            equipos_mencionados=','.join(mencion_equipos),
            horometro=(int(re.search(r'hor[oó]metro\s*([\d,]+)', texto_e, re.I).group(1).replace(',', '')) if re.search(r'hor[oó]metro\s*[\d,]{3,}', texto_e, re.I) else None),
            naturaleza_dato='real', validacion='pendiente_empresa',
        ))
    df = pd.DataFrame(filas)
    if df.empty:
        return df, {'anotaciones': 0}, mapa
    df.insert(0, 'evento_id', [f'{e}-L{n:03d}' for e, n in zip(df.equipo_id, df.orden_en_libreta)])
    aud = {
        'anotaciones': int(len(df)), 'equipos': int(df.equipo_id.nunique()),
        'con_fecha': int(df.fecha.notna().sum()), 'sin_fecha': int(df.fecha.isna().sum()),
        'calidad_fecha': df.fecha_calidad.value_counts().to_dict(),
        'con_un_monto_mxn': int(df.monto_mxn.notna().sum()), 'con_monto_usd': int(df.monto_usd.notna().sum()),
        'con_varios_montos': int((df.n_montos > 1).sum()), 'con_algun_monto': int((df.n_montos > 0).sum()),
        'servicios_con_intervalo': int(df.intervalo_servicio_h.notna().sum()),
    }
    return df, aud, mapa
