import re
from datetime import datetime

import click
from flask.cli import AppGroup
from sqlalchemy import func

from . import db
from .audit import record_audit
from .models import Iglesia, MembresiaIglesia, Persona, Usuario

churches_cli = AppGroup("iglesias", help="Administra iglesias de la plataforma.")
memberships_cli = AppGroup("membresias", help="Administra membresías por iglesia.")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalized_email(email):
    normalized = Usuario.normalize_email(email)
    if "@" not in normalized:
        raise click.ClickException("El correo no es válido.")
    return normalized


def _church(slug):
    church = Iglesia.query.filter_by(slug=str(slug or "").strip().casefold()).first()
    if not church:
        raise click.ClickException("La iglesia no existe.")
    return church


def _user(email, create=False):
    normalized = _normalized_email(email)
    user = Usuario.query.filter(func.lower(Usuario.email) == normalized).first()
    if not user and create:
        user = Usuario(
            email=normalized,
            nombre=normalized,
            proveedor="google",
            activo=True,
        )
        db.session.add(user)
        db.session.flush()
    if not user:
        raise click.ClickException("La cuenta no existe.")
    return user


def _membership(church, email):
    user = _user(email)
    membership = MembresiaIglesia.query.filter_by(
        iglesia_id=church.id, usuario_id=user.id
    ).first()
    if not membership:
        raise click.ClickException("La membresía no existe.")
    return membership


def _bootstrap_church(nombre, slug, admin_email):
    name = str(nombre or "").strip()[:160]
    normalized_slug = str(slug or "").strip().casefold()[:100]
    if len(name) < 2 or not SLUG.fullmatch(normalized_slug):
        raise click.ClickException("Nombre o slug inválido.")
    church = Iglesia.query.filter_by(slug=normalized_slug).first()
    if not church:
        church = Iglesia(nombre=name, slug=normalized_slug, pais="Guatemala")
        db.session.add(church)
        db.session.flush()
    user = _user(admin_email, create=True)
    membership = MembresiaIglesia.query.filter_by(
        usuario_id=user.id, iglesia_id=church.id
    ).first()
    if not membership:
        membership = MembresiaIglesia(usuario=user, iglesia=church)
        db.session.add(membership)
    membership.rol = "admin"
    membership.estado = "activo"
    membership.fecha_aprobacion = membership.fecha_aprobacion or datetime.now()
    record_audit(
        church.id, "crear_iglesia", "iglesia", church.id, {"slug": church.slug}
    )
    db.session.commit()
    click.echo(f"Iglesia lista: {church.slug}; administrador: {user.email}.")


@churches_cli.command("create")
@click.option("--nombre", required=True)
@click.option("--slug", required=True)
@click.option("--admin-email", required=True)
def create_church(nombre, slug, admin_email):
    _bootstrap_church(nombre, slug, admin_email)


@churches_cli.command("bootstrap")
@click.option("--nombre", required=True)
@click.option("--slug", required=True)
@click.option("--admin-email", required=True)
def bootstrap_church(nombre, slug, admin_email):
    _bootstrap_church(nombre, slug, admin_email)


@churches_cli.command("list")
def list_churches():
    for church in Iglesia.query.order_by(Iglesia.nombre).all():
        click.echo(
            f"{church.slug}\t{church.nombre}\t{'activa' if church.activa else 'inactiva'}"
        )


@churches_cli.command("rename")
@click.option("--slug", required=True)
@click.option("--nombre", required=True)
def rename_church(slug, nombre):
    church = _church(slug)
    name = str(nombre or "").strip()[:160]
    if len(name) < 2:
        raise click.ClickException("El nombre no es válido.")
    church.nombre = name
    db.session.commit()
    click.echo(f"Iglesia actualizada: {church.slug}.")


@memberships_cli.command("create-admin")
@click.option("--iglesia", required=True)
@click.option("--email", required=True)
def create_admin(iglesia, email):
    church = _church(iglesia)
    user = _user(email, create=True)
    membership = MembresiaIglesia.query.filter_by(
        usuario_id=user.id, iglesia_id=church.id
    ).first()
    if not membership:
        membership = MembresiaIglesia(usuario=user, iglesia=church)
        db.session.add(membership)
    membership.rol = "admin"
    membership.estado = "activo"
    membership.fecha_aprobacion = membership.fecha_aprobacion or datetime.now()
    record_audit(
        church.id, "crear_admin", "membresia", membership.id, {"email": user.email}
    )
    db.session.commit()
    click.echo(f"Administrador listo: {user.email} en {church.slug}.")


@memberships_cli.command("set-role")
@click.option("--iglesia", required=True)
@click.option("--email", required=True)
@click.option("--role", type=click.Choice(["usuario", "admin"]), required=True)
def set_role(iglesia, email, role):
    church = _church(iglesia)
    membership = _membership(church, email)
    previous = membership.rol
    membership.rol = role
    record_audit(
        church.id,
        "cambiar_rol",
        "membresia",
        membership.id,
        {"rol_anterior": previous, "rol_nuevo": role},
    )
    db.session.commit()
    click.echo(f"Rol actualizado: {membership.usuario.email} -> {role}.")


def _set_state(iglesia, email, state):
    church = _church(iglesia)
    membership = _membership(church, email)
    previous = membership.estado
    membership.estado = state
    if state == "activo":
        membership.fecha_aprobacion = membership.fecha_aprobacion or datetime.now()
    record_audit(
        church.id,
        f"membresia_{state}",
        "membresia",
        membership.id,
        {"estado_anterior": previous},
    )
    db.session.commit()
    click.echo(f"Membresía {state}: {membership.usuario.email}.")


@memberships_cli.command("activate")
@click.option("--iglesia", required=True)
@click.option("--email", required=True)
def activate_membership(iglesia, email):
    _set_state(iglesia, email, "activo")


@memberships_cli.command("suspend")
@click.option("--iglesia", required=True)
@click.option("--email", required=True)
def suspend_membership(iglesia, email):
    _set_state(iglesia, email, "suspendido")


@memberships_cli.command("link-persona")
@click.option("--iglesia", required=True)
@click.option("--email", required=True)
@click.option("--persona-id", type=int, required=True)
def link_persona(iglesia, email, persona_id):
    church = _church(iglesia)
    membership = _membership(church, email)
    person = Persona.query.filter_by(id=persona_id, iglesia_id=church.id).first()
    if not person:
        raise click.ClickException("La persona no pertenece a esta iglesia.")
    membership.persona = person
    record_audit(
        church.id,
        "vincular_persona",
        "membresia",
        membership.id,
        {"persona_id": person.id},
    )
    db.session.commit()
    click.echo(f"Membresía vinculada a persona {person.id}.")
