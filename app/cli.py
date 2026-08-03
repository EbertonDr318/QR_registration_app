import click
from flask.cli import AppGroup
from sqlalchemy import func

from . import db
from .models import Persona, Usuario

users_cli = AppGroup("users", help="Administra cuentas y roles.")


def _user(email):
    normalized = Usuario.normalize_email(email)
    return Usuario.query.filter(func.lower(Usuario.email) == normalized).first()


@users_cli.command("create-admin")
@click.option("--email", required=True)
@click.option("--name")
def create_admin(email, name):
    normalized = Usuario.normalize_email(email)
    user = _user(normalized)
    if user:
        changed = []
        if not user.is_admin:
            user.rol = "admin"
            changed.append("rol admin")
        if not user.activo:
            user.activo = True
            changed.append("cuenta activada")
        if name:
            user.nombre = name[:160]
            changed.append("nombre actualizado")
        db.session.commit()
        click.echo(
            f"Administrador existente: {normalized} ({', '.join(changed) or 'sin cambios'})."
        )
        return
    db.session.add(
        Usuario(
            email=normalized,
            nombre=(name or normalized)[:160],
            rol="admin",
            activo=True,
        )
    )
    db.session.commit()
    click.echo(f"Administrador creado: {normalized}.")


def _change_status(email, active):
    user = _user(email)
    if not user:
        raise click.ClickException("La cuenta no existe.")
    user.activo = active
    db.session.commit()
    click.echo(f"Cuenta {'activada' if active else 'desactivada'}: {user.email}.")


@users_cli.command("activate")
@click.option("--email", required=True)
def activate(email):
    _change_status(email, True)


@users_cli.command("deactivate")
@click.option("--email", required=True)
def deactivate(email):
    _change_status(email, False)


@users_cli.command("set-role")
@click.option("--email", required=True)
@click.option("--role", type=click.Choice(["usuario", "admin"]), required=True)
def set_role(email, role):
    user = _user(email)
    if not user:
        raise click.ClickException("La cuenta no existe.")
    if role == "usuario" and not user.persona:
        raise click.ClickException(
            "Vincula una persona antes de asignar el rol usuario."
        )
    user.rol = role
    db.session.commit()
    click.echo(f"Rol actualizado: {user.email} -> {role}.")


@users_cli.command("link-persona")
@click.option("--email", required=True)
@click.option("--persona-id", type=int, required=True)
def link_persona(email, persona_id):
    user = _user(email)
    person = db.session.get(Persona, persona_id)
    if not user or not person:
        raise click.ClickException("La cuenta o la persona no existe.")
    if person.usuario and person.usuario.id != user.id:
        raise click.ClickException("La persona ya está vinculada a otra cuenta.")
    user.persona = person
    db.session.commit()
    click.echo(f"Cuenta {user.email} vinculada a persona {person.id}.")
