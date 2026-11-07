# Guía paso a paso en Windows

Tiempo estimado: 10–15 minutos (la mayor parte es descarga de dependencias).

## 1. Instalar los requisitos (una sola vez)

| Programa | Versión | Enlace | Nota |
|---|---|---|---|
| Python | 3.11, 3.12 o 3.13 | https://www.python.org/downloads/ | Marque **«Add python.exe to PATH»** |
| Node.js | 20 o 22 (LTS) | https://nodejs.org/ | Incluye `npm` |
| Git | cualquiera | https://git-scm.com/download/win | Para subir a GitHub y para reentrenar |
| Visual Studio Code | cualquiera | https://code.visualstudio.com/ | Opcional |

Compruebe en una terminal nueva:

```powershell
py --version      # o: python --version
node --version
git --version
```

## 2. Descomprimir y abrir

1. Descomprima `MercaCircular-Vision-AI.zip`, por ejemplo en `C:\Proyectos\`.
   **Evite** carpetas sincronizadas por OneDrive (bloquean archivos de `node_modules`).
2. En VS Code: *Archivo → Abrir carpeta…* → `MercaCircular-Vision-AI`.
3. Abra la terminal integrada: *Terminal → Nueva terminal* (PowerShell).

## 3. Instalar dependencias

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Crea `backend\.venv`, instala los paquetes de Python, ejecuta `npm ci` en `frontend` y crea `.env`
con valores por defecto.

> Si ve «la ejecución de scripts está deshabilitada», use exactamente el comando de arriba
> (`-ExecutionPolicy Bypass` solo afecta a ese comando).

## 4. Ejecutar la demo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

Se abren dos ventanas (API y web) y el navegador en **http://localhost:3000**.
La primera vez el backend crea `database\mercacircular.db` y carga los datos demostrativos.

Por separado, si lo prefiere:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1    # http://127.0.0.1:8000/docs
powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1   # http://localhost:3000
```

Para presentar, el modo producción es más fluido: `scripts\start.ps1 -Prod`.

## 5. Probar con el teléfono (cámara y QR)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Lan
```

El script muestra una dirección como `http://192.168.1.25:3000`. Ábrala en el teléfono (misma red
Wi-Fi) y permita el acceso cuando el Firewall de Windows lo pregunte (red privada).

- En el teléfono, *Inspección → Archivo → «Tomar foto con el teléfono»* abre la cámara. La vista en vivo
  de la pestaña *Cámara* exige https o localhost, por eso en la red local se usa la cámara del sistema.
- Los QR generados al abrir la app con esa IP abren la ficha del lote desde el teléfono.

## 6. Ejecutar las pruebas

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

## 7. Volver a los datos iniciales

Desde la app: *Acerca del proyecto → Restablecer datos*. O, con el backend detenido:
`scripts\reset-demo.ps1`.

## 8. Subir a GitHub (`charrixxz23/mercacircular-vision-ai`)

1. En https://github.com/new cree el repositorio `mercacircular-vision-ai` **vacío** (sin README,
   .gitignore ni licencia).
2. En la carpeta del proyecto:

```powershell
git init -b main
git add .
git commit -m "MercaCircular Vision AI: prototipo académico inicial"
git remote add origin https://github.com/charrixxz23/mercacircular-vision-ai.git
git push -u origin main
```

`.gitignore` ya excluye `node_modules`, `.venv`, `.next`, la base de datos local, las fotos subidas,
el dataset descargado y `.env`. Antes de hacer `git add`, puede revisar qué se subirá con `git status`.

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| La web muestra «No hay conexión con el servidor de análisis» | El backend no está corriendo: `scripts\start-backend.ps1` |
| `Address already in use` / puerto ocupado | Cierre la otra ventana que usa el puerto 8000 o 3000 |
| `npm ci` falla con `EPERM` | Mueva el proyecto fuera de OneDrive o cierre VS Code y reintente |
| «Permiso de cámara denegado» | Permita la cámara en el icono del candado del navegador, o use «Archivo» |
| Cambié `BACKEND_URL` y no surte efecto en `-Prod` | En producción se aplica al compilar: vuelva a ejecutar con `-Prod` |
| Quiero PostgreSQL | Ver `database/README.md` |
