"""Acceso privado al tablero: usuario y contraseña.

Las cuentas viven en la variable de entorno MINETRAC_USUARIOS con el formato  usuario:sal$hash;otro:sal$hash
(el hash es scrypt; la contraseña nunca se guarda). Se generan con  python scripts/crear_acceso.py.
Regla: en AWS (MINETRAC_STORAGE=s3) el tablero NO abre sin cuentas configuradas; en la demostración local abre libre.
"""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets

N, R, P = 2 ** 14, 8, 1


def hash_clave(clave: str, sal: str | None = None) -> str:
    sal = sal or secrets.token_hex(16)
    h = hashlib.scrypt(clave.encode('utf-8'), salt=sal.encode(), n=N, r=R, p=P, dklen=32).hex()
    return f'{sal}${h}'


def cuentas(valor: str | None = None) -> dict[str, str]:
    valor = os.environ.get('MINETRAC_USUARIOS', '') if valor is None else valor
    out = {}
    for par in valor.split(';'):
        if ':' in par and '$' in par:
            u, resto = par.strip().split(':', 1)
            out[u.strip().lower()] = resto.strip()
    return out


def verificar(usuario: str, clave: str, tabla: dict[str, str]) -> bool:
    """Compara en tiempo constante; también gasta el mismo tiempo si el usuario no existe."""
    resto = tabla.get((usuario or '').strip().lower())
    sal, esperado = (resto.split('$', 1) if resto else ('x', '0' * 64))
    h = hashlib.scrypt((clave or '').encode('utf-8'), salt=sal.encode(), n=N, r=R, p=P, dklen=32).hex()
    return bool(resto) and hmac.compare_digest(h, esperado)


def requerido(modo_almacenamiento: str) -> bool:
    return modo_almacenamiento == 's3' or os.environ.get('MINETRAC_ACCESO', '').lower() == 'requerido' or bool(cuentas())
