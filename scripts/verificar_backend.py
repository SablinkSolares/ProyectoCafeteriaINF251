"""Ejecuta la suite y conserva una salida UTF-8 reproducible."""
from pathlib import Path
import subprocess
import sys
import os
import argparse

parser=argparse.ArgumentParser()
parser.add_argument("--postgres",action="store_true",help="Usa PostgreSQL local de verificación en el puerto 55432.")
args=parser.parse_args()
raiz=Path(__file__).resolve().parents[1]
entorno={**os.environ,"PYTHONIOENCODING":"utf-8"}
if args.postgres:
    entorno.update(DB_ENGINE="postgres",POSTGRES_DB="dinocafe",POSTGRES_USER="dinocafe",POSTGRES_PASSWORD="verificacion-local",POSTGRES_HOST="127.0.0.1",POSTGRES_PORT="55432")
resultado=subprocess.run([sys.executable,"manage.py","test","--noinput"],cwd=raiz/"backend",env=entorno,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8")
(raiz/"docs"/("pruebas-postgres.log" if args.postgres else "pruebas-backend.log")).write_text(resultado.stdout,encoding="utf-8")
print(resultado.stdout)
sys.exit(resultado.returncode)
