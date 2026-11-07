"""Muestrea la salud de API y base de datos durante el horario de atención.

Ejemplo: python scripts/monitor_disponibilidad.py --url http://localhost:8000/api/health/ --muestras 480 --intervalo 60 --salida docs/disponibilidad.json
"""
import argparse
import json
import time
from datetime import datetime, timezone
from urllib.request import urlopen
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("--url",default="http://localhost:8000/api/health/")
parser.add_argument("--muestras",type=int,default=10)
parser.add_argument("--intervalo",type=float,default=60)
parser.add_argument("--salida",default="disponibilidad.json")
args=parser.parse_args()
if args.muestras < 1 or args.intervalo < 0:
    parser.error("Usa muestras positivas e intervalo no negativo.")
resultados=[]
for indice in range(args.muestras):
    inicio=time.perf_counter()
    try:
        with urlopen(args.url,timeout=5) as respuesta:
            ok=respuesta.status==200 and json.load(respuesta).get("status")=="ok"
    except Exception:
        ok=False
    resultados.append({"fecha_utc":datetime.now(timezone.utc).isoformat(),"ok":ok,"milisegundos":round((time.perf_counter()-inicio)*1000,2)})
    if indice+1<args.muestras:
        time.sleep(args.intervalo)
resumen={"url":args.url,"muestras":args.muestras,"intervalo_segundos":args.intervalo,"porcentaje_observado":100*sum(r["ok"] for r in resultados)/len(resultados),"resultados":resultados,"alcance":"Disponibilidad observada por sondeo. Para evaluar RNF1, cubrir jornadas completas de atención; una muestra corta no acredita el 99%."}
Path(args.salida).write_text(json.dumps(resumen,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({k:v for k,v in resumen.items() if k!="resultados"},ensure_ascii=False))
