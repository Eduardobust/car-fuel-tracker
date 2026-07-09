"""Config flow for Car and Fuel Tracker. Each config entry = one car."""
from __future__ import annotations

import datetime

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CAR_STATUS_RETIRED,
    CONF_BRAND,
    CONF_CAR_NAME,
    CONF_COLOR,
    CONF_COMMENT,
    CONF_CONSUMPTION_UNIT,
    CONF_DEFAULT_FUEL_GRADE,
    CONF_GOOGLE_SHEET_ID,
    CONF_GOOGLE_SHEETS_ENTRY_ID,
    CONF_MODEL,
    CONF_PURCHASE_COST,
    CONF_STARTING_ODOMETER,
    CONF_YEAR,
    CONSUMPTION_UNIT_L_100KM,
    CONSUMPTION_UNITS,
    DOMAIN,
    FUEL_GRADES,
)

CURRENT_YEAR = datetime.date.today().year


class CarFuelTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle adding a new car to Car and Fuel Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            car_name = user_input[CONF_CAR_NAME].strip()

            for entry in self._async_current_entries():
                if entry.data.get(CONF_CAR_NAME, "").lower() == car_name.lower():
                    errors["base"] = "already_configured"
                    break

            if not errors:
                await self.async_set_unique_id(car_name.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=car_name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_CAR_NAME): str,
                vol.Optional(CONF_BRAND, default=""): str,
                vol.Optional(CONF_MODEL, default=""): str,
                vol.Optional(CONF_YEAR, default=CURRENT_YEAR): vol.Coerce(int),
                vol.Optional(CONF_COLOR, default=""): str,
                vol.Optional(CONF_PURCHASE_COST, default=0): vol.Coerce(float),
                vol.Required(CONF_STARTING_ODOMETER, default=0): vol.Coerce(float),
                vol.Required(
                    CONF_DEFAULT_FUEL_GRADE, default=FUEL_GRADES[0]
                ): vol.In(FUEL_GRADES),
                vol.Optional(CONF_COMMENT, default=""): str,
                vol.Optional(
                    CONF_CONSUMPTION_UNIT, default=CONSUMPTION_UNIT_L_100KM
                ): vol.In(CONSUMPTION_UNITS),
                # Optional: config_entry_id of an already-configured Google Sheets
                # integration, and the target sheet ID within it. Leave blank to
                # skip Sheets sync for this car (beta v0 — local sensors only).
                vol.Optional(CONF_GOOGLE_SHEETS_ENTRY_ID, default=""): str,
                vol.Optional(CONF_GOOGLE_SHEET_ID, default=""): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CarFuelTrackerOptionsFlow()


class CarFuelTrackerOptionsFlow(config_entries.OptionsFlow):
    """Edit Sheets linkage / fuel grade / comment / consumption unit, and
    retire or un-retire the car via a checkbox.

    HA forms can't show/hide fields live based on another field in the same
    screen, so this is implemented as two steps: check "Retired?" and submit
    -> if newly retiring, a second screen asks for the justification fields.
    Unmarking it (un-retiring) needs no second screen.

    Do NOT set self.config_entry manually — on current Home Assistant
    versions it's a read-only property populated by the framework.
    """

    def __init__(self) -> None:
        self._pending_options: dict | None = None

    async def async_step_init(self, user_input=None):
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        currently_retired = coordinator.status == CAR_STATUS_RETIRED

        if user_input is not None:
            retired_requested = user_input.pop("retired", False)
            self._pending_options = user_input

            if retired_requested and not currently_retired:
                # Newly retiring -> ask for justification on a second screen
                return await self.async_step_retire_details()

            if not retired_requested and currently_retired:
                # Un-retiring -> no extra fields needed
                await coordinator.async_unretire_car({})

            return self.async_create_entry(title="", data=self._pending_options)

        current = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEFAULT_FUEL_GRADE,
                    default=current.get(CONF_DEFAULT_FUEL_GRADE, FUEL_GRADES[0]),
                ): vol.In(FUEL_GRADES),
                vol.Optional(
                    CONF_COMMENT, default=current.get(CONF_COMMENT, "")
                ): str,
                vol.Optional(
                    CONF_CONSUMPTION_UNIT,
                    default=current.get(CONF_CONSUMPTION_UNIT, CONSUMPTION_UNIT_L_100KM),
                ): vol.In(CONSUMPTION_UNITS),
                vol.Optional(
                    CONF_GOOGLE_SHEETS_ENTRY_ID,
                    default=current.get(CONF_GOOGLE_SHEETS_ENTRY_ID, ""),
                ): str,
                vol.Optional(
                    CONF_GOOGLE_SHEET_ID,
                    default=current.get(CONF_GOOGLE_SHEET_ID, ""),
                ): str,
                vol.Optional("retired", default=currently_retired): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_retire_details(self, user_input=None):
        if user_input is not None:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            await coordinator.async_retire_car(
                {
                    "retirement_reason": user_input.get("retirement_reason", ""),
                    "final_odometer": user_input.get("final_odometer"),
                }
            )
            return self.async_create_entry(title="", data=self._pending_options or {})

        schema = vol.Schema(
            {
                vol.Optional("retirement_reason", default=""): str,
                vol.Optional("final_odometer"): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="retire_details", data_schema=schema)
