from app import db
from app.models import Persona

def test_person_create_duplicate_list_update_and_state(client,person):
    assert person["codigo"]=="P-001"
    assert client.post('/api/personas',json={"codigo":"P-001","nombres":"Otra","apellidos":"Persona"}).status_code==409
    assert len(client.get('/api/personas').get_json()["data"])==1
    updated=client.put(f'/api/personas/{person["id"]}',json={**person,"nombres":"Anita"})
    assert updated.status_code==200 and updated.get_json()["data"]["nombres"]=="Anita"
    off=client.patch(f'/api/personas/{person["id"]}/estado',json={"activo":False})
    assert off.get_json()["data"]["activo"] is False
    assert client.patch(f'/api/personas/{person["id"]}/estado',json={"activo":True}).status_code==200

def test_event_create_and_close(client,event):
    assert event["estado"]=="abierto"
    closed=client.patch(f'/api/eventos/{event["id"]}/estado',json={"estado":"cerrado"})
    assert closed.status_code==200 and closed.get_json()["data"]["estado"]=="cerrado"

def test_attendance_success_duplicate_invalid_and_export(client,app,person,event):
    with app.app_context(): token=db.session.get(Persona,person["id"]).qr_token
    payload={"evento_id":event["id"],"token":token}
    good=client.post('/api/asistencias/registrar',json=payload)
    assert good.status_code==201 and good.get_json()["data"]["metodo_registro"]=="qr"
    assert client.post('/api/asistencias/registrar',json=payload).status_code==409
    assert client.post('/api/asistencias/registrar',json={"evento_id":event["id"],"token":"manipulado"}).status_code==404
    assert len(client.get('/api/asistencias').get_json()["data"])==1
    csv=client.get('/api/asistencias/exportar')
    assert csv.status_code==200 and csv.data.startswith(b'\xef\xbb\xbf') and b'P-001' in csv.data

def test_inactive_and_closed_rejected(client,app,person,event):
    with app.app_context():
        p=db.session.get(Persona,person["id"]);p.activo=False;token=p.qr_token;db.session.commit()
    assert client.post('/api/asistencias/registrar',json={"evento_id":event["id"],"token":token}).status_code==409
    client.patch(f'/api/personas/{person["id"]}/estado',json={"activo":True})
    client.patch(f'/api/eventos/{event["id"]}/estado',json={"estado":"cerrado"})
    assert client.post('/api/asistencias/registrar',json={"evento_id":event["id"],"token":token}).status_code==409

def test_qr_and_pages(client,person):
    assert client.get(f'/api/personas/{person["id"]}/qr').mimetype=='image/png'
    for path in ('/','/personas','/eventos','/escaner','/asistencias'):assert client.get(path).status_code==200

def test_health_and_backend_reports(client, person, event):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok"}

    client.post("/api/asistencias/registrar", json={"evento_id": event["id"], "codigo": person["codigo"]})
    assert client.get("/api/asistencias/exportar.pdf").mimetype == "application/pdf"
    assert client.get("/api/asistencias/exportar.xlsx").mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def test_production_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "mysql://user:password@host/database")
    from app import create_app

    application = create_app()
    assert application.config["DEBUG"] is False
    assert application.config["SESSION_COOKIE_SECURE"] is True
    assert application.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql+pymysql://")

def test_wsgi_import():
    from wsgi import app

    assert app is not None
