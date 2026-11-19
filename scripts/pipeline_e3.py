"""Gráficas del E3 a partir de los artefactos de services/modelos/artefactos/. Uso: python scripts/pipeline_e3.py"""
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.modelos import modelos as m          # noqa: E402
from services.worker.analitica import acf_pacf      # noqa: E402

ART = ROOT / 'services/modelos/artefactos'
OUT = ROOT / 'docs/evidencias/e3'
INK, GOLD, STEEL = '#1f2328', '#f2b600', '#9aa6b0'
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#c9cfd4', 'figure.dpi': 130})


def guardar(fig, nombre):
    fig.tight_layout(); fig.savefig(OUT / nombre, bbox_inches='tight', facecolor='white'); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    serie = pd.read_csv(ART / 'serie_semanal.csv', index_col=0, parse_dates=True).iloc[:, 0]
    serie.index = pd.DatetimeIndex(serie.index, freq='W-MON')
    r = json.loads((ART / 'metricas_e3.json').read_text(encoding='utf-8'))

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.3))
    for a, (x, t) in zip(ax, [(serie, 'Serie original'), (serie.diff().dropna(), 'Primera diferencia')]):
        ap = acf_pacf(x, 20)
        a.bar(range(21), ap['acf'], color=INK, width=.5); a.axhspan(-ap['banda'], ap['banda'], color=GOLD, alpha=.3)
        a.set_title('ACF · ' + t, loc='left', fontsize=10.5, fontweight='bold'); a.set_xlabel('Rezago (semanas)')
    guardar(fig, 'acf_diferencia.png')

    p30 = m.pronosticar(serie, 4)
    p12 = m.pronosticar(serie, 12)
    fig, ax = plt.subplots(figsize=(10, 3.6))
    h = serie.iloc[-40:]
    ax.bar(h.index, h.values, width=5, color='#c9ced3', label='Registrado')
    f = pd.to_datetime(p12.semana)
    ax.fill_between(f, p12.inferior, p12.superior, color=GOLD, alpha=.18, label='Banda 95 % (hasta 12 semanas)')
    f4 = pd.to_datetime(p30.semana)
    ax.fill_between(f4, p30.inferior, p30.superior, color=GOLD, alpha=.45, label='Banda 95 % (30 días)')
    ax.plot(f, p12.pronostico, 'o-', color=INK, ms=3, label='Pronóstico ARIMA(0,1,1)')
    ax.set_ylabel('Intervenciones por semana'); ax.legend(frameon=False, fontsize=8.5, loc='upper left')
    guardar(fig, 'pronostico.png')

    nombres = ['Naive Bayes', 'KNN (k=7)', 'SVM (núcleo RBF)', 'Árbol de decisión (profundidad 3)']
    fig, ax = plt.subplots(1, 4, figsize=(11, 2.9))
    for a, k in zip(ax, nombres):
        cm = np.array(r['clasificador']['modelos'][k]['matriz_confusion'])
        a.imshow(cm, cmap='Greys', vmin=0, vmax=40); a.set_title(k.replace(' (profundidad 3)', ''), fontsize=9)
        for i in range(2):
            for j in range(2):
                a.text(j, i, cm[i, j], ha='center', va='center', fontsize=13, color=GOLD if cm[i, j] > 20 else INK)
        a.set_xticks([0, 1]); a.set_yticks([0, 1]); a.set_xticklabels(['No', 'Sí']); a.set_yticklabels(['No', 'Sí'])
        a.set_xlabel('Predicho'); a.set_ylabel('Real')
        for s in a.spines.values(): s.set_visible(False)
    guardar(fig, 'matrices_confusion.png')
    print('gráficas en', OUT)


if __name__ == '__main__':
    main()
