# QR Registration App — Producción

Aplicación real de registro de personas y control de asistencia mediante QR, desarrollada con Flask, MySQL, SQLAlchemy y Gunicorn. Este repositorio no contiene la demostración de GitHub Pages.

Repositorio: https://github.com/EbertonDr318/QR_registration_app

Demo estático de referencia: https://ebertondr318.github.io/DEMO_QR_registration_app/

## Arquitectura

- `app/models.py`: personas, eventos y asistencias.
- `app/api.py`: API REST, validación, QR y reportes.
- `app/web.py`: vistas HTML.
- `app/templates/` y `app/static/`: interfaz Flask.
- `wsgi.py`: punto de entrada WSGI.
- `railway.toml`: única fuente del comando de inicio Railway.
- `schema.sql`: creación inicial del esquema MySQL.

## Funcionalidades

- Administración de personas, estados y códigos internos únicos.
- Tokens QR aleatorios generados en el backend.
- Creación, apertura y cierre de eventos.
- Registro de asistencia manual o por QR con protección contra duplicados.
- Dashboard, historial, filtros y reportes CSV, Excel y PDF en memoria.
- Endpoint público `GET /health`.

## Instalación local

```bash
cd /Users/jonathanraxcaco/Desktop/RegistroPersonalConQr-Produccion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
mysql -u root -p < schema.sql
python run.py
```

## Variables

`DATABASE_URL` tiene prioridad. Si está vacía, se construye la conexión MySQL con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. En producción configura además `APP_ENV=production`, una `SECRET_KEY` aleatoria y `PORT`.

No se utiliza SQLite silenciosamente: sólo las pruebas automatizadas inyectan SQLite en memoria de forma explícita.

## API principal

- `/api/personas`
- `/api/eventos`
- `/api/asistencias`
- `/api/asistencias/registrar`
- `/api/asistencias/exportar`
- `/api/asistencias/exportar.xlsx`
- `/api/asistencias/exportar.pdf`
- `/health`

## Pruebas

```bash
pytest -q
```

## Gunicorn

```bash
gunicorn wsgi:app --bind 127.0.0.1:8000
```

Railway utiliza:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

## Base de datos y migraciones

El esquema inicial está en `schema.sql`. Antes de cambios incompatibles debe incorporarse Flask-Migrate/Alembic; actualmente no existe un historial de migraciones versionado.

## Seguridad

Implementado: validación backend, ORM, tokens QR impredecibles, restricciones únicas, cookies `HttpOnly`/`SameSite`, cookies `Secure` en producción y errores sin trazas públicas.

Pendientes críticos antes de uso con datos reales: autenticación, cierre de sesión, hash de contraseñas, roles, CSRF, autorización de rutas, auditoría administrativa, rate limiting y rotación de secretos.

## Railway

Consulta [DEPLOYMENT_RAILWAY.md](DEPLOYMENT_RAILWAY.md). El repositorio está preparado, pero Railway no ha sido conectado.

## Licencia

MIT — Jonathan David Raxcacó.
