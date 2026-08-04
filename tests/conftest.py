import secrets

import pytest

from app import create_app, db, login_manager
from app.models import Iglesia, MembresiaIglesia, Persona, Usuario


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


def create_church(**overrides):
    values = {
        "nombre": f"Iglesia {secrets.token_hex(2)}",
        "slug": f"iglesia-{secrets.token_hex(3)}",
        "ciudad": "Guatemala",
        "pais": "Guatemala",
        "activa": True,
    }
    values.update(overrides)
    church = Iglesia(**values)
    db.session.add(church)
    db.session.commit()
    return church


def create_person(church, **overrides):
    values = {
        "iglesia_id": church.id,
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


def create_user(**overrides):
    values = {
        "email": f"user-{secrets.token_hex(3)}@example.test",
        "nombre": "Usuario Prueba",
        "activo": True,
        "proveedor": "google",
        "proveedor_subject": f"subject-{secrets.token_hex(3)}",
    }
    values.update(overrides)
    user = Usuario(**values)
    db.session.add(user)
    db.session.commit()
    return user


def create_membership(user, church, person=None, **overrides):
    values = {
        "usuario_id": user.id,
        "iglesia_id": church.id,
        "persona_id": person.id if person else None,
        "rol": "usuario",
        "estado": "activo",
    }
    values.update(overrides)
    membership = MembresiaIglesia(**values)
    db.session.add(membership)
    db.session.commit()
    return membership


def login(client, user, church=None):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
        if church:
            session["iglesia_id"] = church.id
        else:
            session.pop("iglesia_id", None)


@pytest.fixture()
def churches(app):
    with app.app_context():
        first = create_church(nombre="Iglesia Uno", slug="iglesia-uno")
        second = create_church(nombre="Iglesia Dos", slug="iglesia-dos")
        return first.id, second.id
