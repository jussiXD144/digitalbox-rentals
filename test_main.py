import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .main import app
from .database import Base, get_db
from .models import User

# Setup test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_digitalbox.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert b"DigitalBox" in response.content

def test_register_and_login():
    # Register
    response = client.post(
        "/register",
        data={"email": "test@example.com", "password": "password123"},
        allow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"

    # Login
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "password123"},
        allow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"
    assert "access_token" in response.headers.get("set-cookie")

def test_dashboard_unauthorized():
    response = client.get("/dashboard", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"
