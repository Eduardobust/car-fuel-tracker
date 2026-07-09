"""The Car and Fuel Tracker integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_CAR,
    ATTR_COST,
    ATTR_COST_PER_LITER,
    ATTR_FINAL_ODOMETER,
    ATTR_FUEL_GRADE,
    ATTR_FULL_TANK,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_NOTES,
    ATTR_ODOMETER,
    ATTR_RETIREMENT_REASON,
    ATTR_SERVICE_TYPE,
    ATTR_STATION_BRAND,
    ATTR_STATION_NAME,
    ATTR_TIRE_PRESSURE_CHECKED,
    ATTR_VOLUME,
    DOMAIN,
    FUEL_GRADES,
    SERVICE_LOG_FILLUP,
    SERVICE_LOG_SERVICE,
    SERVICE_RETIRE_CAR,
    SERVICE_UNRETIRE_CAR,
)
from .coordinator import FuelTrackerCoordinator

PLATFORMS = ["sensor"]

LOG_FILLUP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CAR): cv.string,
        vol.Required(ATTR_ODOMETER): vol.Coerce(float),
        vol.Required(ATTR_VOLUME): vol.Coerce(float),
        vol.Required(ATTR_COST_PER_LITER): vol.Coerce(float),
        vol.Optional(ATTR_FUEL_GRADE, default=FUEL_GRADES[0]): vol.In(FUEL_GRADES),
        vol.Optional(ATTR_FULL_TANK, default=False): cv.boolean,
        vol.Optional(ATTR_TIRE_PRESSURE_CHECKED, default=False): cv.boolean,
        vol.Optional(ATTR_STATION_NAME): cv.string,
        vol.Optional(ATTR_STATION_BRAND): cv.string,
        vol.Optional(ATTR_LATITUDE): vol.Coerce(float),
        vol.Optional(ATTR_LONGITUDE): vol.Coerce(float),
    }
)

LOG_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CAR): cv.string,
        vol.Required(ATTR_SERVICE_TYPE): cv.string,
        vol.Optional(ATTR_COST): vol.Coerce(float),
        vol.Optional(ATTR_ODOMETER): vol.Coerce(float),
        vol.Optional(ATTR_NOTES, default=""): cv.string,
    }
)

RETIRE_CAR_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CAR): cv.string,
        vol.Optional(ATTR_RETIREMENT_REASON, default=""): cv.string,
        vol.Optional(ATTR_FINAL_ODOMETER): vol.Coerce(float),
    }
)

UNRETIRE_CAR_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CAR): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    coordinator = FuelTrackerCoordinator(hass, entry)
    await coordinator.async_load()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_LOG_FILLUP):

        async def _handle_log_fillup(call: ServiceCall) -> None:
            await _dispatch_to_car(hass, call.data[ATTR_CAR], "async_log_fillup", call.data)

        async def _handle_log_service(call: ServiceCall) -> None:
            await _dispatch_to_car(hass, call.data[ATTR_CAR], "async_log_service", call.data)

        async def _handle_retire_car(call: ServiceCall) -> None:
            await _dispatch_to_car(hass, call.data[ATTR_CAR], "async_retire_car", call.data)

        async def _handle_unretire_car(call: ServiceCall) -> None:
            await _dispatch_to_car(hass, call.data[ATTR_CAR], "async_unretire_car", call.data)

        hass.services.async_register(
            DOMAIN, SERVICE_LOG_FILLUP, _handle_log_fillup, schema=LOG_FILLUP_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_LOG_SERVICE, _handle_log_service, schema=LOG_SERVICE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_RETIRE_CAR, _handle_retire_car, schema=RETIRE_CAR_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_UNRETIRE_CAR, _handle_unretire_car, schema=UNRETIRE_CAR_SCHEMA
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _dispatch_to_car(hass: HomeAssistant, car_name: str, method: str, data: dict) -> None:
    """Find the coordinator matching car_name (case-insensitive) and call method on it."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if coordinator.car_name.lower() == car_name.lower():
            await getattr(coordinator, method)(data)
            return
    raise ValueError(
        f"Car Fuel Tracker: no car named '{car_name}' found. "
        f"Check spelling against the car name used when adding the integration."
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
