# QR Registration App — Producción

Aplicación real de registro de personas y control de asistencia mediante QR, desarrollada con Flask, MySQL, SQLAlchemy y Gunicorn. Este repositorio no contiene la demostración de GitHub Pages.

Repositorio: https://github.com/EbertonDr318/QR_registration_app

Demo estático de referencia: https://ebertondr318.github.io/DEMO_QR_registration_app/

## Arquitectura

- `app/models.py`: personas, eventos, asistencias y cuentas de acceso.
- `app/auth.py`: inicio de sesión Google OpenID Connect y cierre de sesión.
- `app/permissions.py`: autorización reutilizable para administradores y perfiles vinculados.
- `app/account.py`: panel y API privada de la cuenta personal.
- `app/api.py`: API administrativa, validación, QR y reportes.
- `app/web.py`: entrada y vistas administrativas bajo `/admin`.
- `app/cli.py`: comandos seguros para administrar cuentas y roles.
- `migrations/`: historial no destructivo de Flask-Migrate/Alembic.
- `app/templates/` y `app/static/`: interfaz adaptable según el rol.
- `wsgi.py`: punto de entrada WSGI.
- `railway.toml`: única fuente del comando de inicio Railway.
- `schema.sql`: creación inicial del esquema MySQL.

## Funcionalidades

- Administración de personas, estados y códigos internos únicos.
- Tokens QR aleatorios generados en el backend.
- Creación, apertura y cierre de eventos.
- Registro de asistencia manual o por QR con protección contra duplicados.
- Dashboard, historial, filtros y reportes CSV, Excel y PDF en memoria.
- Una sola pantalla de acceso con Google para usuarios y administradores.
- Roles almacenados en la base de datos y acceso personal limitado a la persona vinculada.
- Protección CSRF en formularios y solicitudes de escritura con `fetch`.
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

Abre el archivo `.env` y configura la conexión a MySQL, una `SECRET_KEY`
aleatoria y las credenciales OAuth de Google. No utilices las credenciales de
ejemplo en un entorno real.

### 5. Crear una base de datos nueva

En macOS, Linux o Git Bash:

```bash
mysql -u root -p < schema.sql
```

En Windows PowerShell:

```powershell
cmd /c "mysql -u root -p < schema.sql"
```

El comando solicitará la contraseña del usuario de MySQL.

Como `schema.sql` ya incluye el estado actual completo, registra esa base nueva
como actualizada sin volver a crear tablas:

```bash
flask --app wsgi:app db stamp head
```

Si ya tienes una instalación con datos, no vuelvas a importar `schema.sql`.
Aplica la migración no destructiva:

```bash
flask --app wsgi:app db upgrade
```

La migración crea `usuarios` y conserva personas, eventos, asistencias y tokens
QR. Antes de vincular cuentas automáticamente, revisa correos duplicados en
`personas`; la migración no agrega una restricción única a `personas.correo`.

### 6. Configurar Google OpenID Connect

En Google Cloud Console crea credenciales OAuth 2.0 para una aplicación web y
registra exactamente estos URI de redirección autorizados:

- Desarrollo: `http://localhost:5000/auth/google/callback`
- Producción: `https://{DOMINIO_PUBLICO_DE_RAILWAY}/auth/google/callback`

Configura el identificador y el secreto resultantes como `GOOGLE_CLIENT_ID` y
`GOOGLE_CLIENT_SECRET` en `.env`. El secreto nunca debe guardarse en Git.

### 7. Crear el primer administrador

```bash
flask --app wsgi:app users create-admin --email administrador@example.com --name "Administrador"
```

El comando es idempotente. Una cuenta existente se promueve explícitamente a
`admin` y se activa; ninguna cuenta recibe ese rol automáticamente durante el
login.

### 8. Ejecutar la aplicación

```bash
python run.py
```

Abre `http://localhost:5000` en el navegador. Para detener el servidor,
presiona `Ctrl+C`.

## Variables

`DATABASE_URL` tiene prioridad. Si está vacía, se construye la conexión MySQL
con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. También son
necesarias `SECRET_KEY`, `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`. En
producción configura `APP_ENV=production` y `PORT`.

No se utiliza SQLite silenciosamente: sólo las pruebas automatizadas inyectan SQLite en memoria de forma explícita.

## API principal

- Cuenta propia autenticada: `/api/mi-cuenta`, `/api/mi-cuenta/qr` y
  `/api/mi-cuenta/eventos`.
- Administración: `/api/personas`, `/api/eventos`, `/api/asistencias`, escáner
  y exportaciones. Requieren rol `admin` en el backend.
- Público: `/health`.

## Pruebas

```bash
pytest -q
```

Las pruebas desacoplan los claims OpenID Connect y no contactan a Google.

## Gunicorn

```bash
gunicorn wsgi:app --bind 127.0.0.1:8000
```

Railway utiliza:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

## Base de datos y migraciones

El esquema completo para instalaciones nuevas está en `schema.sql`. Las
instalaciones existentes deben usar Flask-Migrate/Alembic:

```bash
flask --app wsgi:app db upgrade
flask --app wsgi:app db migrate -m "descripcion"
```

Revisa manualmente cada migración generada antes de aplicarla. No ejecutes
`db.drop_all()`, `DROP TABLE` ni reemplaces una base existente.

## Cuentas y roles

Todos ingresan desde `/login` con el mismo botón de Google. El rol se obtiene
de `usuarios`, nunca del navegador:

- Un correo que coincide exactamente con una única `Persona` activa crea una
  cuenta `usuario` y la vincula automáticamente.
- Un correo desconocido, duplicado o asociado a una persona inactiva no entra.
- Un administrador debe crearse o promoverse explícitamente por CLI.

Comandos disponibles:

```bash
flask --app wsgi:app users create-admin --email administrador@example.com
flask --app wsgi:app users activate --email usuario@example.com
flask --app wsgi:app users deactivate --email usuario@example.com
flask --app wsgi:app users set-role --email usuario@example.com --role admin
flask --app wsgi:app users link-persona --email usuario@example.com --persona-id 123
```

Para probar un usuario normal, crea una persona activa con el correo de su
cuenta de Google y usa el login común; será dirigido a `/mi-cuenta`. Para probar
un administrador, ejecuta `users create-admin` con su correo y usa exactamente
el mismo login; será dirigido a `/admin`.

## Seguridad

Implementado: Google OpenID Connect, sesiones Flask-Login con protección fuerte,
roles verificados en backend, cierre de sesión `POST`, CSRF, validación de
redirecciones, ORM, tokens QR impredecibles no serializados, cookies
`HttpOnly`/`SameSite=Lax`, cookies `Secure` en producción y errores sin trazas
públicas. La aplicación no almacena tokens de Google.

## Railway

Consulta [DEPLOYMENT_RAILWAY.md](DEPLOYMENT_RAILWAY.md). El repositorio está preparado, pero Railway no ha sido conectado.

Después de desplegar una versión con nuevas migraciones, ejecuta una vez en el
entorno Railway:

```bash
flask --app wsgi:app db upgrade
```

No se aplican migraciones automáticamente durante el inicio de Gunicorn.

## Licencia

MIT — Jonathan David Raxcacó.
