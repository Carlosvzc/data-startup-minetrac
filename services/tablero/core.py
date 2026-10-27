"""Cálculos del tablero: indicadores de la bitácora real de mantenimiento y análisis espectral (FFT)."""
import numpy as np
import pandas as pd


def eventos(m):
    """Una fila por intervención (la tabla limpia trae una fila por intervención y sistema)."""
    return m.drop_duplicates(['camion_id', 'evento_id'])


def resumen(m):
    ev = eventos(m)
    con = ev.costo_mxn_intervencion.notna()
    rep = int(m.drop_duplicates(['camion_id', 'componente', 'fecha']).reincidencia_30d.sum())
    n = len(ev)
    return {'intervenciones': n,
            'gasto_mxn': float(ev.costo_mxn_intervencion.sum()),
            'con_monto': int(con.sum()),
            'pct_con_monto': 100 * float(con.mean()) if n else 0.0,
            'promedio_mxn': float(ev.costo_mxn_intervencion.mean()) if con.any() else None,
            'reincidencias': rep,
            'pct_reincidencia': 100 * rep / n if n else 0.0}


def serie_diaria(m, inicio=None, fin=None):
    """Intervenciones por día en un calendario completo (con ceros)."""
    ev = eventos(m).copy()
    ev['fecha'] = pd.to_datetime(ev.fecha)
    if inicio is not None:
        ev = ev[ev.fecha >= pd.Timestamp(inicio)]
    if fin is not None:
        ev = ev[ev.fecha <= pd.Timestamp(fin)]
    if ev.empty:
        return pd.Series(dtype=float)
    dias = pd.date_range(ev.fecha.min(), ev.fecha.max(), freq='D')
    return ev.groupby('fecha').size().reindex(dias, fill_value=0).astype(float).rename('intervenciones')


def spectral(serie):
    """FFT de una serie diaria: quita la tendencia lineal, aplica ventana Hann y busca máximos locales."""
    if len(serie) < 30 or not (np.diff(serie.index.values).astype('timedelta64[D]').astype(int) == 1).all():
        raise ValueError('Se requieren al menos 30 días completos y consecutivos.')
    t = np.arange(len(serie))
    y = serie.to_numpy(float)
    residual = y - np.polyval(np.polyfit(t, y, 1), t)
    window = np.hanning(len(y))
    a = 2 * np.abs(np.fft.rfft(residual * window)) / window.sum()
    a[0] = 0
    if len(y) % 2 == 0:
        a[-1] /= 2
    f = np.fft.rfftfreq(len(y), d=1)
    peaks = np.where((a[1:-1] > a[:-2]) & (a[1:-1] > a[2:]))[0] + 1
    peaks = sorted(peaks, key=lambda i: a[i], reverse=True)
    peaks = [i for i in peaks if f[i] > 0 and 2 <= 1 / f[i] <= 60][:5]
    spec = pd.DataFrame({'frecuencia_ciclos_dia': f[1:], 'periodo_dias': 1 / f[1:], 'amplitud': a[1:]})
    return spec, [{'periodo_dias': float(1 / f[i]), 'amplitud': float(a[i]), 'frecuencia_ciclos_dia': float(f[i])} for i in peaks]


def recomendaciones(m, aux):
    """Tres recomendaciones de negocio calculadas con la selección actual (texto plano)."""
    r = resumen(m)
    out = []
    comp = aux['componentes']
    if len(comp):
        top = comp.iloc[0]
        out.append(('01 / REFACCIONES', f"Presupuestar {top.componente.lower()} y cotizar con más de un proveedor",
                    f"Concentra {100 * top.costo_mxn / comp.costo_mxn.sum():.0f}% del gasto con monto anotado (${top.costo_mxn:,.0f} MXN). "
                    "Pedir cotizaciones comparables antes de la siguiente compra grande."))
    else:
        out.append(('01 / REFACCIONES', 'Anotar el monto de cada reparación', 'Esta selección no tiene montos anotados, así que no se puede priorizar el gasto.'))
    por = aux['por_camion']
    lider = por.index[-1]
    out.append(('02 / FLOTA', f"Revisar el historial del camión {lider} antes de otra reparación mayor",
                f"Acumula {int(por.total.iloc[-1])} intervenciones. En la flota, {r['reincidencias']} repeticiones ({r['pct_reincidencia']:.1f} por cada 100 intervenciones) "
                "se repitieron sobre el mismo componente en hasta 30 días: solicitar diagnóstico y validar si fueron continuaciones del mismo trabajo antes de reclamar garantía."))
    out.append(('03 / DATOS', 'Registrar monto, tipo de pieza y horómetro en cada reparación',
                f"Solo {r['pct_con_monto']:.0f}% de las intervenciones tiene monto anotado. Sin tipo de pieza (original o genérica) y horómetro al cambio "
                "no se puede calcular el costo por hora útil ni decidir qué refacción conviene."))
    return out


def ciclo_cercano(spec, dias, tolerancia=0.15):
    """Amplitud máxima del espectro cerca de un periodo (±15%) y cuántas veces supera a la mediana del espectro."""
    sp = spec[spec.periodo_dias.between(2, 60)]
    ven = sp[sp.periodo_dias.between(dias * (1 - tolerancia), dias * (1 + tolerancia))]
    if ven.empty:
        return None
    mediana = float(sp.amplitud.median())
    return {'periodo_dias': dias, 'amplitud': float(ven.amplitud.max()),
            'veces_mediana': float(ven.amplitud.max() / mediana) if mediana else None}
