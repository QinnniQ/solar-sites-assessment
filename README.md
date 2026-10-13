# Solar Sites

An advisor workspace for managing client solar sites and comparing household solar self-use with and without a home battery. Built for Praeter's full-stack assessment.

## Start the complete application

Docker is the only prerequisite. From the repository root:

~~~sh
docker build -t solar .
docker run -p 8000:8000 solar
~~~

Open [http://localhost:8000](http://localhost:8000), create your own account, and add a site. No API key, seed account, external database, or second process is needed. The app calls the public PVGIS service when an estimate is requested, so those estimates need an internet connection.

For data that survives replacement of the container, run it with a named volume:

~~~sh
docker run -p 8000:8000 -v solar-data:/data solar
~~~

The exact two commands in the assessment work without a volume; SQLite data in that case lasts for the life of the container only.

## Stack and structure

- **FastAPI / Python:** explicit request validation and small, readable route handlers. The API is in `backend/app.py`; PVGIS access and energy calculations are separate modules.
- **SQLite:** an embedded, transactional database that lets reviewers run one container without provisioning a service. Every site read and mutation filters by the authenticated user ID.
- **React / TypeScript / Vite:** a typed, responsive advisor interface. Docker builds its static assets and the Python process serves both the UI and `/api` on port 8000.
- **Argon2id password hashing; opaque server-side sessions:** passwords are never stored or logged in plaintext. The session cookie is HttpOnly and SameSite=Strict; state-changing authenticated requests require a CSRF token in the `X-CSRF-Token` header. Registration and login return that token as `csrfToken`. The accompanying readable CSRF cookie lets the interface continue after a page reload. For an HTTPS deployment, set `SOLAR_COOKIE_SECURE=1`.

The database is initialized automatically on startup. The assessment has no migration requirement; a production rollout with evolving schema would add versioned migrations, backups, and operational monitoring.

## Solar and battery methodology

The backend calls [European Commission PVGIS 5.3](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en), never the browser. `PVcalc` supplies 12 monthly production totals. The annual value is their sum. The model uses the site's coordinates and `peakKwp`, a **14% system loss**, and PVGIS **optimal inclination and orientation**. These are fixed, disclosed defaults, not a survey of the actual roof. `roofAreaM2` is optional reference information; we do not infer installable capacity or panel fit from it.

For battery analysis, `seriescalc` supplies an hourly PV shape for **2023**. Each month's hourly values are scaled to that month's `PVcalc` energy total. This makes the comparison use the same annual production shown in the production view. A 30-day server-side cache keyed by PVGIS tool and inputs avoids repeat requests. PVGIS calls have timeouts and one restrained retry for overload/rate limiting; a location with no usable data receives a distinct error.

PVGIS does not provide household electricity demand. We spread the advisor's `annualUseKwh` **uniformly over the returned hours**. This is an intentionally simple, reproducible household assumption; real use varies by hour, season, and household. The battery starts empty, charges only from surplus solar, and discharges only to meet later household demand. It cannot charge from the grid. Charge and discharge are each 95% efficient, yielding 90.25% round-trip efficiency. `capacityKwh` is usable stored energy. Any energy still stored at the end of the year is **not** counted as self-used. The no-battery case uses the identical solar and demand series.

The comparison is an energy estimate, not a financial quote. It excludes tariff structures, export compensation, degradation, power limits, installation costs, and measured roof orientation. It should not be presented as guaranteed yield or bill savings.

## API contract

All JSON site fields are camelCase: `clientName`, `address`, `latitude`, `longitude`, optional `roofAreaM2`, and `peakKwp`, plus `id` in responses.

| Route | Result |
| --- | --- |
| `POST /api/register` | Creates account and session; returns `{email, csrfToken}` (201, or 409 if email exists). |
| `POST /api/login` | Starts session; returns `{email, csrfToken}` (401 for wrong credentials). |
| `POST /api/logout` | Ends session (204). |
| `GET /api/me` | Returns `{email}`; requires session. |
| `GET /api/sites` | Lists only the signed-in advisor's sites. |
| `POST /api/sites` | Creates a site (201); invalid fields return a per-field `errors` object (422). |
| `GET /api/sites/{id}` | Returns an owned site; unknown and unowned IDs both return 404. |
| `PUT /api/sites/{id}` | Replaces and returns an owned site. |
| `DELETE /api/sites/{id}` | Deletes an owned site (204). |
| `GET /api/sites/{id}/production` | Returns `{yearlyKwh, monthlyKwh: [{month, kwh}]}` with months 1–12. |
| `GET /api/sites/{id}/battery?capacityKwh=&annualUseKwh=` | Returns `productionKwh`, `consumptionKwh`, `withoutBattery`, `withBattery`, and `batteryGainKwh`. Each case includes `selfUsedKwh`, `exportedKwh`, `gridImportedKwh`, `selfConsumptionPercent`, and `selfSufficiencyPercent`. |

All site and analysis routes require a session. Authenticated POST/PUT/DELETE routes also require the `X-CSRF-Token` header. Unowned resources are returned as 404 to avoid exposing whether another advisor's site exists. Invalid input returns 422; unavailable PVGIS returns 503; malformed upstream data returns 502. PVGIS no-data errors return 422 with a clear `PVGIS_NO_DATA` code.

## Development and verification

Use Python 3.12+ and Node 22+. In separate terminals:

~~~sh
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/uvicorn backend.app:app --reload --port 8000
~~~

~~~sh
cd frontend
npm ci
npm run dev
~~~

The Vite development server proxies `/api` to port 8000. Open the URL it prints. On macOS/Linux, use `.venv/bin/pip` and `.venv/bin/uvicorn`.

Run checks:

~~~sh
.venv/Scripts/pytest -q
cd frontend && npm run build
~~~

The tests cover cross-advisor isolation, session/CSRF behavior, validation, the required API shapes, monthly alignment, and battery energy invariants. A final clean Docker build and browser journey verify the submission path.

## Submission

Provide one GitHub repository URL with this root `Dockerfile` and README. Make it public or grant Praeter access before sending the link. Do not share any account credentials; reviewers can register their own. Hosting is optional and should not be paid for for this assessment.
