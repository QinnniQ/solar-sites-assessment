"""Versioned, backend-only PVGIS integration with bounded cache and clear failures."""

import asyncio
import json
import math
import time

import httpx

from .db import database

BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3"
CACHE_SECONDS = 30 * 24 * 60 * 60
SYSTEM_LOSS_PERCENT = 14
HOURLY_YEAR = 2023


class PVGISError(Exception):
    def __init__(self, code: str, message: str, status: int):
        self.code = code
        self.message = message
        self.status = status


def _positive_number(value) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("Invalid PVGIS energy value")
    return number


async def _request(tool: str, params: dict) -> dict:
    cache_key = json.dumps([tool, params], sort_keys=True, separators=(",", ":"))
    with database() as connection:
        cached = connection.execute(
            "SELECT payload, fetched_at FROM pvgis_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
    if cached and cached["fetched_at"] > time.time() - CACHE_SECONDS:
        return json.loads(cached["payload"])

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=5.0)) as client:
            for attempt in range(2):
                response = await client.get(f"{BASE_URL}/{tool}", params=params)
                if response.status_code in (429, 529) and attempt == 0:
                    await asyncio.sleep(0.7)
                    continue
                break
    except httpx.RequestError as exc:
        raise PVGISError(
            "PVGIS_UNAVAILABLE", "PVGIS could not be reached. Please retry shortly.", 503
        ) from exc

    if response.status_code in (400, 404):
        raise PVGISError(
            "PVGIS_NO_DATA",
            "PVGIS has no usable solar data for this location and configuration.",
            422,
        )
    if response.status_code in (429, 529) or response.status_code >= 500:
        raise PVGISError(
            "PVGIS_UNAVAILABLE", "PVGIS is temporarily unavailable. Please retry shortly.", 503
        )
    if response.status_code != 200:
        raise PVGISError("PVGIS_ERROR", "PVGIS could not calculate this estimate.", 502)
    try:
        payload = response.json()
        if not isinstance(payload, dict) or "outputs" not in payload:
            raise ValueError("Missing outputs")
    except (ValueError, TypeError) as exc:
        raise PVGISError(
            "PVGIS_BAD_RESPONSE", "PVGIS returned an unreadable result.", 502
        ) from exc

    with database() as connection:
        connection.execute(
            "DELETE FROM pvgis_cache WHERE fetched_at <= ?",
            (int(time.time()) - CACHE_SECONDS,),
        )
        connection.execute(
            "INSERT OR REPLACE INTO pvgis_cache (cache_key, payload, fetched_at) VALUES (?, ?, ?)",
            (cache_key, json.dumps(payload), int(time.time())),
        )
    return payload


def _common_params(site: dict) -> dict:
    return {
        "lat": site["latitude"],
        "lon": site["longitude"],
        "peakpower": site["peakKwp"],
        "loss": SYSTEM_LOSS_PERCENT,
        "optimalangles": 1,
        "outputformat": "json",
    }


async def production(site: dict) -> dict:
    payload = await _request("PVcalc", _common_params(site))
    try:
        rows = payload["outputs"]["monthly"]["fixed"]
        monthly = {}
        for row in rows:
            month = int(row["month"])
            if month in monthly or month < 1 or month > 12:
                raise ValueError("Duplicate or invalid month")
            monthly[month] = _positive_number(row["E_m"])
        if set(monthly) != set(range(1, 13)):
            raise ValueError("Incomplete months")
    except (KeyError, TypeError, ValueError) as exc:
        raise PVGISError(
            "PVGIS_BAD_RESPONSE", "PVGIS returned incomplete monthly production data.", 502
        ) from exc
    values = [{"month": month, "kwh": round(monthly[month], 2)} for month in range(1, 13)]
    return {"yearlyKwh": round(sum(row["kwh"] for row in values), 2), "monthlyKwh": values}


async def hourly_production(site: dict) -> list[tuple[int, float]]:
    params = {
        **_common_params(site),
        "pvcalculation": 1,
        "startyear": HOURLY_YEAR,
        "endyear": HOURLY_YEAR,
    }
    payload = await _request("seriescalc", params)
    try:
        rows = payload["outputs"]["hourly"]
        result = []
        months = set()
        for row in rows:
            timestamp = row["time"]
            month = int(timestamp[4:6])
            if month < 1 or month > 12:
                raise ValueError("Invalid month")
            result.append((month, _positive_number(row["P"]) / 1000))
            months.add(month)
        if len(result) < 8000 or months != set(range(1, 13)):
            raise ValueError("Incomplete hourly year")
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise PVGISError(
            "PVGIS_BAD_RESPONSE", "PVGIS returned incomplete hourly production data.", 502
        ) from exc


def aligned_hourly(
    hourly: list[tuple[int, float]], monthly: list[dict]
) -> list[float]:
    """Match PVcalc monthly totals while retaining the hourly series' solar shape."""
    totals = {month: 0.0 for month in range(1, 13)}
    for month, kwh in hourly:
        totals[month] += kwh
    targets = {row["month"]: row["kwh"] for row in monthly}
    for month in range(1, 13):
        if totals[month] == 0 and targets[month] > 0:
            raise PVGISError(
                "PVGIS_BAD_RESPONSE", "PVGIS hourly and monthly estimates cannot be aligned.", 502
            )
    return [
        kwh * targets[month] / totals[month] if totals[month] else 0.0
        for month, kwh in hourly
    ]
