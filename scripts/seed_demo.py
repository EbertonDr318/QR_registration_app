from datetime import date, time, timedelta
from pathlib import Path
import secrets, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app,db
from app.models import Persona,Evento,Asistencia

app=create_app()
with app.app_context():
    if Persona.query.first(): raise SystemExit("La base ya contiene personas; no se insertaron duplicados.")
    people=[("DEM-001","Ana","López","Centro","Jóvenes"),("DEM-002","Bruno","Méndez","Centro","Adultos"),("DEM-003","Carla","Pérez","Norte","Jóvenes"),("DEM-004","Diego","Ramírez","Norte","Adultos"),("DEM-005","Elena","Torres","Centro","Jóvenes"),("DEM-006","Fabio","Santos","Norte","Adultos")]
    persons=[Persona(codigo=c,nombres=n,apellidos=a,sede=s,grupo=g,correo=f"{c.lower()}@example.test",qr_token=secrets.token_urlsafe(32)) for c,n,a,s,g in people]
    events=[Evento(nombre="Jornada de bienvenida",descripcion="Evento ficticio de demostración",fecha=date.today(),hora_inicio=time(9),sede="Centro"),Evento(nombre="Taller comunitario",descripcion="Segundo evento ficticio",fecha=date.today()+timedelta(days=7),hora_inicio=time(15),sede="Norte",estado="cerrado")]
    db.session.add_all(persons+events);db.session.flush();db.session.add_all([Asistencia(persona=persons[i],evento=events[0],metodo_registro="manual") for i in range(3)]);db.session.commit();print("Datos ficticios insertados correctamente.")
