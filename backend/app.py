"""Praeter Solar Sites: one origin for the API and the built React application."""

import hashlib
import hmac
import math
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .battery import compare
from .db import database, initialize
from .pvgis import PVGISError, aligned_hourly, hourly_production, production
from .schemas import LoginInput, RegisterInput, SiteInput, site_from_row

SESSION_AGE_SECONDS = 7 * 24 * 60 * 60
PASSWORD_HASHER = PasswordHasher()
DUMMY_HASH = PASSWORD_HASHER.hash("a-password-that-is-never-valid")
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize()
    yield


app = FastAPI(title="Solar Sites", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    errors = {}
    for issue in exc.errors():
        location = [str(part) for part in issue["loc"] if part not in ("body", "query")]
        field = ".".join(location) if location else "request"
        message = issue["msg"]
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        errors.setdefault(field, message)
    return JSONResponse(status_code=422, content={"errors": errors})


@app.exception_handler(PVGISError)
async def pvgis_error(_request: Request, exc: PVGISError):
    return JSONResponse(
        status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}}
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unauthorized():
    raise HTTPException(status_code=401, detail="Please sign in to continue.")


def current_user(request: Request) -> dict:
    token = request.cookies.get("solar_session")
    if not token:
        _unauthorized()
    with database() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.email, sessions.csrf_hash, sessions.expires_at
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (_sha256(token),),
        ).fetchone()
    if row is None or row["expires_at"] <= time.time():
        _unauthorized()
    return dict(row)


def csrf_user(request: Request, user: dict = Depends(current_user)) -> dict:
    header = request.headers.get("X-CSRF-Token", "")
    cookie = request.cookies.get("solar_csrf", "")
    if (
        not header
        or not cookie
        or not hmac.compare_digest(header, cookie)
        or not hmac.compare_digest(_sha256(header), user["csrf_hash"])
    ):
        raise HTTPException(status_code=403, detail="Invalid CSRF token. Please sign in again.")
    return user


def _start_session(user_id: int, email: str) -> JSONResponse:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    with database() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, csrf_hash, expires_at) VALUES (?, ?, ?, ?)",
            (_sha256(token), user_id, _sha256(csrf), int(time.time()) + SESSION_AGE_SECONDS),
        )
    response = JSONResponse({"email": email, "csrfToken": csrf})
    secure = os.getenv("SOLAR_COOKIE_SECURE", "0") == "1"
    response.set_cookie(
        "solar_session",
        token,
        max_age=SESSION_AGE_SECONDS,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.set_cookie(
        "solar_csrf",
        csrf,
        max_age=SESSION_AGE_SECONDS,
        secure=secure,
        httponly=False,
        samesite="strict",
    )
    return response


@app.post("/api/register", status_code=201)
def register(body: RegisterInput):
    email = str(body.email).lower()
    try:
        with database() as connection:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, PASSWORD_HASHER.hash(body.password), int(time.time())),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    response = _start_session(user_id, email)
    response.status_code = 201
    return response


@app.post("/api/login")
def login(body: LoginInput):
    email = str(body.email).lower()
    with database() as connection:
        user = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
    try:
        PASSWORD_HASHER.verify(user["password_hash"] if user else DUMMY_HASH, body.password)
    except VerificationError:
        raise HTTPException(status_code=401, detail="Incorrect email or password.") from None
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return _start_session(user["id"], user["email"])


@app.post("/api/logout", status_code=204)
def logout(request: Request, user: dict = Depends(csrf_user)):
    with database() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE token_hash = ? AND user_id = ?",
            (_sha256(request.cookies["solar_session"]), user["id"]),
        )
    response = Response(status_code=204)
    response.delete_cookie("solar_session")
    response.delete_cookie("solar_csrf")
    return response


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"email": user["email"]}


def _owned_site(site_id: int, user_id: int) -> dict:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM sites WHERE id = ? AND user_id = ?", (site_id, user_id)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Site not found.")
    return site_from_row(row)


@app.get("/api/sites")
def list_sites(user: dict = Depends(current_user)):
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM sites WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (user["id"],),
        ).fetchall()
    return [site_from_row(row) for row in rows]


@app.post("/api/sites", status_code=201)
def create_site(body: SiteInput, user: dict = Depends(csrf_user)):
    values = body.model_dump()
    now = int(time.time())
    with database() as connection:
        cursor = connection.execute(
            """
            INSERT INTO sites
            (user_id, client_name, address, latitude, longitude, roof_area_m2,
             peak_kwp, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                values["clientName"],
                values["address"],
                values["latitude"],
                values["longitude"],
                values["roofAreaM2"],
                values["peakKwp"],
                now,
                now,
            ),
        )
        site_id = cursor.lastrowid
    return _owned_site(site_id, user["id"])


@app.get("/api/sites/{site_id}")
def get_site(site_id: int, user: dict = Depends(current_user)):
    return _owned_site(site_id, user["id"])


@app.put("/api/sites/{site_id}")
def update_site(site_id: int, body: SiteInput, user: dict = Depends(csrf_user)):
    values = body.model_dump()
    with database() as connection:
        cursor = connection.execute(
            """
            UPDATE sites SET client_name = ?, address = ?, latitude = ?, longitude = ?,
                roof_area_m2 = ?, peak_kwp = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                values["clientName"],
                values["address"],
                values["latitude"],
                values["longitude"],
                values["roofAreaM2"],
                values["peakKwp"],
                int(time.time()),
                site_id,
                user["id"],
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Site not found.")
    return _owned_site(site_id, user["id"])


@app.delete("/api/sites/{site_id}", status_code=204)
def delete_site(site_id: int, user: dict = Depends(csrf_user)):
    with database() as connection:
        cursor = connection.execute(
            "DELETE FROM sites WHERE id = ? AND user_id = ?", (site_id, user["id"])
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Site not found.")
    return Response(status_code=204)


@app.get("/api/sites/{site_id}/production")
async def site_production(site_id: int, user: dict = Depends(current_user)):
    site = _owned_site(site_id, user["id"])
    return await production(site)


@app.get("/api/sites/{site_id}/battery")
async def site_battery(
    site_id: int,
    capacityKwh: float = Query(ge=0, le=1000),
    annualUseKwh: float = Query(gt=0, le=1_000_000),
    user: dict = Depends(current_user),
):
    if not math.isfinite(capacityKwh) or not math.isfinite(annualUseKwh):
        raise HTTPException(status_code=422, detail="Battery inputs must be finite numbers.")
    site = _owned_site(site_id, user["id"])
    import asyncio

    annual, hourly = await asyncio.gather(production(site), hourly_production(site))
    aligned = aligned_hourly(hourly, annual["monthlyKwh"])
    return compare(aligned, capacityKwh, annualUseKwh)


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    icon = FRONTEND_DIST / "favicon.svg"
    if not icon.exists():
        raise HTTPException(status_code=404, detail="Icon not found.")
    return FileResponse(icon, media_type="image/svg+xml")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Endpoint not found.")
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend has not been built.")
    return FileResponse(index)
