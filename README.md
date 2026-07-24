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

### Requisitos previos

Antes de comenzar, asegúrate de tener instalado:

- Git.
- Python 3.12 o una versión compatible.
- MySQL 8 o una versión compatible.
- Una terminal o consola de comandos.

### 1. Clonar el repositorio

```bash
git clone https://github.com/EbertonDr318/QR_registration_app.git
cd QR_registration_app
```

### 2. Crear y activar el entorno virtual

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Instalar las dependencias

```bash
python -m pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

En macOS o Linux:

```bash
cp .env.example .env
```

En Windows:

```bat
copy .env.example .env
```

Abre el archivo `.env` y configura la conexión a MySQL. No utilices las
credenciales de ejemplo en un entorno real.

### 5. Crear la base de datos

En macOS, Linux o Git Bash:

```bash
mysql -u root -p < schema.sql
```

En Windows PowerShell:

```powershell
cmd /c "mysql -u root -p < schema.sql"
```

El comando solicitará la contraseña del usuario de MySQL.

### 6. Ejecutar la aplicación

```bash
python run.py
```

Abre `http://127.0.0.1:5000` en el navegador. Para detener el servidor,
presiona `Ctrl+C`.

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
