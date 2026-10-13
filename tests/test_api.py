from fastapi.testclient import TestClient

from backend.app import app
from backend.db import database


SITE = {
    "clientName": "Van Dijk",
    "address": "Kerkstraat 1, Delft",
    "latitude": 52.08,
    "longitude": 4.31,
    "roofAreaM2": 45,
    "peakKwp": 5,
}


def register(client, email):
    result = client.post("/api/register", json={"email": email, "password": "correct-horse-2026"})
    assert result.status_code == 201
    assert result.json()["email"] == email
    assert result.json()["csrfToken"]
    return result.json()["csrfToken"]


def test_auth_csrf_validation_and_site_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("SOLAR_DB_PATH", str(tmp_path / "solar.db"))
    with TestClient(app) as first, TestClient(app) as second:
        assert first.get("/api/me").status_code == 401
        csrf = register(first, "first@example.com")
        assert first.get("/api/me").json() == {"email": "first@example.com"}
        assert first.post("/api/sites", json=SITE).status_code == 403
        headers = {"X-CSRF-Token": csrf}
        invalid = first.post(
            "/api/sites",
            json={**SITE, "clientName": "  ", "latitude": 120, "peakKwp": 0},
            headers=headers,
        )
        assert invalid.status_code == 422
        assert {"clientName", "latitude", "peakKwp"} <= invalid.json()["errors"].keys()
        created = first.post("/api/sites", json=SITE, headers=headers)
        assert created.status_code == 201
        site_id = created.json()["id"]
        assert first.get("/api/sites").json()[0]["id"] == site_id
        with database() as connection:
            stored = connection.execute("SELECT password_hash FROM users WHERE email = ?", ("first@example.com",)).fetchone()
            assert stored["password_hash"] != "correct-horse-2026"
        register(second, "second@example.com")
        assert second.get("/api/sites").json() == []
        assert second.get(f"/api/sites/{site_id}").status_code == 404
        assert second.get(f"/api/sites/{site_id}/production").status_code == 404
        assert second.get(f"/api/sites/{site_id}/battery?capacityKwh=10&annualUseKwh=3500").status_code == 404
        second_csrf = second.cookies["solar_csrf"]
        assert second.put(f"/api/sites/{site_id}", json=SITE, headers={"X-CSRF-Token": second_csrf}).status_code == 404
        assert second.delete(f"/api/sites/{site_id}", headers={"X-CSRF-Token": second_csrf}).status_code == 404
        assert first.get(f"/api/sites/{site_id}").status_code == 200
        assert first.post("/api/logout", headers=headers).status_code == 204
        assert first.get("/api/me").status_code == 401


def test_production_and_battery_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("SOLAR_DB_PATH", str(tmp_path / "solar.db"))

    async def fake_production(_site):
        return {
            "yearlyKwh": 1200,
            "monthlyKwh": [{"month": month, "kwh": 100} for month in range(1, 13)],
        }

    async def fake_hourly(_site):
        return [(month, 50.0) for month in range(1, 13) for _ in range(2)]

    # A complete year is unnecessary for the route contract because the PVGIS parser
    # is exercised before this service boundary.
    import backend.app as app_module

    monkeypatch.setattr(app_module, "production", fake_production)
    monkeypatch.setattr(app_module, "hourly_production", fake_hourly)
    with TestClient(app) as client:
        csrf = register(client, "advisor@example.com")
        created = client.post("/api/sites", json=SITE, headers={"X-CSRF-Token": csrf}).json()
        site_id = created["id"]
        production = client.get(f"/api/sites/{site_id}/production")
        assert production.status_code == 200
        assert production.json()["yearlyKwh"] == 1200
        assert len(production.json()["monthlyKwh"]) == 12
        battery = client.get(f"/api/sites/{site_id}/battery?capacityKwh=10&annualUseKwh=800")
        assert battery.status_code == 200
        assert battery.json()["productionKwh"] == 1200
        assert "selfUsedKwh" in battery.json()["withoutBattery"]
        assert "selfUsedKwh" in battery.json()["withBattery"]
