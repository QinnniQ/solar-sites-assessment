# Solar Sites — working project brief

**Client:** Praeter · Full-stack developer assessment

**Submission deadline:** Monday, 19 October 2026 (time not specified; aim to submit before the day begins)

**Source of truth:** `Solar-sites-assessment.pdf`, attached to Praeter's 13 October 2026 email. The PDF's appendix governs route names and JSON field names.

## 1. Outcome

Build a small, credible advisor application that lets each advisor manage their own client sites, estimate solar production from the European Commission's PVGIS data, and compare household solar self-use with and without a home battery. The result must be correct, safe, easy to run, and easy to explain in an interview. Visual polish should make the workflow clear and trustworthy without expanding the assessment scope.

## 2. Non-negotiable requirements

- Python backend; TypeScript and React frontend.
- Account registration, login, logout, and an authenticated current-user endpoint.
- Advisors can create, list, inspect, update, and delete only their own sites. A site contains `id`, `clientName`, `address`, `latitude`, `longitude`, optional `roofAreaM2`, and `peakKwp`.
- Show yearly production in kWh and exactly 12 monthly kWh values for a site. Show a clear no-data result when PVGIS cannot cover a location.
- Accept battery capacity in kWh and annual household use in kWh; compare annual self-used solar energy with and without a battery. State the consumption profile and battery assumptions in the README and UI.
- All PVGIS calls go through the Python backend. Use the public, keyless PVGIS API.
- Preserve the appendix routes and camelCase JSON field names exactly. Use defensible HTTP status codes and field-level validation errors for invalid site creation.
- Supply a root `Dockerfile`. `docker build -t solar .` and `docker run -p 8000:8000 solar` must serve the **whole application** at `http://localhost:8000` with no other services, accounts, secrets, or paid hosting required.
- Supply a README with exact run steps, stack choices, modelling assumptions, limitations, and test instructions. Deliver one accessible GitHub repository link. Reviewers create their own accounts.

## 3. Product flow

1. **Entry:** register or sign in, with clear errors and no demo credentials.
2. **Sites:** see the advisor's sites, add a site, edit details, delete with confirmation, and open a site.
3. **Site analysis:** see the site's input data, annual solar estimate, a 12-month chart, source/assumption notes, and useful loading and failure states.
4. **Battery comparison:** enter `capacityKwh` and `annualUseKwh`; see self-used, exported, and grid-supplied energy for both cases plus the battery's incremental self-use. Explain that these are estimates, not an investment or bill-saving guarantee.

Design direction: refined, restrained, responsive interface with readable data hierarchy, accessible forms, keyboard support, sensible number and unit formatting, and honest uncertainty language. Prioritize analytical clarity over animation or extra pages.

## 4. Fixed API contract

| Route | Input | Required behavior |
| --- | --- | --- |
| `POST /api/register` | `{email, password}` | Create account, start session, reject existing email. |
| `POST /api/login` | `{email, password}` | Start session, reject wrong credentials. |
| `POST /api/logout` | — | End session. |
| `GET /api/me` | — | Return `{email}`; fail without session. |
| `GET /api/sites` | — | Return `[site]` for caller only. |
| `POST /api/sites` | `{clientName, address, latitude, longitude, roofAreaM2?, peakKwp}` | Return created site; invalid input gets a message for each affected field. |
| `GET /api/sites/{id}` | — | Return caller-owned site; no access to others' sites. |
| `PUT /api/sites/{id}` | Same site input as POST | Return updated site. |
| `DELETE /api/sites/{id}` | — | Delete caller-owned site; return no body. |
| `GET /api/sites/{id}/production` | — | Return `{yearlyKwh, monthlyKwh: [{month, kwh}]}` with 12 months. |
| `GET /api/sites/{id}/battery` | `?capacityKwh=&annualUseKwh=` | Return `{productionKwh, consumptionKwh, withoutBattery: {selfUsedKwh, …}, withBattery: {selfUsedKwh, …}}`. |

The PDF allows a cookie or token session. If a token is returned, its JSON field must be `token`. If a cookie and CSRF token are used, return `csrfToken` and expect it in the `X-CSRF-Token` header. Extra battery result fields may be defined internally, but the named fields above must remain stable.

## 5. Recommended implementation decisions

- **Backend:** FastAPI for explicit request/response validation and a compact, inspectable API. Keep PVGIS access, calculation, persistence, and routes in separate modules.
- **Frontend:** React + TypeScript + Vite; build static assets into the Python-serving Docker image so a single port serves API and UI.
- **Persistence:** SQLite with schema migrations and a persistent data path configurable by environment variable. No external database is required for review. Explain that container data needs a mounted volume for persistence across container replacement.
- **Authentication:** server-side sessions in an HttpOnly cookie, with a CSRF token for state-changing requests; password hashes using a current password-hashing library. Authorize every site lookup by the session's user ID. Avoid disclosing whether an unowned site exists.
- **PVGIS:** pin the versioned `v5_3` endpoints; call `PVcalc` for monthly/annual output and `seriescalc` for hourly output used by the battery simulation. Use backend-only requests with bounded timeouts, response validation, restrained caching, and clear upstream error mapping. Never pass arbitrary client-supplied PVGIS URLs.
- **Model:** derive an hourly household demand profile that sums exactly to `annualUseKwh` (a simple, documented fixed daily shape is acceptable). For each hour, use PV production to meet current load first, then charge the battery from surplus, then export any remainder; discharge the battery to meet later load, then import any shortfall. Start and end with a documented state-of-charge convention, disallow grid charging, and state any charge/discharge efficiency assumption. Run the no-battery case on the same hourly data. Keep energy accounting explicit and test conservation and monotonicity.
- **Consistency:** align the hourly PV series used for battery analysis with the displayed 12-month PVGIS production totals, for example by scaling each month's hourly shape to its `PVcalc` monthly kWh. Document the normalization and handle zero-output months safely. This lets the battery comparison and production card agree on annual production.
- **Roof area:** store and show `roofAreaM2`; do not silently derive panel capacity from it because `peakKwp` is explicitly provided. Explain that roof fit is outside the assessment's calculations.

These are implementation recommendations, not additional requirements from Praeter. Keep them only if they remain explainable and feasible within the deadline.

## 6. Quality bar and acceptance checks

**Functional:** all required routes work with exact names and shapes; site CRUD persists; production contains January through December in order; battery capacity zero reproduces the no-battery result; battery self-use never exceeds either production or consumption.

**Security:** passwords are hashed; protected routes reject unauthenticated requests; cross-user list/read/update/delete/analysis cannot disclose or alter another advisor's site; input bounds and non-finite numbers are rejected; session/CSRF handling is tested; no secrets or test credentials are committed.

**Reliability:** distinguish bad input, unavailable PVGIS data, PVGIS overload/rate limit, and network failure. PVGIS errors do not break site CRUD. Avoid excessive repeat calls and respect PVGIS service limits.

**Usability:** forms have inline, field-specific errors; the UI handles empty, loading, retryable error, and success states; charts have text equivalents; mobile layout remains usable.

**Delivery:** clean build from a fresh checkout using the two prescribed Docker commands; browser smoke test on `localhost:8000`; backend calculation/auth tests and a small end-to-end user journey; README and public/private GitHub access verified before sending the link.

## 7. Execution order

1. Lock the API shapes, modelling assumptions, and project skeleton.
2. Build authentication, persistence, and ownership-safe site CRUD.
3. Integrate PVGIS production and its failure states.
4. Implement and test the hourly battery comparison.
5. Build and polish the React advisor workflow.
6. Validate Docker from a clean build, run tests, review security and accessibility, write README, and verify repository access.

Stop adding features once the fixed contract and user journey are solid. Any remaining time should improve correctness, documentation, and interview readiness.

## 8. Open choices to settle before implementation

- Exact household load profile and battery efficiency/state-of-charge convention.
- Whether PVGIS assumptions use the PDF example's `loss=14` and `optimalangles=1`; if chosen, label them as defaults rather than facts about a client's roof.
- Whether annual production is presented as a PVGIS climate estimate while the battery simulation uses a specific hourly weather year; if so, document the normalizing method and source year.
- Submission time on 19 October is unspecified. Plan for an earlier handoff rather than relying on end of day.

## 9. Out of scope

Payments, commercial quotations, tariff savings, geocoding, roof geometry validation, multi-advisor sharing, external authentication providers, maps, and paid hosting. Add none of these unless the required application is already complete and stable.
