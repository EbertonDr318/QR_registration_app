import secrets

import pytest

from app import create_app, db, login_manager
from app.models import Evento, Persona, Usuario


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SESSION_PROTECTION": None,
            "DEBUG": False,
        }
    )
    login_manager.session_protection = None
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_person(**overrides):
    values = {
        "codigo": f"P-{secrets.token_hex(3)}",
        "nombres": "Ana",
        "apellidos": "Prueba",
        "correo": "ana@example.test",
        "sede": "Centro",
        "grupo": "A",
        "qr_token": secrets.token_urlsafe(32),
        "activo": True,
    }
    values.update(overrides)
    person = Persona(**values)
    db.session.add(person)
    db.session.commit()
    return person


def create_user(person=None, **overrides):
    values = {
        "email": "ana@example.test",
        "nombre": "Ana Prueba",
        "rol": "usuario",
        "activo": True,
        "proveedor": "google",
        "proveedor_subject": f"subject-{secrets.token_hex(3)}",
        "persona": person,
    }
    values.update(overrides)
    user = Usuario(**values)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


@pytest.fixture()
def person(app):
    with app.app_context():
        person = create_person()
        return person.id


@pytest.fixture()
def regular_user(app, person):
    with app.app_context():
        return create_user(db.session.get(Persona, person)).id


@pytest.fixture()
def admin_user(app):
    with app.app_context():
        return create_user(
            email="admin@example.test",
            nombre="Admin",
            rol="admin",
            person=None,
        ).id


@pytest.fixture()
def event(app):
    from datetime import date, time, timedelta

    with app.app_context():
        event = Evento(
            nombre="Jornada",
            fecha=date.today() + timedelta(days=1),
            hora_inicio=time(9),
            sede="Centro",
            estado="abierto",
        )
        db.session.add(event)
        db.session.commit()
        return event.id
