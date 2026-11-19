"""Prueba de carga del E3: 50 usuarios contra la API de modelos.

    locust -f tests/carga/locustfile.py --headless -u 50 -r 10 -t 60s --host http://IP:8010 --csv resultados_locust
"""
from locust import HttpUser, between, task


class UsuarioModelos(HttpUser):
    wait_time = between(0.5, 2)

    @task(3)
    def pronostico_7_dias(self):
        self.client.post('/pronostico', json={'horizonte_dias': 7}, name='/pronostico (7 días)')

    @task(2)
    def pronostico_30_dias(self):
        self.client.post('/pronostico', json={'horizonte_dias': 30}, name='/pronostico (30 días)')

    @task(5)
    def clasificar(self):
        self.client.post('/clasificar', json={'sistema': 'motor', 'mes': 3, 'dia_semana': 2, 'dias_desde_previo_equipo': 12,
                                              'registros_previos_90d': 4, 'previos_mismo_sistema_90d': 1}, name='/clasificar')

    @task(1)
    def salud(self):
        self.client.get('/salud')
