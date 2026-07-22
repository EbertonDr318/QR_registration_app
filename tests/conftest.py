import pytest
from app import create_app,db

@pytest.fixture()
def app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","DEBUG":False})
    with app.app_context(): db.create_all()
    yield app
    with app.app_context(): db.drop_all()
@pytest.fixture()
def client(app):return app.test_client()
@pytest.fixture()
def person(client):
    return client.post('/api/personas',json={"codigo":"P-001","nombres":"Ana","apellidos":"Prueba","correo":"ana@example.test","sede":"Centro","grupo":"A"}).get_json()["data"]
@pytest.fixture()
def event(client):
    return client.post('/api/eventos',json={"nombre":"Jornada","fecha":"2026-07-22","hora_inicio":"09:00","sede":"Centro"}).get_json()["data"]
