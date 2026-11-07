# Base de datos

La demo usa **SQLite**: al iniciar el backend se crea `database/mercacircular.db` y las fotos se guardan
en `database/media/`. Ninguno de los dos se sube a GitHub (están en `.gitignore`).

- Los datos persisten entre reinicios.
- La primera vez se cargan los datos demostrativos de `demo-data/seed.json` (marcados con `is_demo = true`).
- Para volver al estado inicial: detenga el backend y ejecute `scripts\reset-demo.ps1`, o use
  **Acerca del proyecto → Restablecer datos** en la app.

`schema.sql` describe las tablas (generado desde `backend/app/models.py`); no hace falta ejecutarlo.

## PostgreSQL

El código usa SQLAlchemy con tipos genéricos (incluido `JSON`), así que funciona con PostgreSQL
cambiando una variable:

```powershell
backend\.venv\Scripts\pip install "psycopg[binary]"
# en .env
DATABASE_URL=postgresql+psycopg://usuario:contraseña@localhost:5432/mercacircular
```

Las tablas se crean al iniciar. Para un despliegue real conviene agregar migraciones (Alembic):
ver *Trabajo futuro* en el README.
