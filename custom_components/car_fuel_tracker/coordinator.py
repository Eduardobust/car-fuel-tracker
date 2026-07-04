"""Data coordinator for a single car in Car and Fuel Tracker.

Beta v0: local Store-based persistence + push-based updates to entities.
No polling — state changes only when log_fillup / log_service / retire_car
services run.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    AVG_WINDOW_10_FILLS,
    AVG_WINDOW_180_DAYS,
    AVG_WINDOW_LIFETIME,
    CAR_STATUS_ACTIVE,
    CAR_STATUS_RETIRED,
    CONF_BRAND,
    CONF_COLOR,
    CONF_COMMENT,
    CONF_GOOGLE_SHEET_ID,
    CONF_GOOGLE_SHEETS_ENTRY_ID,
    CONF_MODEL,
    CONF_PURCHASE_COST,
    CONF_STARTING_ODOMETER,
    CONF_YEAR,
    DOMAIN,
    STORAGE_KEY_FMT,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class FuelTrackerCoordinator(DataUpdateCoordinator):
    """Holds fills/services history and profile/status for one car."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_{entry.entry_id}")
        self.hass = hass
        self.entry = entry
        self.car_name: str = entry.data["car_name"]
        self._store = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_FMT.format(entry_id=entry.entry_id)
        )
        self._fills: list[dict[str, Any]] = []
        self._services: list[dict[str, Any]] = []
        self._tire_last_checked: str | None = None

        # Retirement state (persisted; car profile itself comes from entry.data)
        self._status: str = CAR_STATUS_ACTIVE
        self._retired_date: str | None = None
        self._retirement_reason: str | None = None
        self._final_odometer: float | None = None

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self._fills = stored.get("fills", [])
            self._services = stored.get("services", [])
            self._tire_last_checked = stored.get("tire_last_checked")
            self._status = stored.get("status", CAR_STATUS_ACTIVE)
            self._retired_date = stored.get("retired_date")
            self._retirement_reason = stored.get("retirement_reason")
            self._final_odometer = stored.get("final_odometer")
        self.async_set_updated_data(self._build_data())

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "fills": self._fills,
                "services": self._services,
                "tire_last_checked": self._tire_last_checked,
                "status": self._status,
                "retired_date": self._retired_date,
                "retirement_reason": self._retirement_reason,
                "final_odometer": self._final_odometer,
            }
        )

    # ------------------------------------------------------------------ #
    # Guard
    # ------------------------------------------------------------------ #
    def _ensure_active(self) -> None:
        if self._status == CAR_STATUS_RETIRED:
            raise HomeAssistantError(
                f"Car Fuel Tracker: '{self.car_name}' is retired as of "
                f"{self._retired_date}. Its data is frozen — no new fillups, "
                f"services, or further retirement actions are allowed."
            )

    # ------------------------------------------------------------------ #
    # Public API used by services.py handlers
    # ------------------------------------------------------------------ #
    async def async_log_fillup(self, payload: dict[str, Any]) -> None:
        self._ensure_active()

        odometer = float(payload["odometer"])
        volume = float(payload["volume"])
        cost_per_liter = float(payload["cost_per_liter"])
        total_cost = round(volume * cost_per_liter, 2)

        prev_odometer = self._fills[-1]["odometer"] if self._fills else None
        delta_km = round(odometer - prev_odometer, 1) if prev_odometer is not None else None

        fill = {
            "date": dt_util.now().isoformat(),
            "odometer": odometer,
            "delta_km": delta_km,
            "volume": volume,
            "fuel_grade": payload.get("fuel_grade"),
            "cost_per_liter": cost_per_liter,
            "total_cost": total_cost,
            "full_tank": bool(payload.get("full_tank", False)),
            "tire_pressure_checked": bool(payload.get("tire_pressure_checked", False)),
            "station_name": payload.get("station_name"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
        }

        if delta_km and delta_km > 0:
            fill["cost_per_km"] = round(total_cost / delta_km, 4)
        else:
            fill["cost_per_km"] = None

        fill["l_per_100km"] = self._calc_consumption_if_full_tank(fill)

        self._fills.append(fill)

        if fill["tire_pressure_checked"]:
            self._tire_last_checked = fill["date"]

        await self._async_save()
        self.async_set_updated_data(self._build_data())
        await self._async_push_to_sheets("fuel", fill)

    async def async_log_service(self, payload: dict[str, Any]) -> None:
        self._ensure_active()

        record = {
            "date": dt_util.now().isoformat(),
            "service_type": payload.get("service_type"),
            "cost": float(payload["cost"]) if payload.get("cost") is not None else None,
            "odometer": float(payload["odometer"]) if payload.get("odometer") is not None else None,
            "notes": payload.get("notes", ""),
        }
        self._services.append(record)
        await self._async_save()
        self.async_set_updated_data(self._build_data())
        await self._async_push_to_sheets("service", record)

    async def async_retire_car(self, payload: dict[str, Any]) -> None:
        """Freeze the car: no further fillup/service logging after this."""
        self._ensure_active()

        self._status = CAR_STATUS_RETIRED
        self._retired_date = dt_util.now().isoformat()
        self._retirement_reason = payload.get("retirement_reason", "")
        final_odo = payload.get("final_odometer")
        self._final_odometer = (
            float(final_odo)
            if final_odo is not None
            else (self._fills[-1]["odometer"] if self._fills else None)
        )

        await self._async_save()
        self.async_set_updated_data(self._build_data())
        await self._async_push_to_sheets(
            "retirement",
            {
                "date": self._retired_date,
                "reason": self._retirement_reason,
                "final_odometer": self._final_odometer,
            },
        )

    # ------------------------------------------------------------------ #
    # Calculations
    # ------------------------------------------------------------------ #
    def _calc_consumption_if_full_tank(self, current_fill: dict[str, Any]) -> float | None:
        if not current_fill["full_tank"]:
            return None

        prev_full_index = None
        for i in range(len(self._fills) - 1, -1, -1):
            if self._fills[i]["full_tank"]:
                prev_full_index = i
                break

        if prev_full_index is None:
            return None

        segment = self._fills[prev_full_index + 1:]
        volume_sum = sum(f["volume"] for f in segment) + current_fill["volume"]
        km_delta = current_fill["odometer"] - self._fills[prev_full_index]["odometer"]

        if km_delta <= 0:
            return None

        return round((volume_sum / km_delta) * 100, 2)

    def _rolling_avg_cost_per_km(self, window: str) -> float | None:
        eligible = [f for f in self._fills if f.get("cost_per_km") is not None]
        if not eligible:
            return None

        if window == AVG_WINDOW_10_FILLS:
            subset = eligible[-10:]
        elif window == AVG_WINDOW_180_DAYS:
            cutoff = dt_util.now() - timedelta(days=180)
            subset = [
                f for f in eligible if datetime.fromisoformat(f["date"]) >= cutoff
            ]
        else:  # lifetime
            subset = eligible

        if not subset:
            return None
        return round(sum(f["cost_per_km"] for f in subset) / len(subset), 4)

    def _days_since_tire_check(self) -> int | None:
        if not self._tire_last_checked:
            return None
        last = datetime.fromisoformat(self._tire_last_checked)
        return (dt_util.now() - last).days

    # ------------------------------------------------------------------ #
    # Sheets sync (best-effort — never blocks local sensors on failure)
    # ------------------------------------------------------------------ #
    async def _async_push_to_sheets(self, sheet_tab: str, record: dict[str, Any]) -> None:
        sheets_entry_id = self.entry.data.get(CONF_GOOGLE_SHEETS_ENTRY_ID) or self.entry.options.get(
            CONF_GOOGLE_SHEETS_ENTRY_ID
        )
        sheet_id = self.entry.data.get(CONF_GOOGLE_SHEET_ID) or self.entry.options.get(
            CONF_GOOGLE_SHEET_ID
        )
        if not sheets_entry_id:
            return

        try:
            await self.hass.services.async_call(
                "google_sheets",
                "append_sheet",
                {
                    "config_entry": sheets_entry_id,
                    "worksheet": sheet_tab,
                    "sheet_id": sheet_id,
                    "car": self.car_name,
                    **record,
                },
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Car Fuel Tracker: could not push %s record to Google Sheets for %s: %s",
                sheet_tab,
                self.car_name,
                err,
            )

    # ------------------------------------------------------------------ #
    # Snapshot consumed by sensor.py
    # ------------------------------------------------------------------ #
    def _car_profile(self) -> dict[str, Any]:
        data = self.entry.data
        return {
            "brand": data.get(CONF_BRAND, ""),
            "model": data.get(CONF_MODEL, ""),
            "year": data.get(CONF_YEAR),
            "color": data.get(CONF_COLOR, ""),
            "purchase_cost": data.get(CONF_PURCHASE_COST),
            "starting_odometer": data.get(CONF_STARTING_ODOMETER),
            "comment": self.entry.options.get(CONF_COMMENT, data.get(CONF_COMMENT, "")),
        }

    def _build_data(self) -> dict[str, Any]:
        last_fill = self._fills[-1] if self._fills else None
        last_service = self._services[-1] if self._services else None
        return {
            "car_profile": self._car_profile(),
            "status": self._status,
            "retired_date": self._retired_date,
            "retirement_reason": self._retirement_reason,
            "final_odometer": self._final_odometer,
            "last_fillup": last_fill,
            "odometer": last_fill["odometer"] if last_fill else None,
            "l_per_100km": last_fill["l_per_100km"] if last_fill else None,
            "cost_per_km_last_fill": last_fill["cost_per_km"] if last_fill else None,
            "cost_per_km_avg_10_fills": self._rolling_avg_cost_per_km(AVG_WINDOW_10_FILLS),
            "cost_per_km_avg_180_days": self._rolling_avg_cost_per_km(AVG_WINDOW_180_DAYS),
            "cost_per_km_avg_lifetime": self._rolling_avg_cost_per_km(AVG_WINDOW_LIFETIME),
            "days_since_tire_check": self._days_since_tire_check(),
            "tire_last_checked": self._tire_last_checked,
            "last_service": last_service,
            "fill_count": len(self._fills),
            "service_count": len(self._services),
        }
