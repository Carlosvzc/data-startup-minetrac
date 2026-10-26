
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/tablero'))
from core import clean_data,metrics,spectral
rng=np.random.default_rng(42)
for folder in ['data/raw','data/clean','data/sample','docs']: (ROOT/folder).mkdir(parents=True,exist_ok=True)
catalog=pd.read_csv(ROOT/'data/sample/inventario.csv',dtype=str)
catalog.to_csv(ROOT/'data/clean/inventario.csv',index=False)
dates=pd.date_range('2025-08-01',periods=420,freq='D')
rows=[]
for j,e in catalog.iterrows():
    category=e.categoria
    rate={'Cargador':1250,'Camión':55,'Minicargador':750,'Retroexcavadora':950}[category]
    rate*=1+0.025*(j%4)
    mode='tonelada' if category=='Camión' else 'hora'
    productivity=20+(j%4)*2
    variable={'Cargador':490,'Camión':480,'Minicargador':245,'Retroexcavadora':350}[category]
    horo=3000+j*720
    for t,day in enumerate(dates):
        scheduled=12.
        stop=round(float(rng.choice([0,0,0,0,0.5,1,2])),2)
        hours=6.3+1.15*np.cos(2*np.pi*t/7)+0.72*np.cos(2*np.pi*t/15)+0.0008*t+rng.normal(0,0.20)+(j%3)*0.08
        hours=round(float(np.clip(hours,0,scheduled-stop)),4)
        maintenance=float(rng.integers(1000,8001)) if rng.random()<0.035 else 0.
        rows.append(dict(registro_id=f'{e.equipo_id}-{day:%Y%m%d}',equipo_id=e.equipo_id,categoria=category,
                         fecha=day.strftime('%Y-%m-%d'),ubicacion=['Pista','Peña','Carretera'][j%3],
                         modalidad_cobro=mode,horas_programadas_h=scheduled,horas_paro_h=stop,
                         horas_trabajadas_h=hours,productividad_t_h=productivity,tarifa_mxn=round(rate,2),
                         costo_variable_mxn_h=variable,costo_fijo_mxn_dia=180+10*(j%4),
                         costo_mantenimiento_mxn=maintenance,naturaleza_dato='simulado',semilla=42))
pristine=pd.DataFrame(rows)
idx=rng.choice(len(pristine),90,replace=False)
dirty=pristine.copy()
dirty.loc[idx[:40],'horas_trabajadas_h']=np.nan
dirty.loc[idx[40:55],'horas_trabajadas_h']*=-1
dirty.loc[idx[55:65],'horas_trabajadas_h']=99
dirty.loc[idx[65:90],'equipo_id']=' '+dirty.loc[idx[65:90],'equipo_id'].str.lower()+' '
# Duplicate only unaffected rows so exact expected defect counts stay disjoint.
candidate=dirty.drop(index=idx)
dirty=pd.concat([dirty,candidate.sample(30,random_state=42)],ignore_index=True).sample(frac=1,random_state=7).reset_index(drop=True)
dirty.to_csv(ROOT/'data/raw/operacion_simulada_raw.csv',index=False)
clean,audit=clean_data(dirty)
clean.to_csv(ROOT/'data/clean/operacion.csv',index=False)
clean.loc[clean.motivo_correccion.ne('ninguno'),['registro_id','horas_originales_h','horas_trabajadas_h','motivo_correccion']].to_csv(ROOT/'docs/correcciones.csv',index=False)
pd.DataFrame({'error':['nulos','duplicados','negativos','atipicos','formato'],
              'detectados':[audit[k] for k in ['nulos','duplicados','negativos','atipicos','formato']],
              'residuales':[0]*5}).to_csv(ROOT/'docs/auditoria.csv',index=False)
spec,peaks=spectral(clean);spec.to_csv(ROOT/'data/clean/fft.csv',index=False)
report={'generacion':{'semilla':42,'dias':420,'equipos':21,'inicio':str(dates[0].date()),'fin':str(dates[-1].date()),'ciclos_inyectados_dias':[7,15]},
        'auditoria':audit,'kpis':metrics(clean),'picos_fft':peaks,
        'error_imputacion_mae_h':float(np.abs(clean.set_index('registro_id').horas_trabajadas_h-pristine.set_index('registro_id').horas_trabajadas_h).mean())}
(ROOT/'data/clean/resultados.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
clean.head(63).to_csv(ROOT/'data/sample/operacion_muestra.csv',index=False)
manifest=[]
for p in (ROOT/'data').rglob('*'):
    if p.is_file():manifest.append({'archivo':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'docs/manifiesto.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
assert audit=={'filas_raw':8850,'filas_clean':8820,'duplicados':30,'formato':25,'nulos':40,'negativos':15,'atipicos':10},audit
assert abs(peaks[0]['periodo_dias']-7)<0.2 and abs(peaks[1]['periodo_dias']-15)<0.2,peaks
print(json.dumps(report,ensure_ascii=False,indent=2))



