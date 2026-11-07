#!/bin/sh
# Arranca la API en segundo plano (solo accesible dentro del contenedor) y
# luego el servidor de Next.js, que reenvía /api, /media y /samples a la API.
set -e

cd /app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Esperar a que la API responda (la primera vez carga los datos demostrativos).
i=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" 2>/dev/null; do
  i=$((i + 1))
  if [ "$i" -gt 90 ]; then
    echo "La API no respondió en 90 s" >&2
    exit 1
  fi
  sleep 1
done
echo "API lista. Interfaz en el puerto ${PORT:-10000}"

cd /app/frontend
HOSTNAME=0.0.0.0 PORT="${PORT:-10000}" exec node server.js
