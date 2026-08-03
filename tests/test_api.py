import re
from datetime import date, time, timedelta

from app import create_app, db, login_manager
from app.auth import authenticate_claims
from app.models import Asistencia, Evento, Persona, Usuario
from conftest import create_person, create_user, login


def test_visitor_is_redirected_to_login_and_health_stays_public(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert client.get("/api/personas").status_code == 401
    assert client.get("/health").get_json() == {"status": "ok"}


def test_verified_known_person_creates_regular_user(app):
    with app.app_context():
        person = create_person(correo="NEW@EXAMPLE.TEST")
        user, error = authenticate_claims(
            {
                "sub": "google-new",
                "email": " new@example.test ",
                "email_verified": True,
                "name": "Nueva",
            }
        )
        assert error is None
        assert user.rol == "usuario"
        assert user.persona_id == person.id
        assert user.email == "new@example.test"


def test_existing_admin_keeps_database_role(app):
    with app.app_context():
        create_user(
            email="admin@example.test", rol="admin", person=None, proveedor_subject=None
        )
        user, error = authenticate_claims(
            {
                "sub": "google-admin",
                "email": "ADMIN@example.test",
                "email_verified": True,
                "name": "Admin",
            }
        )
        assert error is None
        assert user.is_admin
        assert user.proveedor_subject == "google-admin"


def test_role_based_home_redirects(client, app, regular_user, admin_user):
    with app.app_context():
        regular = db.session.get(Usuario, regular_user)
        login(client, regular)
    assert client.get("/").headers["Location"].endswith("/mi-cuenta")

    client.get("/logout")
    with app.app_context():
        admin = db.session.get(Usuario, admin_user)
        login(client, admin)
    assert client.get("/").headers["Location"].endswith("/admin")


def test_regular_user_cannot_access_admin_or_admin_api(client, app, regular_user):
    with app.app_context():
        login(client, db.session.get(Usuario, regular_user))
    assert client.get("/admin").status_code == 403
    response = client.get("/api/personas")
    assert response.status_code == 403
    assert response.is_json


def test_admin_can_use_existing_features_and_reports(client, app, admin_user):
    with app.app_context():
        login(client, db.session.get(Usuario, admin_user))
    created = client.post(
        "/api/personas",
        json={
            "codigo": "P-001",
            "nombres": "Ana",
            "apellidos": "Prueba",
            "sede": "Centro",
        },
    )
    assert created.status_code == 201
    event = client.post(
        "/api/eventos",
        json={
            "nombre": "Jornada",
            "fecha": "2026-08-04",
            "hora_inicio": "09:00",
            "sede": "Centro",
        },
    ).get_json()["data"]
    attendance = client.post(
        "/api/asistencias/registrar",
        json={"evento_id": event["id"], "codigo": "P-001"},
    )
    assert attendance.status_code == 201
    assert client.get("/api/asistencias/exportar").mimetype.startswith("text/csv")
    assert client.get("/api/asistencias/exportar.xlsx").status_code == 200
    assert client.get("/api/asistencias/exportar.pdf").status_code == 200


def test_user_only_reads_own_profile_and_qr(client, app, regular_user):
    with app.app_context():
        other = create_person(correo="other@example.test")
        other_id = other.id
        login(client, db.session.get(Usuario, regular_user))
    own = client.get("/api/mi-cuenta")
    assert own.status_code == 200
    assert own.get_json()["data"]["correo"] == "ana@example.test"
    assert "qr_token" not in own.get_json()["data"]
    assert client.get("/api/mi-cuenta/qr").mimetype == "image/png"
    assert client.get(f"/api/personas/{other_id}").status_code == 403
    assert client.get(f"/api/personas/{other_id}/qr").status_code == 403


def test_inactive_account_and_inactive_person_are_rejected(client, app, person):
    with app.app_context():
        person_row = db.session.get(Persona, person)
        inactive = create_user(person_row, activo=False)
        login(client, inactive)
    assert client.get("/mi-cuenta").status_code == 302

    with app.app_context():
        inactive.activo = True
        person_row.activo = False
        db.session.commit()
        login(client, inactive)
    assert client.get("/mi-cuenta").status_code == 302


def test_unknown_and_duplicate_email_do_not_get_access(app):
    claims = {"sub": "unknown", "email": "unknown@example.test", "email_verified": True}
    with app.app_context():
        user, error = authenticate_claims(claims)
        assert user is None and error
        create_person(correo="duplicate@example.test")
        create_person(correo="DUPLICATE@example.test")
        user, error = authenticate_claims(
            {**claims, "sub": "duplicate", "email": "duplicate@example.test"}
        )
        assert user is None and error


def test_events_are_scoped_to_current_user(client, app, regular_user, person):
    with app.app_context():
        own = db.session.get(Persona, person)
        other = create_person(correo="other@example.test", sede="Norte")
        visible = Evento(
            nombre="General",
            fecha=date.today() + timedelta(days=1),
            hora_inicio=time(9),
            sede="",
            estado="abierto",
        )
        same_site = Evento(
            nombre="Centro",
            fecha=date.today() + timedelta(days=2),
            hora_inicio=time(9),
            sede="Centro",
            estado="abierto",
        )
        wrong_site = Evento(
            nombre="Norte",
            fecha=date.today() + timedelta(days=1),
            hora_inicio=time(9),
            sede="Norte",
            estado="abierto",
        )
        closed = Evento(
            nombre="Cerrado",
            fecha=date.today() + timedelta(days=1),
            hora_inicio=time(9),
            sede="Centro",
            estado="cerrado",
        )
        past = Evento(
            nombre="Pasado",
            fecha=date.today() - timedelta(days=1),
            hora_inicio=time(9),
            sede="Centro",
            estado="abierto",
        )
        db.session.add_all([visible, same_site, wrong_site, closed, past])
        db.session.flush()
        db.session.add_all(
            [
                Asistencia(persona=own, evento=past),
                Asistencia(persona=other, evento=wrong_site),
            ]
        )
        db.session.commit()
        login(client, db.session.get(Usuario, regular_user))
    data = client.get("/api/mi-cuenta/eventos").get_json()["data"]
    assert [item["evento"] for item in data["asistencias"]] == ["Pasado"]
    assert [item["nombre"] for item in data["proximos"]] == ["General", "Centro"]


def test_logout_is_post_and_clears_session(client, app, regular_user):
    with app.app_context():
        login(client, db.session.get(Usuario, regular_user))
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
    assert client.get("/mi-cuenta").status_code == 302


def test_csrf_is_required_for_writes():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
            "SESSION_PROTECTION": None,
        }
    )
    login_manager.session_protection = None
    with application.app_context():
        db.create_all()
        admin = create_user(email="admin@example.test", rol="admin", person=None)
        admin_id = admin.id
    client = application.test_client()
    with application.app_context():
        login(client, db.session.get(Usuario, admin_id))
    assert client.post("/api/personas", json={}).status_code == 400
    page = client.get("/admin")
    token = (
        re.search(rb'<meta name="csrf-token" content="([^"]+)"', page.data)
        .group(1)
        .decode()
    )
    response = client.post("/api/personas", json={}, headers={"X-CSRFToken": token})
    assert response.status_code == 400
    assert response.get_json()["message"] == "Datos inválidos"


def test_cli_admin_creation_is_idempotent(app):
    runner = app.test_cli_runner()
    first = runner.invoke(
        args=["users", "create-admin", "--email", "ADMIN@example.test"]
    )
    second = runner.invoke(
        args=["users", "create-admin", "--email", "admin@example.test"]
    )
    assert first.exit_code == second.exit_code == 0
    with app.app_context():
        assert Usuario.query.count() == 1
        assert Usuario.query.one().is_admin


def test_production_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "mysql://user:password@host/database")
    application = create_app()
    assert application.config["DEBUG"] is False
    assert application.config["SESSION_COOKIE_SECURE"] is True
    assert application.config["SESSION_COOKIE_HTTPONLY"] is True
    assert application.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert application.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql+pymysql://")


def test_wsgi_import():
    from wsgi import app

    assert app is not None
