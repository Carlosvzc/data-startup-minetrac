"""Análisis del E2: serie semanal, descomposición, ADF, ACF/PACF y regresión a mano (NumPy).
Escribe data/clean/e2_resultados.json y las gráficas de docs/evidencias/e2/.
    python scripts/pipeline_e2.py
"""
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/worker'))
from analitica import resultados_e2   # noqa: E402

OUT = ROOT / 'docs/evidencias/e2'
INK, GOLD, STEEL, BLUE = '#1f2328', '#f2b600', '#9aa6b0', '#3e5c76'
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#c9cfd4', 'figure.dpi': 130})


def guardar(fig, nombre):
    fig.tight_layout(); fig.savefig(OUT / nombre, bbox_inches='tight', facecolor='white'); plt.close(fig)


def graficas(r):
    OUT.mkdir(parents=True, exist_ok=True)
    f = pd.to_datetime(r['serie']['fechas'])
    s = np.array(r['serie']['valores'])
    d = r['descomposicion']
    fig, ax = plt.subplots(4, 1, figsize=(9, 8.2), sharex=True)
    for a, (t, v, c) in zip(ax, [('Serie observada: anotaciones por semana', s, INK), ('Tendencia', d['tendencia'], GOLD),
                                 ('Estacionalidad (ciclo de 52 semanas)', d['estacional'], BLUE), ('Residuo', d['residuo'], STEEL)]):
        a.plot(f, np.array(v, dtype=float), color=c, lw=1.6); a.set_title(t, loc='left', fontsize=10.5, fontweight='bold')
    guardar(fig, 'descomposicion.png')
    fig, ax = plt.subplots(2, 2, figsize=(10, 6))
    for j, (clave, tit) in enumerate([('acf_pacf', 'serie original'), ('acf_pacf_diferencia', 'primera diferencia')]):
        ap = r[clave]
        for i, (nombre, v) in enumerate([('ACF', ap['acf']), ('PACF', ap['pacf'])]):
            a = ax[i][j]; a.bar(range(len(v)), v, color=INK, width=.5); a.axhline(0, color='#888', lw=.8)
            a.axhspan(-ap['banda'], ap['banda'], color=GOLD, alpha=.25, label='banda 95%')
            a.set_title(f'{nombre} · {tit}', loc='left', fontsize=10.5, fontweight='bold'); a.set_xlabel('Rezago (semanas)')
    guardar(fig, 'acf_pacf.png')
    g = r['regresion']; fr = pd.to_datetime(g['fechas'])
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    ax[0].plot(fr, g['real'], color=STEEL, lw=1.3, label='Real'); ax[0].plot(fr, g['ajustado'], color=GOLD, lw=2, label='Ajustado (a mano)')
    ax[0].set_title('Ajuste de la regresión', loc='left', fontweight='bold'); ax[0].legend(frameon=False)
    ax[1].scatter(g['ajustado'], g['residuos'], color=INK, s=14); ax[1].axhline(0, color=GOLD, lw=1.6)
    ax[1].set_title('Residuos frente a valores ajustados', loc='left', fontweight='bold'); ax[1].set_xlabel('Valor ajustado')
    ax[2].hist(g['residuos'], bins=18, color=BLUE, edgecolor='white'); ax[2].set_title('Distribución de residuos', loc='left', fontweight='bold')
    guardar(fig, 'regresion_residuos.png')


def main():
    lib = pd.read_csv(ROOT / 'data/clean/libreta_eventos.csv')
    r = resultados_e2(lib)
    (ROOT / 'data/clean/e2_resultados.json').write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
    graficas(r)
    g = r['regresion']
    print('Semanas:', r['serie']['semanas'], '| ADF serie p=%.3f | ADF diferencia p=%.2g' % (r['adf_serie']['p_valor'], r['adf_diferencia']['p_valor']))
    print('β =', np.round(g['beta'], 4), '| R²=%.3f | DW=%.2f | coincide con sklearn:' % (g['r2'], g['durbin_watson']), r['comparacion_sklearn']['coinciden'], r['comparacion_sklearn']['max_dif_abs'])
    return r


if __name__ == '__main__':
    main()
