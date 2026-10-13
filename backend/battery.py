"""Transparent hourly energy balance for an illustrative household."""

CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95


def compare(hourly_kwh: list[float], capacity_kwh: float, annual_use_kwh: float) -> dict:
    if not hourly_kwh:
        raise ValueError("Hourly production cannot be empty")
    load = annual_use_kwh / len(hourly_kwh)
    direct = sum(min(pv, load) for pv in hourly_kwh)
    production = sum(hourly_kwh)
    without = _result(direct, production, annual_use_kwh)

    state_of_charge = 0.0
    battery_supplied = 0.0
    exported = 0.0
    for pv in hourly_kwh:
        surplus = max(0.0, pv - load)
        deficit = max(0.0, load - pv)
        stored = min(capacity_kwh - state_of_charge, surplus * CHARGE_EFFICIENCY)
        state_of_charge += stored
        exported += surplus - stored / CHARGE_EFFICIENCY
        supplied = min(deficit, state_of_charge * DISCHARGE_EFFICIENCY)
        state_of_charge -= supplied / DISCHARGE_EFFICIENCY
        battery_supplied += supplied

    used = direct + battery_supplied
    with_battery = _result(used, production, annual_use_kwh)
    with_battery["exportedKwh"] = round(exported, 2)
    with_battery["endingChargeKwh"] = round(state_of_charge, 2)
    return {
        "productionKwh": round(production, 2),
        "consumptionKwh": round(annual_use_kwh, 2),
        "withoutBattery": without,
        "withBattery": with_battery,
        "batteryGainKwh": round(battery_supplied, 2),
    }


def _result(self_used: float, production: float, consumption: float) -> dict:
    return {
        "selfUsedKwh": round(self_used, 2),
        "exportedKwh": round(production - self_used, 2),
        "gridImportedKwh": round(consumption - self_used, 2),
        "selfConsumptionPercent": round(
            100 * self_used / production if production else 0, 1
        ),
        "selfSufficiencyPercent": round(
            100 * self_used / consumption if consumption else 0, 1
        ),
    }
