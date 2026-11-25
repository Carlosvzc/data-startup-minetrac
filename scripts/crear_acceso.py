"""Genera la línea de MINETRAC_USUARIOS para una o varias personas (la contraseña no se imprime ni se guarda).

Uso:  python scripts/crear_acceso.py carlos diego profesor
Pide una contraseña por usuario y escribe algo como  carlos:sal$hash;diego:sal$hash
Pega esa línea como valor de MINETRAC_USUARIOS en el servidor (nunca en Git).
"""
import getpass, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/tablero'))
import acceso

partes = []
for u in sys.argv[1:] or [input('Usuario: ').strip()]:
    c1, c2 = getpass.getpass(f'Contraseña de {u}: '), getpass.getpass('Repítela: ')
    if c1 != c2 or len(c1) < 10:
        sys.exit('No coinciden o tienen menos de 10 caracteres.')
    partes.append(f'{u.lower()}:{acceso.hash_clave(c1)}')
print('\nMINETRAC_USUARIOS=' + ';'.join(partes))
