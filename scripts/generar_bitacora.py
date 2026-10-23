"""Generador de bitácora sintética de maquinaria minera (respaldo mientras llegan los datos reales).
Simula 24 meses de bitácora diaria de una flota de 10 equipos, con errores sembrados para practicar limpieza."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
dias = pd.date_range("2024-10-01", "2026-09-30", freq="D")
equipos = {
    "CAM-01": ("Camión", 0.9), "CAM-02": ("Camión", 1.1), "CAM-03": ("Camión", 1.4),
    "CAR-01": ("Cargador", 1.0), "CAR-02": ("Cargador", 1.3),
    "EXC-01": ("Excavadora", 0.8), "EXC-02": ("Excavadora", 1.2),
    "MOT-01": ("Motoconformadora", 0.7), "PER-01": ("Perforadora", 1.1), "RET-01": ("Retroexcavadora", 0.9),
}
componentes = {"Manguera": 0.22, "Aceite/fugas": 0.18, "Gato hidráulico": 0.08, "Joystick": 0.07,
               "Motor": 0.10, "Aire acondicionado": 0.10, "Llantas/orugas": 0.15, "Sistema eléctrico": 0.10}
comp_n, comp_p = list(componentes), np.array(list(componentes.values()))
horas_comp = {"Manguera": 6, "Aceite/fugas": 8, "Gato hidráulico": 40, "Joystick": 12, "Motor": 60,
              "Aire acondicionado": 14, "Llantas/orugas": 20, "Sistema eléctrico": 16}
espera = {"Gato hidráulico": 35, "Motor": 20, "Joystick": 5, "Manguera": 1, "Aceite/fugas": 1,
          "Aire acondicionado": 4, "Llantas/orugas": 7, "Sistema eléctrico": 6}
filas = []
horo = {e: float(rng.integers(3000, 9000)) for e in equipos}
for e, (tipo, riesgo) in equipos.items():
    fuera_hasta = None
    for d in dias:
        if fuera_hasta is not None and d <= fuera_hasta:
            filas.append([d.date(), e, tipo, round(horo[e], 1), 0.0, 24.0, "Fuera de servicio", "", "", np.nan, np.nan, "Sí"])
            continue
        fuera_hasta = None
        lluvia = 1.25 if d.month in (7, 8, 9) else 1.0            # temporada de lluvias
        fin_sem = 0.6 if d.weekday() == 6 else 1.0
        horas_op = float(np.clip(rng.normal(16 * fin_sem, 2), 0, 22))
        horo[e] += horas_op
        p_falla = 0.016 * riesgo * lluvia * (1 + horo[e] / 20000)
        if rng.random() < p_falla:
            c = rng.choice(comp_n, p=comp_p)
            h = float(max(2, rng.normal(horas_comp[c], horas_comp[c] * 0.25)))
            dias_esp = int(max(0, rng.poisson(espera[c])))
            enstock = "Sí" if (c in ("Manguera", "Aceite/fugas", "Joystick") and rng.random() < 0.85) else "No"
            if enstock == "Sí":
                dias_esp = 0
            costo = round(float(rng.gamma(2.0, {"Motor": 60000, "Gato hidráulico": 25000}.get(c, 4000))), 2)
            filas.append([d.date(), e, tipo, round(horo[e], 1), round(horas_op, 1), round(h + dias_esp * 24, 1),
                          "Correctivo", c, "Falla", dias_esp, costo, "Sí" if rng.random() < 0.8 else "Pendiente"])
            fuera_hasta = d + pd.Timedelta(days=max(0, int((h + dias_esp * 24) // 24)))
        else:
            prev = "Preventivo" if horo[e] // 250 != (horo[e] - horas_op) // 250 else "Operación"
            filas.append([d.date(), e, tipo, round(horo[e], 1), round(horas_op, 1), 0.5 if prev == "Preventivo" else 0.0,
                          prev, "", "", np.nan, np.nan, "Sí"])
cols = ["fecha", "equipo_id", "tipo_equipo", "horometro", "horas_operadas", "horas_fuera_servicio",
        "tipo_evento", "componente", "falla", "dias_espera_pieza", "costo_reparacion_mxn", "validado"]
df = pd.DataFrame(filas, columns=cols)
df["falla"] = df["falla"].replace("", "No").replace({"Falla": "Sí"})
df.loc[df["tipo_evento"] != "Correctivo", "falla"] = "No"
df.loc[df["tipo_evento"] == "Fuera de servicio", "falla"] = "No"

n = len(df)
df.loc[rng.choice(n, 40, replace=False), "horas_operadas"] = np.nan                       # 1. nulos
df.loc[rng.choice(n, 15, replace=False), "horas_operadas"] *= -1                          # 2. negativos
df.loc[rng.choice(n, 10, replace=False), "horas_operadas"] = 999                          # 3. atípicos
idx = rng.choice(n, 25, replace=False)
df.loc[idx, "equipo_id"] = df.loc[idx, "equipo_id"].str.lower()                           # 4. formato
df = pd.concat([df, df.sample(30, random_state=1)])                                       # 5. duplicados
df = df.sample(frac=1, random_state=2).reset_index(drop=True)
df.to_csv("bitacora_maquinaria.csv", index=False)
print(f"Generados {len(df):,} registros en bitacora_maquinaria.csv")
