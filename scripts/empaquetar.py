"""Genera un ZIP de código, recursos y documentación sin datos locales ni dependencias."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os

raiz=Path(__file__).resolve().parents[1]
salida=raiz.parent/"DinoCafe-unificado.zip"
excluir={"node_modules",".venv","venv","__pycache__","dist",".git","media"}
with ZipFile(salida,"w",compression=ZIP_DEFLATED) as archivo:
    for directorio,carpetas,nombres in os.walk(raiz):
        carpetas[:]=sorted(p for p in carpetas if p not in excluir)
        for nombre in sorted(nombres):
            ruta=Path(directorio)/nombre
            if ruta.name==".env" or ruta.suffix in {".pyc",".sqlite3"} or ruta.name in {"vitest-stderr.log","audit-results.json"}:
                continue
            archivo.write(ruta,Path("DinoCafe")/ruta.relative_to(raiz))
print(f"{salida.name}: {salida.stat().st_size:,} bytes")
