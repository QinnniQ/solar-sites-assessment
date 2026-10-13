"""Exercise the same image and port that Praeter will use."""

import uuid

import httpx


def main() -> None:
    with httpx.Client(base_url="http://localhost:8000", timeout=90.0) as client:
        home = client.get("/")
        assert home.status_code == 200 and "Solar Sites" in home.text
        icon = client.get("/favicon.svg")
        assert icon.status_code == 200 and "<svg" in icon.text
        print("Frontend: OK")

        email = "smoke-" + uuid.uuid4().hex[:10] + "@example.com"
        registered = client.post(
            "/api/register", json={"email": email, "password": "smoke-password-2026"}
        )
        registered.raise_for_status()
        csrf = registered.json()["csrfToken"]
        headers = {"X-CSRF-Token": csrf}
        assert client.get("/api/me").json() == {"email": email}
        print("Account and session: OK")

        site = client.post(
            "/api/sites",
            headers=headers,
            json={
                "clientName": "Smoke test",
                "address": "Delft, Netherlands",
                "latitude": 52.08,
                "longitude": 4.31,
                "roofAreaM2": 45,
                "peakKwp": 5,
            },
        )
        site.raise_for_status()
        site_id = site.json()["id"]
        print("Site creation: OK")

        production = client.get(f"/api/sites/{site_id}/production")
        production.raise_for_status()
        annual = production.json()
        assert len(annual["monthlyKwh"]) == 12 and annual["yearlyKwh"] > 0
        print("Live PVGIS annual production:", annual["yearlyKwh"], "kWh")

        battery = client.get(
            f"/api/sites/{site_id}/battery",
            params={"capacityKwh": 10, "annualUseKwh": 3500},
        )
        battery.raise_for_status()
        result = battery.json()
        assert abs(result["productionKwh"] - annual["yearlyKwh"]) < 0.1
        assert result["withBattery"]["selfUsedKwh"] >= result["withoutBattery"]["selfUsedKwh"]
        print("Live PVGIS battery gain:", result["batteryGainKwh"], "kWh")

        deleted = client.delete(f"/api/sites/{site_id}", headers=headers)
        assert deleted.status_code == 204
        print("Site deletion: OK")


if __name__ == "__main__":
    main()
