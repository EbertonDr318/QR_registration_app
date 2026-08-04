import re
from datetime import date, time, timedelta
from pathlib import Path

from app import create_app, db, login_manager
from app.auth import _google_callback_url, authenticate_claims
from app.models import (
    Asistencia,
    Evento,
    Iglesia,
    MembresiaIglesia,
    Persona,
    RegistroAuditoria,
    Usuario,
)
from conftest import create_church, create_membership, create_person, create_user, login


def test_visitor_is_redirected_and_health_is_public(client):
    assert client.get("/").headers["Location"].endswith("/login")
    assert client.get("/api/personas").status_code == 401
    assert client.get("/health").get_json() == {"status": "ok"}


def test_verified_login_creates_global_user_without_membership(app):
    with app.app_context():
        user, error = authenticate_claims(
            {
                "sub": "google-1",
                "email": " USER@EXAMPLE.TEST ",
                "email_verified": True,
                "name": "User",
            }
        )
        assert error is None
        assert user.email == "user@example.test"
        assert user.membresias == []
        assert not hasattr(user, "rol")


def test_unverified_email_and_inactive_account_are_rejected(app):
    with app.app_context():
        user, error = authenticate_claims(
            {"sub": "bad", "email": "bad@example.test", "email_verified": False}
        )
        assert user is None and error
        create_user(email="off@example.test", proveedor_subject="off", activo=False)
        user, error = authenticate_claims(
            {"sub": "off", "email": "off@example.test", "email_verified": True}
        )
        assert user is None and error


def test_one_membership_selects_automatically(client, app, churches):
    with app.app_context():
        church = db.session.get(Iglesia, churches[0])
        person = create_person(church)
        user = create_user(email=person.correo)
        create_membership(user, church, person)
        login(client, user)
    response = client.get("/")
    assert response.headers["Location"].endswith("/mi-cuenta")
    with client.session_transaction() as session:
        assert session["iglesia_id"] == churches[0]


def test_multiple_memberships_show_selector_and_reject_foreign_church(
    client, app, churches
):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        outsider = create_church(nombre="Ajena", slug="ajena")
        user = create_user()
        create_membership(user, first, rol="admin")
        create_membership(user, second, rol="usuario")
        outsider_id = outsider.id
        login(client, user)
    assert client.get("/").headers["Location"].endswith("/seleccionar-iglesia")
    assert b"Iglesia Uno" in client.get("/seleccionar-iglesia").data
    assert (
        client.post(
            "/seleccionar-iglesia", data={"iglesia_id": outsider_id}
        ).status_code
        == 403
    )


def test_user_can_have_different_roles_per_church(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        user = create_user()
        create_membership(user, first, rol="admin")
        create_membership(user, second, rol="usuario")
        login(client, user, first)
    assert client.get("/admin").status_code == 200
    response = client.post("/cambiar-iglesia", data={"iglesia_id": churches[1]})
    assert response.headers["Location"].endswith("/mi-cuenta")
    assert client.get("/admin").status_code == 403


def test_no_membership_goes_to_onboarding(client, app, churches):
    with app.app_context():
        user = create_user()
        login(client, user)
    assert client.get("/").headers["Location"].endswith("/unirse")
    page = client.get("/unirse")
    assert b"Iglesia Uno" in page.data and b"Iglesia Dos" in page.data


def test_onboarding_creates_pending_person_as_regular_user(client, app, churches):
    with app.app_context():
        church = db.session.get(Iglesia, churches[0])
        user = create_user(email="join@example.test")
        user_id = user.id
        login(client, user)
    response = client.post("/unirse", data={"iglesia_id": churches[0]})
    assert response.headers["Location"].endswith("/unirse")
    with app.app_context():
        membership = MembresiaIglesia.query.filter_by(usuario_id=user_id).one()
        assert membership.estado == "pendiente"
        assert membership.rol == "usuario"
        assert membership.persona.codigo == "UX-USER-001"
        assert membership.persona.correo == "join@example.test"


def test_onboarding_assigns_sequential_codes_without_duplicates(client, app, churches):
    with app.app_context():
        church = db.session.get(Iglesia, churches[0])
        first_user = create_user(email="pending@example.test")
        first_id = first_user.id
        login(client, first_user)
    client.post("/unirse", data={"iglesia_id": churches[0]})
    with app.app_context():
        second_user = create_user(email="duplicate@example.test")
        second_id = second_user.id
        login(client, second_user)
    client.post("/unirse", data={"iglesia_id": churches[0]})
    with app.app_context():
        first = MembresiaIglesia.query.filter_by(usuario_id=first_id).one()
        membership = MembresiaIglesia.query.filter_by(usuario_id=second_id).one()
        assert first.persona.codigo == "UX-USER-001"
        assert membership.persona.codigo == "UX-USER-002"
        assert Persona.query.filter_by(iglesia_id=churches[0]).count() == 2


def test_admin_lists_only_current_tenant_data(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        own = create_person(first, codigo="SAME", nombres="Propia")
        other = create_person(second, codigo="SAME", nombres="Ajena")
        user = create_user()
        create_membership(user, first, rol="admin")
        login(client, user, first)
        own_id = own.id
        other_id = other.id
    data = client.get("/api/personas").get_json()["data"]
    assert [row["nombres"] for row in data] == ["Propia"]
    assert client.get(f"/api/personas/{other_id}").status_code == 404
    assert own_id != other_id


def test_events_attendance_and_reports_are_tenant_scoped(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        person_one = create_person(first, codigo="ONE")
        person_two = create_person(second, codigo="TWO")
        event_one = Evento(
            iglesia=first, nombre="Evento Uno", fecha=date.today(), hora_inicio=time(9)
        )
        event_two = Evento(
            iglesia=second, nombre="Evento Dos", fecha=date.today(), hora_inicio=time(9)
        )
        db.session.add_all([event_one, event_two])
        db.session.flush()
        db.session.add_all(
            [
                Asistencia(iglesia=first, persona=person_one, evento=event_one),
                Asistencia(iglesia=second, persona=person_two, evento=event_two),
            ]
        )
        user = create_user()
        create_membership(user, first, rol="admin")
        db.session.commit()
        login(client, user, first)
    assert [e["nombre"] for e in client.get("/api/eventos").get_json()["data"]] == [
        "Evento Uno"
    ]
    attendance = client.get("/api/asistencias").get_json()["data"]
    assert [row["codigo"] for row in attendance] == ["ONE"]
    csv = client.get("/api/asistencias/exportar").data
    assert b"ONE" in csv and b"TWO" not in csv
    assert client.get("/api/asistencias/exportar.xlsx").status_code == 200
    assert client.get("/api/asistencias/exportar.pdf").status_code == 200


def test_cross_tenant_attendance_is_rejected(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        foreign_person = create_person(second, codigo="FOREIGN")
        event = Evento(
            iglesia=first, nombre="Local", fecha=date.today(), hora_inicio=time(9)
        )
        db.session.add(event)
        user = create_user()
        create_membership(user, first, rol="admin")
        db.session.commit()
        event_id = event.id
        token = foreign_person.qr_token
        login(client, user, first)
    response = client.post(
        "/api/asistencias/registrar", json={"evento_id": event_id, "token": token}
    )
    assert response.status_code == 404


def test_regular_user_only_sees_membership_person_and_own_qr(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        own = create_person(first, correo="own@example.test")
        other = create_person(first, correo="other@example.test")
        user = create_user(email="own@example.test")
        create_membership(user, first, own)
        own_id = own.id
        other_id = other.id
        login(client, user, first)
    own_data = client.get("/api/mi-cuenta").get_json()["data"]
    assert own_data["id"] == own_id and "qr_token" not in own_data
    assert client.get("/api/mi-cuenta/qr").mimetype == "image/png"
    assert client.get(f"/api/personas/{other_id}").status_code == 403


def test_upcoming_events_follow_church_date_state_and_site(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        person = create_person(first, sede="Centro")
        user = create_user()
        create_membership(user, first, person)
        events = [
            Evento(
                iglesia=first,
                nombre="General",
                fecha=date.today() + timedelta(days=1),
                hora_inicio=time(9),
                sede="",
            ),
            Evento(
                iglesia=first,
                nombre="Centro",
                fecha=date.today() + timedelta(days=2),
                hora_inicio=time(9),
                sede="Centro",
            ),
            Evento(
                iglesia=first,
                nombre="Otra sede",
                fecha=date.today(),
                hora_inicio=time(9),
                sede="Norte",
            ),
            Evento(
                iglesia=first,
                nombre="Cerrado",
                fecha=date.today(),
                hora_inicio=time(9),
                sede="Centro",
                estado="cerrado",
            ),
            Evento(
                iglesia=second,
                nombre="Otro tenant",
                fecha=date.today(),
                hora_inicio=time(9),
                sede="Centro",
            ),
        ]
        db.session.add_all(events)
        db.session.commit()
        login(client, user, first)
    names = [
        row["nombre"]
        for row in client.get("/api/mi-cuenta/eventos").get_json()["data"]["proximos"]
    ]
    assert names == ["General", "Centro"]


def test_suspended_membership_immediately_loses_access(client, app, churches):
    with app.app_context():
        church = db.session.get(Iglesia, churches[0])
        person = create_person(church)
        user = create_user()
        membership = create_membership(user, church, person)
        membership_id = membership.id
        login(client, user, church)
    assert client.get("/mi-cuenta").status_code == 200
    with app.app_context():
        db.session.get(MembresiaIglesia, membership_id).estado = "suspendido"
        db.session.commit()
    assert client.get("/mi-cuenta").status_code == 403


def test_admin_membership_actions_are_scoped_and_audited(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        admin_user = create_user()
        create_membership(admin_user, first, rol="admin")
        target = create_membership(create_user(), first, estado="pendiente")
        foreign = create_membership(create_user(), second, estado="pendiente")
        target_id, foreign_id = target.id, foreign.id
        login(client, admin_user, first)
    assert client.get("/admin/membresias").status_code == 200
    assert client.get("/admin/configuracion").status_code == 200
    assert (
        client.post(
            f"/admin/membresias/{foreign_id}/estado", data={"estado": "activo"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/admin/membresias/{target_id}/rol", data={"rol": "admin"}
        ).status_code
        == 302
    )
    with app.app_context():
        assert db.session.get(MembresiaIglesia, target_id).rol == "admin"
        assert (
            RegistroAuditoria.query.filter_by(
                iglesia_id=churches[0], accion="cambiar_rol"
            ).count()
            == 1
        )


def test_admin_updates_only_current_church_settings(client, app, churches):
    with app.app_context():
        first = db.session.get(Iglesia, churches[0])
        second = db.session.get(Iglesia, churches[1])
        original_second_name = second.nombre
        admin_user = create_user()
        create_membership(admin_user, first, rol="admin")
        login(client, admin_user, first)

    response = client.post(
        "/admin/configuracion",
        data={
            "nombre": "Iglesia Actualizada",
            "ciudad": "Mixco",
            "pais": "Guatemala",
            "zona_horaria": "America/Guatemala",
            "descripcion": "Datos editados durante la prueba de usabilidad.",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Iglesia, churches[0]).nombre == "Iglesia Actualizada"
        assert db.session.get(Iglesia, churches[1]).nombre == original_second_name
        assert (
            RegistroAuditoria.query.filter_by(
                iglesia_id=churches[0], accion="actualizar_iglesia"
            ).count()
            == 1
        )


def test_membership_page_explains_link_and_preserves_current_values(
    client, app, churches
):
    with app.app_context():
        church = db.session.get(Iglesia, churches[0])
        admin_user = create_user()
        create_membership(admin_user, church, rol="admin")
        person = create_person(church, codigo="UX-USER-001")
        create_membership(
            create_user(), church, person=person, rol="usuario", estado="pendiente"
        )
        login(client, admin_user, church)
    page = client.get("/admin/membresias")
    assert page.status_code == 200
    assert b"Autorizar ingreso" in page.data
    assert b"Rechazar solicitud" in page.data
    assert b"Ficha asignada: UX-USER-001" in page.data
    assert b"Cambiar rol" not in page.data
    assert b"Vincular ficha" not in page.data


def test_csrf_protects_api_and_tenant_selection():
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
        church = create_church(nombre="CSRF", slug="csrf")
        user = create_user()
        create_membership(user, church, rol="admin")
        user_id, church_id = user.id, church.id
    client = application.test_client()
    with application.app_context():
        login(
            client, db.session.get(Usuario, user_id), db.session.get(Iglesia, church_id)
        )
    assert client.post("/api/personas", json={}).status_code == 400
    assert (
        client.post("/cambiar-iglesia", data={"iglesia_id": church_id}).status_code
        == 400
    )
    page = client.get("/admin")
    token = (
        re.search(rb'<meta name="csrf-token" content="([^"]+)"', page.data)
        .group(1)
        .decode()
    )
    response = client.post("/api/personas", json={}, headers={"X-CSRFToken": token})
    assert response.get_json()["message"] == "Datos inválidos"


def test_logout_is_post_and_clears_tenant_session(client, app, churches):
    with app.app_context():
        church = db.session.get(Iglesia, churches[0])
        user = create_user()
        create_membership(user, church, rol="admin")
        login(client, user, church)
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
    with client.session_transaction() as session:
        assert "_user_id" not in session and "iglesia_id" not in session


def test_cli_creates_church_and_admin_idempotently(app):
    runner = app.test_cli_runner()
    args = [
        "iglesias",
        "bootstrap",
        "--nombre",
        "Principal",
        "--slug",
        "principal",
        "--admin-email",
        "admin@example.test",
    ]
    assert runner.invoke(args=args).exit_code == 0
    assert runner.invoke(args=args).exit_code == 0
    with app.app_context():
        assert (
            Iglesia.query.count()
            == Usuario.query.count()
            == MembresiaIglesia.query.count()
            == 1
        )
        assert MembresiaIglesia.query.one().is_admin


def test_public_base_url_builds_exact_google_callback(app):
    app.config["PUBLIC_BASE_URL"] = "https://example.up.railway.app"
    with app.test_request_context():
        assert (
            _google_callback_url()
            == "https://example.up.railway.app/auth/google/callback"
        )


def test_migration_assigns_existing_records_without_rotating_qr():
    path = Path("migrations/versions/8de9dc5a35bd_agregar_arquitectura_multiiglesia.py")
    migration = path.read_text(encoding="utf-8")
    assert "Iglesia Principal" in migration
    assert "UPDATE personas SET iglesia_id" in migration
    assert "UPDATE eventos SET iglesia_id" in migration
    assert "UPDATE asistencias SET iglesia_id" in migration
    assert "qr_token" not in migration
    assert "DROP DATABASE" not in migration.upper()


def test_production_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "test-only-production-secret")
    monkeypatch.setenv("DATABASE_URL", "mysql://user:password@host/database")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.up.railway.app")
    application = create_app()
    assert application.config["SESSION_COOKIE_SECURE"] is True
    assert application.config["SESSION_COOKIE_HTTPONLY"] is True
    assert application.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert application.config["PREFERRED_URL_SCHEME"] == "https"
    assert application.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql+pymysql://")


def test_wsgi_import():
    from wsgi import app

    assert app is not None
