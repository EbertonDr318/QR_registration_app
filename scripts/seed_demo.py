from datetime import date, time, timedelta
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db
from app.models import Asistencia, Evento, Iglesia, Persona


app = create_app()
with app.app_context():
    if Persona.query.first():
        raise SystemExit("La base ya contiene personas; no se insertaron duplicados.")

    church = Iglesia.query.filter_by(slug="iglesia-principal").first()
    if not church:
        church = Iglesia(nombre="Iglesia Principal", slug="iglesia-principal")
        db.session.add(church)
        db.session.flush()

    people = [
        ("DEM-001", "Ana", "López", "Centro", "Jóvenes"),
        ("DEM-002", "Bruno", "Méndez", "Centro", "Adultos"),
        ("DEM-003", "Carla", "Pérez", "Norte", "Jóvenes"),
        ("DEM-004", "Diego", "Ramírez", "Norte", "Adultos"),
        ("DEM-005", "Elena", "Torres", "Centro", "Jóvenes"),
        ("DEM-006", "Fabio", "Santos", "Norte", "Adultos"),
    ]
    persons = [
        Persona(
            iglesia=church,
            codigo=code,
            nombres=first_name,
            apellidos=last_name,
            sede=site,
            grupo=group,
            correo=f"{code.lower()}@example.test",
            qr_token=secrets.token_urlsafe(32),
        )
        for code, first_name, last_name, site, group in people
    ]
    events = [
        Evento(
            iglesia=church,
            nombre="Jornada de bienvenida",
            descripcion="Evento ficticio de demostración",
            fecha=date.today(),
            hora_inicio=time(9),
            sede="Centro",
        ),
        Evento(
            iglesia=church,
            nombre="Taller comunitario",
            descripcion="Segundo evento ficticio",
            fecha=date.today() + timedelta(days=7),
            hora_inicio=time(15),
            sede="Norte",
            estado="cerrado",
        ),
    ]
    db.session.add_all(persons + events)
    db.session.flush()
    db.session.add_all(
        [
            Asistencia(
                iglesia=church,
                persona=persons[index],
                evento=events[0],
                metodo_registro="manual",
            )
            for index in range(3)
        ]
    )
    db.session.commit()
    print("Datos ficticios insertados correctamente.")
