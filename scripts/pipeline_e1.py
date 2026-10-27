"""Pipeline E1 de MineTrac (solo información real de Máquinas Centella).

1) Leemos la bitácora de reparaciones de los camiones y la limpia (services/worker/etl_bitacora.py).
2) Leemos el catálogo de equipos (EQUIPOS MAQ CENTELLA.xlsx).
3) Calculamos indicadores y FFT de las intervenciones diarias.
4) Guardamos data/raw, data/clean, data/sample y docs/auditoria.csv.

No simulamos datos: la operación (horas, toneladas, tarifas, ingresos) está pendiente de entrega por la empresa.

Uso (desde la raíz del repositorio):
    python scripts/pipeline_e1.py --equipos "EQUIPOS MAQ CENTELLA.xlsx" --camiones "CAMIONES 12M3 Y 14M3.xlsx"
"""
from pathlib import Path
import argparse, json, re, shutil, sys
import pandas as pd
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/tablero'))
sys.path.insert(0, str(ROOT / 'services/worker'))
from core import resumen, serie_diaria, spectral   # noqa: E402
from etl_bitacora import procesar_libro            # noqa: E402

CATEGORIAS = {'K': 'Cargador', 'M': 'Minicargador', 'R': 'Retroexcavadora', 'C': 'Camión'}


def leer_catalogo(path):
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    filas = []
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and re.fullmatch(r'[KMRC]\d+', c.value.strip()):
                modelo = ws.cell(row=c.row, column=c.column + 1).value
                filas.append(dict(equipo_id=c.value.strip(), categoria=CATEGORIAS[c.value.strip()[0]],
                                  modelo=str(modelo).strip() if modelo is not None else ''))
    cat = pd.DataFrame(filas).drop_duplicates('equipo_id')
    cat['orden'] = cat.equipo_id.str[0].map({'C': 0, 'K': 1, 'M': 2, 'R': 3}) * 100 + cat.equipo_id.str[1:].astype(int)
    return cat.sort_values('orden').drop(columns='orden').reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--equipos', default=str(next((ROOT / 'data/raw').glob('EQUIPOS*.xlsx'), 'data/raw/EQUIPOS.xlsx')))
    ap.add_argument('--camiones', default=str(next((ROOT / 'data/raw').glob('CAMIONES*.xlsx'), 'data/raw/CAMIONES.xlsx')))
    a = ap.parse_args()
    for f in ['data/raw', 'data/clean', 'data/sample', 'docs']:
        (ROOT / f).mkdir(parents=True, exist_ok=True)
    for src in (a.equipos, a.camiones):  # copia de los originales (carpeta ignorada por git)
        dst = ROOT / 'data/raw' / Path(src).name
        if Path(src).resolve() != dst.resolve():
            shutil.copy(src, dst)

    mant, aud, mapa = procesar_libro(openpyxl.load_workbook(a.camiones, data_only=True))
    mant.to_csv(ROOT / 'data/clean/mantenimiento.csv', index=False, encoding='utf-8-sig')
    (ROOT / 'data/raw/mapa_proveedores_PRIVADO.json').write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding='utf-8')

    cat = leer_catalogo(a.equipos)
    cat.assign(naturaleza_dato='real', validacion='pendiente_empresa').to_csv(ROOT / 'data/clean/inventario.csv', index=False, encoding='utf-8-sig')

    serie = serie_diaria(mant, inicio='2024-04-01')
    spec, picos = spectral(serie)
    spec.to_csv(ROOT / 'data/clean/fft.csv', index=False)
    resultados = {
        'auditoria_bitacora': aud, 'kpis': resumen(mant), 'picos_fft': picos,
        'serie': {'inicio': str(serie.index.min().date()), 'fin': str(serie.index.max().date()), 'dias': int(len(serie))},
        'inventario': {'equipos': int(len(cat)), 'por_categoria': cat.categoria.value_counts().to_dict()},
        'bitacora': {'inicio': mant.fecha.min(), 'fin': mant.fecha.max(), 'camiones': int(mant.camion_id.nunique())},
    }
    (ROOT / 'data/clean/resultados.json').write_text(json.dumps(resultados, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    f = aud['formato']
    pd.DataFrame([
        ['nulos', aud['nulos_costo'] + aud['nulos_fecha_imputados'], aud['nulos_costo']],
        ['duplicados', aud['duplicados'], 0], ['negativos', aud['negativos'], 0],
        ['atipicos', aud['atipicos'], aud['atipicos']], ['formato', aud['formato_total'], 0],
    ], columns=['error', 'detectados', 'residuales']).to_csv(ROOT / 'docs/auditoria.csv', index=False)

    # Muestra pública (sin texto libre ni nombres)
    mant.drop(columns=['naturaleza_dato']).head(60).to_csv(ROOT / 'data/sample/mantenimiento_muestra.csv', index=False)
    cat.to_csv(ROOT / 'data/sample/inventario.csv', index=False)
    print(json.dumps({k: resultados[k] for k in ['auditoria_bitacora', 'kpis', 'picos_fft', 'serie']}, ensure_ascii=False, indent=1, default=str))
    return resultados


if __name__ == '__main__':
    main()
