# Ejecucion local sin Docker

Usa el entorno virtual del backend:

```powershell
cd C:\Users\USER\Documents\Me\Hackathon\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:ENABLE_EXTERNAL_SOURCES = "false"
$env:DATABASE_URL = "sqlite:///./movete_cb.db"
$env:REDIS_URL = ""
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Endpoints de comprobacion:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/api/v1/fuentes/estado`
- `GET http://127.0.0.1:8000/api/v1/estaciones?limit=5`
- `GET http://127.0.0.1:8000/api/v1/paradas?limit=5`
- `POST http://127.0.0.1:8000/api/v1/rutas/calcular`

El backend usa SQLite y cache en memoria cuando `REDIS_URL` esta vacio. Con `ENABLE_EXTERNAL_SOURCES=false` las rutas usan los datos locales sembrados. Puedes cambiarlo a `true` para consultar datos abiertos, con un timeout total controlado y fallback local. PostGIS y Redis se activaran despues mediante Docker.
