"""Config flow for Car and Fuel Tracker. Each config entry = one car."""
from __future__ import annotations

import datetime

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_BRAND,
    CONF_CAR_NAME,
    CONF_COLOR,
    CONF_COMMENT,
    CONF_DEFAULT_FUEL_GRADE,
    CONF_GOOGLE_SHEET_ID,
    CONF_GOOGLE_SHEETS_ENTRY_ID,
    CONF_MODEL,
    CONF_PURCHASE_COST,
    CONF_STARTING_ODOMETER,
    CONF_YEAR,
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
        return CarFuelTrackerOptionsFlow(config_entry)


class CarFuelTrackerOptionsFlow(config_entries.OptionsFlow):
    """Allow editing Sheets linkage / default fuel grade / comment after setup.

    Note: once a car is retired (see retire_car service), the integration
    treats its data as frozen going forward — this options flow does not
    itself block edits, but retired cars should not be edited.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

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
                    CONF_GOOGLE_SHEETS_ENTRY_ID,
                    default=current.get(CONF_GOOGLE_SHEETS_ENTRY_ID, ""),
                ): str,
                vol.Optional(
                    CONF_GOOGLE_SHEET_ID,
                    default=current.get(CONF_GOOGLE_SHEET_ID, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
