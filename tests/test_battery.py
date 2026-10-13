import pytest

from backend.battery import compare
from backend.pvgis import aligned_hourly


def test_zero_capacity_matches_no_battery():
    result = compare([0, 4, 0, 0], 0, 4)
    assert result["withoutBattery"]["selfUsedKwh"] == result["withBattery"]["selfUsedKwh"]
    assert result["batteryGainKwh"] == 0


def test_battery_shifts_solar_without_creating_energy():
    profile = [0, 5, 0, 0]
    no_battery = compare(profile, 0, 4)
    with_battery = compare(profile, 2, 4)
    assert with_battery["withBattery"]["selfUsedKwh"] > no_battery["withoutBattery"]["selfUsedKwh"]
    assert with_battery["withBattery"]["selfUsedKwh"] <= 4
    assert with_battery["withBattery"]["selfUsedKwh"] <= 5
    assert with_battery["withBattery"]["gridImportedKwh"] < no_battery["withoutBattery"]["gridImportedKwh"]
    assert with_battery["withBattery"]["exportedKwh"] < no_battery["withoutBattery"]["exportedKwh"]
    assert with_battery["batteryGainKwh"] == pytest.approx(1.9, abs=0.01)


def test_monthly_alignment_preserves_shape_and_totals():
    hourly = [(month, 1.0) for month in range(1, 13)]
    hourly += [(1, 3.0)]
    monthly = [{"month": month, "kwh": 10.0} for month in range(1, 13)]
    values = aligned_hourly(hourly, monthly)
    assert sum(values) == pytest.approx(120)
    assert values[0] == pytest.approx(2.5)
    assert values[-1] == pytest.approx(7.5)
