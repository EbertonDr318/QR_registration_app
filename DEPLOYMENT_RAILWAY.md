# Despliegue en Railway

Esta guía prepara el despliegue; no conecta ni modifica ningún proyecto Railway automáticamente.

1. Crea un proyecto en Railway y elige **Deploy from GitHub repo**.
2. Selecciona `EbertonDr318/QR_registration_app` y la rama `main`.
3. Agrega un servicio MySQL y conserva sus credenciales únicamente en Railway.
4. Configura `APP_ENV=production`, `FLASK_DEBUG=0`, `SECRET_KEY`, `PORT` y `DATABASE_URL`. Si Railway entrega una URL `mysql://`, la aplicación la adapta a PyMySQL.
5. Importa `schema.sql` en la base o ejecuta las migraciones cuando se incorpore Alembic.
6. Railway leerá `railway.toml` y ejecutará `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
7. Confirma que el health check `/health` devuelva `{"status":"ok"}`.
8. Genera un dominio, abre la aplicación por HTTPS y prueba personas, eventos, asistencias, QR y reportes.
9. Revisa stdout/stderr desde **Deployments → View Logs**. Nunca pegues secretos en commits o mensajes de log.

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
