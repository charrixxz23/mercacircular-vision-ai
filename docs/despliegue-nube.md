# Demo en la nube (Render, plan gratuito)

GitHub Pages solo sirve páginas estáticas y esta aplicación necesita ejecutar Python (FastAPI + OpenCV)
para analizar imágenes. Por eso la demo pública se despliega en **Render** con un único contenedor
Docker que incluye la API y la interfaz.

| Archivo | Para qué |
|---|---|
| `Dockerfile` | Compila el frontend (Next.js, modo *standalone*) e instala el backend en una imagen Python 3.12 |
| `docker/start.sh` | Arranca la API en `127.0.0.1:8000` (interna) y luego la interfaz en `$PORT` (pública) |
| `render.yaml` | *Blueprint* de Render: servicio web Docker, plan `free`, chequeo de salud en `/api/health` |
| `.github/workflows/ci.yml` | En cada push: pytest, verificación de tipos, vitest, compilación y **construcción y arranque de la imagen Docker** |

## Desplegar (una sola vez, ~10 minutos)

1. Entre a https://render.com y elija **Sign in with GitHub** con la cuenta `charrixxz23`.
2. **New → Blueprint**. Si es la primera vez, autorice a Render a leer el repositorio
   `mercacircular-vision-ai` (puede limitar el acceso solo a ese repositorio).
3. Elija el repositorio. Render lee `render.yaml` y muestra el servicio `mercacircular-vision-ai`
   con plan **Free**. Pulse **Deploy Blueprint** (o **Apply**).
4. La primera compilación tarda unos 5–10 minutos. Cuando el estado sea **Live**, la URL será
   parecida a `https://mercacircular-vision-ai.onrender.com` (si el nombre está ocupado, Render
   agrega un sufijo).
5. Copie la URL en la sección *Demo en línea* del README.

Cada `git push` a `main` vuelve a desplegar automáticamente.

## Qué esperar del plan gratuito

- **Se duerme** tras 15 minutos sin visitas; la siguiente visita tarda alrededor de un minuto en
  despertar (Render muestra una pantalla de carga). Antes de presentar, ábrala un par de minutos antes.
- **Disco efímero:** al reiniciarse o despertar, se pierden los lotes y fotos que hayan cargado los
  visitantes y la demo vuelve a los 80 lotes demostrativos. Es el comportamiento deseado para una
  demo pública; para conservar datos se necesitaría PostgreSQL (ver `database/README.md`).
- **CPU 0.1:** el análisis de una imagen tarda más que en una laptop (del orden de 1 s en lugar de
  ~50 ms), pero funciona.
- **Memoria:** API + interfaz usan ≈ 250 MB de los 512 MB disponibles (medido durante el desarrollo).
- La cámara en vivo funciona porque Render sirve la app por **https**.

## Probar la imagen en su PC (opcional, requiere Docker Desktop)

```powershell
docker build -t mercacircular .
docker run --rm -p 10000:10000 mercacircular
# http://localhost:10000
```

## Privacidad en la demo pública

Cualquiera con el enlace puede registrar lotes y subir fotos. No suba fotos con personas ni datos
reales. Los datos se borran al reiniciarse el servicio y el botón *Restablecer datos* está habilitado
(`ALLOW_DEMO_RESET=true`).
