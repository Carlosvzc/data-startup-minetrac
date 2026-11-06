"""Base de datos del E2: PostgreSQL en la nube (RDS) o SQLite en pruebas. Se elige con DATABASE_URL."""
from __future__ import annotations
import os, datetime as dt
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(String(32), primary_key=True)
    estado = Column(String(16), default='en_cola')      # en_cola | procesando | listo | fallido
    archivo = Column(String(200))
    filas_recibidas = Column(Integer, default=0)
    filas_limpias = Column(Integer, default=0)
    filas_rechazadas = Column(Integer, default=0)
    intentos = Column(Integer, default=0)
    error = Column(Text)
    creado = Column(DateTime, default=dt.datetime.utcnow)
    terminado = Column(DateTime)


class Evento(Base):
    __tablename__ = 'eventos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(32), index=True)
    equipo_id = Column(String(8), index=True)
    fecha = Column(Date)
    sistema = Column(String(32))
    tipo_evento = Column(String(64))
    monto_mxn = Column(Float)


def motor(url: str | None = None):
    url = url or os.getenv('DATABASE_URL', 'sqlite:///data/e2.db')
    e = create_engine(url, future=True, pool_pre_ping=True)
    Base.metadata.create_all(e)
    return e


def sesion(e):
    return sessionmaker(bind=e, expire_on_commit=False, future=True)()
