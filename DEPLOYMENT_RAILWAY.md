# Despliegue en Railway

Esta guía prepara el despliegue; no conecta ni modifica ningún proyecto Railway automáticamente.

1. Crea un proyecto en Railway y elige **Deploy from GitHub repo**.
2. Selecciona `EbertonDr318/QR_registration_app` y la rama `main`.
3. Agrega un servicio MySQL y conserva sus credenciales únicamente en Railway.
4. Configura `APP_ENV=production`, `FLASK_DEBUG=0`, `SECRET_KEY`, `PORT`,
   `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` y
   `GOOGLE_DISCOVERY_URL`. Si Railway
   entrega una URL `mysql://`, la aplicación la adapta a PyMySQL.
5. Registra en Google Cloud el callback exacto
   `https://qrregistrationapp-production.up.railway.app/auth/google/callback`.
6. Para una base existente, aplica las migraciones desde el entorno Railway con
   `flask --app wsgi:app db upgrade`. El inicio de Gunicorn no ejecuta
   migraciones automáticamente.
   La migración crea `Iglesia Principal` y conserva los registros existentes.
7. Para una base completamente nueva, importa `schema.sql` y ejecuta
   `flask --app wsgi:app db stamp head`.
8. Railway leerá `railway.toml` y ejecutará `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
9. Confirma que el health check `/health` devuelva `{"status":"ok"}`.
10. Crea o verifica el primer administrador por iglesia con
    `flask --app wsgi:app membresias create-admin --iglesia iglesia-principal --email administrador@example.com`.
11. Genera un dominio, abre la aplicación por HTTPS y prueba ambos roles, cambio
    de iglesia, QR y reportes.
12. Revisa stdout/stderr desde **Deployments → View Logs**. Nunca pegues secretos en commits o mensajes de log.

## Rollback

En **Deployments**, selecciona la última versión estable y usa **Redeploy**. No reviertas la base sin un respaldo compatible.

## Respaldo MySQL

Programa copias periódicas y prueba su restauración en una base aislada. Antes de migraciones destructivas, crea una copia manual verificable.

## Diagnóstico

- Build fallido: revisa versión de Python y `requirements.txt`.
- Aplicación no inicia: confirma `PORT`, `DATABASE_URL` y el log de Gunicorn.
- Health check fallido: prueba `/health` y verifica que Gunicorn escuche en `0.0.0.0`.
- Error MySQL: confirma red, nombre de base, usuario, contraseña y codificación UTF-8.
- Error 500: revisa logs; no habilites `DEBUG` en producción.
