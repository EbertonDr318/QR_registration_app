# RMS — Registro y asistencia QR multiiglesia

Aplicación Flask de producción para administrar personas, eventos y asistencias
mediante QR. Varias iglesias pueden utilizar la misma plataforma con aislamiento
estricto de datos por tenant.

Repositorio: `EbertonDr318/QR_registration_app`

## Arquitectura

- `Usuario`: identidad global autenticada por Google. No almacena rol global,
  contraseña ni tokens OAuth.
- `Iglesia`: tenant independiente de la plataforma.
- `MembresiaIglesia`: relación entre Usuario e Iglesia; contiene rol, estado y
  la Persona vinculada dentro de esa iglesia.
- `Persona`: perfil operativo perteneciente a una iglesia.
- `Evento` y `Asistencia`: registros pertenecientes a una iglesia.
- `RegistroAuditoria`: historial seguro de acciones administrativas relevantes.

```text
Usuario
  └── MembresiaIglesia
        ├── Iglesia
        └── Persona

Iglesia
  ├── Personas
  ├── Eventos
  └── Asistencias
```

El identificador de la iglesia seleccionada se guarda en la sesión, pero cada
solicitud vuelve a validar en la base que la iglesia esté activa y que el
Usuario posea una membresía activa. Las consultas administrativas siempre se
filtran por ese contexto validado.

## Funcionalidades

- Una sola pantalla de login con “Continuar con Google”.
- Usuario global con múltiples membresías.
- Rol `usuario` o `admin` diferente en cada iglesia.
- Selector automático cuando existe una membresía activa y selector visible
  cuando existen varias.
- Onboarding para solicitar acceso a una iglesia.
- Panel personal, QR propio e historial limitado a la Persona vinculada.
- Dashboard, personas, eventos, escáner, asistencias y reportes aislados por
  iglesia.
- Administración y auditoría de membresías.
- CSV, Excel y PDF generados exclusivamente con datos del tenant actual.
- Endpoint público `GET /health`.

## Instalación local

### Requisitos

- Git.
- Python 3.12 o compatible.
- MySQL 8 o compatible.

### 1. Clonar y crear el entorno

```bash
git clone https://github.com/EbertonDr318/QR_registration_app.git
cd QR_registration_app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

En Windows PowerShell, activa el entorno con:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Configura `.env` localmente. Nunca lo agregues a Git:

```env
APP_ENV=development
SECRET_KEY=
DATABASE_URL=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_DISCOVERY_URL=https://accounts.google.com/.well-known/openid-configuration
```

`DATABASE_URL` tiene prioridad. Si no se define, la aplicación utiliza
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`.

### 3. Base nueva

```bash
mysql -u root -p < schema.sql
flask --app wsgi:app db stamp head
```

### 4. Instalación existente

No vuelvas a importar `schema.sql`. Realiza un respaldo y aplica:

```bash
flask --app wsgi:app db upgrade
```

La migración crea `Iglesia Principal`, asigna allí las personas, eventos y
asistencias existentes, conserva IDs, códigos y tokens QR, y reemplaza el rol
global por membresías.

### 5. Primera iglesia y administrador

```bash
flask --app wsgi:app iglesias create \
  --nombre "Iglesia Principal" \
  --slug "iglesia-principal" \
  --admin-email administrador@example.com
```

El comando es idempotente. También puedes crear otro administrador:

```bash
flask --app wsgi:app membresias create-admin \
  --iglesia iglesia-principal \
  --email administrador@example.com
```

Ningún usuario puede convertirse en administrador desde el navegador.

### 6. Ejecutar

```bash
python run.py
```

Abre `http://localhost:5000`.

## Flujo de Google OAuth

1. El visitante pulsa “Continuar con Google”.
2. Google devuelve claims OpenID Connect verificados.
3. El backend exige `email_verified=true` y busca por `sub`, después por correo.
4. Si el Usuario no existe, crea únicamente la identidad global.
5. Una membresía activa se selecciona automáticamente.
6. Varias membresías activas llevan a `/seleccionar-iglesia`.
7. Sin membresías, el Usuario llega a `/unirse`.

Durante onboarding:

- Una única Persona activa con el mismo correo dentro de la iglesia crea una
  membresía `usuario` activa y vinculada.
- Ninguna coincidencia o varias coincidencias generan una solicitud pendiente.
- Nunca se asigna el rol `admin` automáticamente.

## Google Cloud

Configura una aplicación OAuth web con estos callbacks exactos:

```text
http://localhost:5000/auth/google/callback
http://127.0.0.1:5000/auth/google/callback
https://qrregistrationapp-production.up.railway.app/auth/google/callback
```

Origen JavaScript autorizado de producción:

```text
https://qrregistrationapp-production.up.railway.app
```

Guarda Client ID y Client Secret únicamente como variables del servicio Flask.

## Comandos administrativos

```bash
flask --app wsgi:app iglesias list
flask --app wsgi:app iglesias rename --slug iglesia-principal --nombre "Nuevo nombre"
flask --app wsgi:app membresias set-role --iglesia iglesia-principal --email correo@example.com --role usuario
flask --app wsgi:app membresias activate --iglesia iglesia-principal --email correo@example.com
flask --app wsgi:app membresias suspend --iglesia iglesia-principal --email correo@example.com
flask --app wsgi:app membresias link-persona --iglesia iglesia-principal --email correo@example.com --persona-id 123
```

Las solicitudes pendientes también se administran desde `/admin/membresias`.

## Migraciones

```bash
flask --app wsgi:app db upgrade
flask --app wsgi:app db migrate -m "descripcion"
```

Revisa manualmente cada migración antes de aplicarla. No ejecutes
`db.drop_all()`, `DROP DATABASE` ni sustituyas una base existente.

## Railway

Configura en el servicio de la aplicación Flask, no en el servicio MySQL:

```env
APP_ENV=production
SECRET_KEY=
DATABASE_URL=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_DISCOVERY_URL=https://accounts.google.com/.well-known/openid-configuration
```

Después del despliegue ejecuta manualmente:

```bash
flask --app wsgi:app db upgrade
```

Gunicorn continúa utilizando `$PORT` desde `railway.toml`. Las migraciones no se
ejecutan automáticamente durante el inicio.

## Seguridad

- Cookies `HttpOnly`, `SameSite=Lax` y `Secure` en producción.
- Protección fuerte de sesión Flask-Login.
- CSRF en formularios y solicitudes `fetch`.
- OAuth `state` administrado por Authlib.
- Sin contraseñas ni tokens OAuth almacenados.
- Sin `qr_token` en respuestas JSON, HTML o JavaScript.
- Sin roles ni `iglesia_id` confiados desde el frontend.
- Recursos de otros tenants responden 404 o 403 según corresponda.
- Auditoría sin secretos, cookies ni tokens QR completos.

## Pruebas

Las pruebas simulan OpenID Connect y utilizan SQLite en memoria explícitamente:

```bash
pytest -q
```

Cubren login, onboarding, múltiples membresías, roles por iglesia, suspensión,
IDOR, aislamiento de personas/eventos/asistencias/reportes, QR propio, CSRF,
logout, CLI y conservación de datos en la migración.

## Licencia

MIT — Jonathan David Raxcacó.
