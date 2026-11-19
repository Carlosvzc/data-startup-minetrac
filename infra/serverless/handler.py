"""Función serverless (AWS Lambda) del E3: clasifica un registro sin servidor propio.

Usa el Naive Bayes exportado a naive_bayes.json y lo calcula en Python puro (sin scikit-learn), por eso el paquete pesa pocos KB.
Recibe el mismo JSON que POST /clasificar de la API de modelos.
"""
import json
import math
import os
from pathlib import Path

_RAIZ = Path(os.environ.get('LAMBDA_TASK_ROOT', Path(__file__).parent))
_PAR = json.loads((_RAIZ / 'naive_bayes.json').read_text(encoding='utf-8'))


def probabilidad(fila: dict) -> float:
    p = _PAR
    x = []
    for k, (med, mu, sd) in enumerate(zip(p['mediana'], p['media'], p['escala'])):
        v = fila.get(p['numericas'][k])
        x.append(((med if v is None else float(v)) - mu) / sd)
    x += [1.0 if fila['sistema'] == s else 0.0 for s in p['sistemas']]
    logs = []
    for c in range(len(p['clases'])):
        lp = math.log(p['previa'][c])
        for j, xj in enumerate(x):
            var = p['var'][c][j]
            lp += -0.5 * math.log(2 * math.pi * var) - (xj - p['theta'][c][j]) ** 2 / (2 * var)
        logs.append(lp)
    mx = max(logs)
    e = [math.exp(l - mx) for l in logs]
    return e[p['clases'].index(1)] / sum(e)


def lambda_handler(event, context):
    try:
        d = json.loads(event['body']) if isinstance(event.get('body'), str) else (event.get('body') or event)
        if d.get('sistema') not in _PAR['sistemas']:
            return {'statusCode': 422, 'body': json.dumps({'error': 'sistema inválido', 'validos': _PAR['sistemas']})}
        fila = {'sistema': d['sistema'], 'mes': int(d['mes']), 'dia_semana': int(d['dia_semana']),
                'dias_desde_previo_equipo': d.get('dias_desde_previo_equipo')}
        for k in ('registros_previos_90d', 'previos_mismo_sistema_90d', 'pieza_declarada', 'proveedor_declarado'):
            fila[k] = int(d.get(k) or 0)
        if not (1 <= fila['mes'] <= 12 and 0 <= fila['dia_semana'] <= 6):
            raise ValueError('mes o dia_semana fuera de rango')
        pr = probabilidad(fila)
        return {'statusCode': 200, 'headers': {'content-type': 'application/json'},
                'body': json.dumps({'repite_30d': pr >= 0.5, 'probabilidad': round(pr, 4)})}
    except (KeyError, TypeError, ValueError) as e:
        return {'statusCode': 422, 'body': json.dumps({'error': f'entrada inválida: {e}'})}
