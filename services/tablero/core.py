
import numpy as np
import pandas as pd

def clean_data(raw):
    d=raw.copy()
    fmt=d.equipo_id.ne(d.equipo_id.str.strip().str.upper())
    formats=int(fmt.sum())
    d['equipo_id']=d.equipo_id.str.strip().str.upper()
    d['fecha']=pd.to_datetime(d.fecha,errors='raise')
    keys=['equipo_id','fecha']
    duplicate_count=int(d.duplicated(keys).sum())
    # Only exact duplicate observations can be discarded.
    if d.loc[d.duplicated(keys,keep=False)].drop_duplicates().duplicated(keys).any():
        raise ValueError('Claves duplicadas con contenido conflictivo.')
    d=d.drop_duplicates(keys).sort_values(keys).reset_index(drop=True)
    h=pd.to_numeric(d.horas_trabajadas_h,errors='coerce')
    null=h.isna();neg=h.lt(0);out=h.gt(d.horas_programadas_h-d.horas_paro_h)
    stats={'filas_raw':len(raw),'filas_clean':len(d),'duplicados':duplicate_count,'formato':formats,
           'nulos':int(null.sum()),'negativos':int(neg.sum()),'atipicos':int(out.sum())}
    d['motivo_correccion']='ninguno'
    for mask,name in [(null,'nulo'),(neg,'negativo'),(out,'atipico')]:
        d.loc[mask,'motivo_correccion']=name
    d['horas_originales_h']=h
    d['horas_trabajadas_h']=h.mask(null|neg|out)
    d['horas_trabajadas_h']=d.groupby('equipo_id').horas_trabajadas_h.transform(lambda x:x.interpolate(limit_direction='both'))
    if d.horas_trabajadas_h.isna().any():raise ValueError('Equipo sin base suficiente para imputar.')
    d['horas_trabajadas_h']=np.minimum(d.horas_trabajadas_h,d.horas_programadas_h-d.horas_paro_h).round(4)
    # These dependent fields are reconstructed only inside this synthetic scenario.
    d['toneladas_t']=np.where(d.modalidad_cobro.eq('tonelada'),d.horas_trabajadas_h*d.productividad_t_h,0).round(4)
    d['ingreso_mxn']=np.where(d.modalidad_cobro.eq('hora'),d.horas_trabajadas_h*d.tarifa_mxn,d.toneladas_t*d.tarifa_mxn).round(2)
    d['costo_operativo_mxn']=(d.horas_trabajadas_h*d.costo_variable_mxn_h+d.costo_fijo_mxn_dia).round(2)
    d['margen_directo_mxn']=(d.ingreso_mxn-d.costo_operativo_mxn-d.costo_mantenimiento_mxn).round(2)
    d['fecha']=d.fecha.dt.strftime('%Y-%m-%d')
    return d,stats

def metrics(d):
    hours=float(d.horas_trabajadas_h.sum()); scheduled=float(d.horas_programadas_h.sum())
    revenue=float(d.ingreso_mxn.sum()); maintenance=float(d.costo_mantenimiento_mxn.sum())
    return {'ingresos_mxn':revenue,
            'margen_directo_pct':100*float(d.margen_directo_mxn.sum())/revenue if revenue else None,
            'mantenimiento_mxn_h':maintenance/hours if hours else None,
            'disponibilidad_pct':100*(scheduled-float(d.horas_paro_h.sum()))/scheduled if scheduled else None,
            'horas_trabajadas':hours,'mantenimiento_mxn':maintenance,'margen_directo_mxn':float(d.margen_directo_mxn.sum())}

def spectral(d):
    daily=d.groupby('fecha',sort=True).horas_trabajadas_h.sum()
    dates=pd.to_datetime(daily.index);intervals=np.diff(dates.values).astype('timedelta64[D]').astype(int)
    if len(daily)<30 or not np.all(intervals==1):raise ValueError('Se requieren al menos 30 días completos y consecutivos.')
    t=np.arange(len(daily));y=daily.to_numpy(float)
    residual=y-np.polyval(np.polyfit(t,y,1),t)
    window=np.hanning(len(y));a=2*np.abs(np.fft.rfft(residual*window))/window.sum();a[0]=0
    if len(y)%2==0:a[-1]/=2
    f=np.fft.rfftfreq(len(y),d=1)
    # Local maxima avoid counting adjacent bins of the same broadened peak.
    peaks=np.where((a[1:-1]>a[:-2])&(a[1:-1]>a[2:]))[0]+1
    peaks=sorted(peaks,key=lambda i:a[i],reverse=True)
    peaks=[i for i in peaks if f[i]>0 and 2<=1/f[i]<=60][:5]
    return pd.DataFrame({'frecuencia_ciclos_dia':f[1:],'periodo_dias':1/f[1:],'amplitud_h':a[1:]}),[
        {'periodo_dias':float(1/f[i]),'amplitud_h':float(a[i]),'frecuencia_ciclos_dia':float(f[i])} for i in peaks]

