"""Demostración de extremo a extremo: sube un CSV a la API y espera a que el worker lo procese; mide el tiempo.
    python scripts/demo_e2e.py [URL_API] [archivo.csv]        (por defecto http://localhost:8000)
"""
import sys, time, json, urllib.request, uuid

api = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
ruta = sys.argv[2] if len(sys.argv) > 2 else 'data/sample/ejemplo_ingesta.csv'
b = uuid.uuid4().hex
cuerpo = (f'--{b}\r\nContent-Disposition: form-data; name="archivo"; filename="{ruta.split("/")[-1]}"\r\nContent-Type: text/csv\r\n\r\n').encode() \
    + open(ruta, 'rb').read() + f'\r\n--{b}--\r\n'.encode()
t0 = time.time()
req = urllib.request.Request(api + '/ingesta', data=cuerpo, headers={'Content-Type': f'multipart/form-data; boundary={b}'})
job = json.load(urllib.request.urlopen(req))
print('Enviado:', job)
while True:
    j = json.load(urllib.request.urlopen(f"{api}/jobs/{job['job_id']}"))
    if j['estado'] in ('listo', 'fallido'):
        break
    time.sleep(1)
print('Resultado:', j)
print(f'Tiempo CSV -> base: {time.time() - t0:.1f} s (meta: menos de 300 s)')
sys.exit(0 if j['estado'] == 'listo' else 1)
