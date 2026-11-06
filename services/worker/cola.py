"""Cola de mensajes. SQS en la nube (o ElasticMQ/LocalStack en local) y una cola en memoria para pruebas."""
from __future__ import annotations
import json, os, time, uuid
from dataclasses import dataclass


@dataclass
class Mensaje:
    cuerpo: dict
    handle: str
    intentos: int


class ColaMemoria:
    """Misma interfaz que SQS: recibir, borrar, visibilidad y cola de mensajes muertos tras max_intentos."""
    def __init__(self, max_intentos: int = 3):
        self.max_intentos, self.pendientes, self.muertos = max_intentos, {}, []

    def enviar(self, cuerpo: dict) -> str:
        h = uuid.uuid4().hex
        self.pendientes[h] = {'cuerpo': cuerpo, 'intentos': 0}
        return h

    def recibir(self) -> Mensaje | None:
        for h, m in list(self.pendientes.items()):
            if m['intentos'] >= self.max_intentos:
                self.muertos.append(self.pendientes.pop(h)['cuerpo']); continue
            m['intentos'] += 1
            return Mensaje(m['cuerpo'], h, m['intentos'])
        return None

    def borrar(self, handle: str):
        self.pendientes.pop(handle, None)

    def devolver(self, handle: str):   # el mensaje queda visible otra vez (equivale a vencer la visibilidad)
        pass


class ColaSQS:
    def __init__(self, nombre='minetrac-eventos', max_intentos=3, endpoint=None, region=None, visibilidad=30):
        import boto3
        kw = {'region_name': region or os.getenv('AWS_REGION', 'us-east-1')}
        if endpoint or os.getenv('SQS_ENDPOINT'):
            kw['endpoint_url'] = endpoint or os.getenv('SQS_ENDPOINT')
        self.sqs = boto3.client('sqs', **kw)
        dlq = self.sqs.create_queue(QueueName=nombre + '-muertos')['QueueUrl']
        arn = self.sqs.get_queue_attributes(QueueUrl=dlq, AttributeNames=['QueueArn'])['Attributes']['QueueArn']
        self.url = self.sqs.create_queue(QueueName=nombre, Attributes={
            'VisibilityTimeout': str(visibilidad),
            'RedrivePolicy': json.dumps({'deadLetterTargetArn': arn, 'maxReceiveCount': str(max_intentos)})})['QueueUrl']
        self.url_muertos = dlq

    def enviar(self, cuerpo: dict) -> str:
        return self.sqs.send_message(QueueUrl=self.url, MessageBody=json.dumps(cuerpo))['MessageId']

    def recibir(self, espera=20) -> Mensaje | None:
        r = self.sqs.receive_message(QueueUrl=self.url, MaxNumberOfMessages=1, WaitTimeSeconds=espera,
                                     AttributeNames=['ApproximateReceiveCount'])
        for m in r.get('Messages', []):
            return Mensaje(json.loads(m['Body']), m['ReceiptHandle'], int(m['Attributes']['ApproximateReceiveCount']))
        return None

    def borrar(self, handle: str):
        self.sqs.delete_message(QueueUrl=self.url, ReceiptHandle=handle)

    def devolver(self, handle: str):   # visibilidad 0: reintento inmediato
        self.sqs.change_message_visibility(QueueUrl=self.url, ReceiptHandle=handle, VisibilityTimeout=0)

    def muertos(self) -> int:
        a = self.sqs.get_queue_attributes(QueueUrl=self.url_muertos, AttributeNames=['ApproximateNumberOfMessages'])
        return int(a['Attributes']['ApproximateNumberOfMessages'])


def crear_cola():
    return ColaSQS() if os.getenv('COLA', 'sqs') == 'sqs' else ColaMemoria()
