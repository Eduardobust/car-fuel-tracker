"""Sensor platform for Car and Fuel Tracker — one device per car."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FuelTrackerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FuelTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FuelTrackerCarInfoSensor(coordinator, entry),
        FuelTrackerCarStatusSensor(coordinator, entry),
        FuelTrackerLastFillupSensor(coordinator, entry),
        FuelTrackerOdometerSensor(coordinator, entry),
        FuelTrackerConsumptionSensor(coordinator, entry),
        FuelTrackerCostPerKmLastFillSensor(coordinator, entry),
        FuelTrackerTotalVolumeSensor(coordinator, entry),
        FuelTrackerTotalFuelCostSensor(coordinator, entry),
        FuelTrackerFuelCostCurrentMonthSensor(coordinator, entry),
        FuelTrackerFuelCostCurrentYearSensor(coordinator, entry),
        FuelTrackerTotalServiceCostSensor(coordinator, entry),
        FuelTrackerTotalExpenseSensor(coordinator, entry),
        FuelTrackerCostPerKmAvgSensor(coordinator, entry, "10_fills", "Cost per km (last 10 fills)"),
        FuelTrackerCostPerKmAvgSensor(coordinator, entry, "180_days", "Cost per km (180 days)"),
        FuelTrackerCostPerKmAvgSensor(coordinator, entry, "lifetime", "Cost per km (lifetime)"),
        FuelTrackerDaysSinceTireCheckSensor(coordinator, entry),
        FuelTrackerLastServiceSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class _BaseFuelTrackerSensor(CoordinatorEntity, SensorEntity):
    """Common device grouping so all sensors for a car sit under one device."""

    def __init__(self, coordinator: FuelTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._car_name = entry.data["car_name"]

    @property
    def device_info(self) -> DeviceInfo:
        profile = self.coordinator.data.get("car_profile", {}) if self.coordinator.data else {}
        brand = profile.get("brand") or "Car Fuel Tracker"
        model = profile.get("model") or "Vehicle"
        year = profile.get("year")
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._car_name,
            manufacturer=brand,
            model=f"{model} ({year})" if year else model,
        )


class FuelTrackerCarInfoSensor(_BaseFuelTrackerSensor):
    """Static-ish profile info: brand, model, year, color, cost, comment."""

    _attr_icon = "mdi:card-account-details"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_car_info"
        self._attr_name = f"{self._car_name} Car Info"

    @property
    def native_value(self):
        profile = self.coordinator.data.get("car_profile", {})
        brand = profile.get("brand", "")
        model = profile.get("model", "")
        label = f"{brand} {model}".strip()
        return label or self._car_name

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("car_profile", {})


class FuelTrackerCarStatusSensor(_BaseFuelTrackerSensor):
    """active / retired — retired cars are frozen (no new fillups/services)."""

    _attr_icon = "mdi:car-cog"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = f"{self._car_name} Status"

    @property
    def native_value(self):
        return self.coordinator.data.get("status")

    @property
    def extra_state_attributes(self):
        return {
            "retired_date": self.coordinator.data.get("retired_date"),
            "retirement_reason": self.coordinator.data.get("retirement_reason"),
            "final_odometer": self.coordinator.data.get("final_odometer"),
        }


class FuelTrackerLastFillupSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:gas-station"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_fillup"
        self._attr_name = f"{self._car_name} Last Fillup"

    @property
    def native_value(self):
        last = self.coordinator.data.get("last_fillup")
        return last["date"] if last else None

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("last_fillup") or {}


class FuelTrackerOdometerSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "km"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_odometer"
        self._attr_name = f"{self._car_name} Odometer"

    @property
    def native_value(self):
        return self.coordinator.data.get("odometer")


class FuelTrackerConsumptionSensor(_BaseFuelTrackerSensor):
    """Consumption in the car's configured display unit (L/100km, km/L, mpg US/UK)."""

    _attr_icon = "mdi:fuel"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_consumption"
        self._attr_name = f"{self._car_name} Consumption"

    @property
    def native_unit_of_measurement(self):
        return self.coordinator.data.get("consumption_unit_label")

    @property
    def native_value(self):
        return self.coordinator.data.get("consumption_display")

    @property
    def extra_state_attributes(self):
        return {"l_per_100km_raw": self.coordinator.data.get("l_per_100km_raw")}


class FuelTrackerCostPerKmLastFillSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:cash"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cost_per_km_last_fill"
        self._attr_name = f"{self._car_name} Cost per km (last fill)"

    @property
    def native_value(self):
        return self.coordinator.data.get("cost_per_km_last_fill")


class FuelTrackerCostPerKmAvgSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:cash-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, window_key: str, label: str):
        super().__init__(coordinator, entry)
        self._window_key = window_key
        self._attr_unique_id = f"{entry.entry_id}_cost_per_km_avg_{window_key}"
        self._attr_name = f"{self._car_name} {label}"

    @property
    def native_value(self):
        return self.coordinator.data.get(f"cost_per_km_avg_{self._window_key}")


class FuelTrackerTotalVolumeSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:gas-station-outline"
    _attr_native_unit_of_measurement = "L"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_volume"
        self._attr_name = f"{self._car_name} Total Volume Filled"

    @property
    def native_value(self):
        return self.coordinator.data.get("total_volume")


class FuelTrackerTotalFuelCostSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:cash-register"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_fuel_cost"
        self._attr_name = f"{self._car_name} Total Fuel Cost"

    @property
    def native_value(self):
        return self.coordinator.data.get("total_fuel_cost")


class FuelTrackerFuelCostCurrentMonthSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:calendar-month"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fuel_cost_current_month"
        self._attr_name = f"{self._car_name} Fuel Cost (This Month)"

    @property
    def native_value(self):
        return self.coordinator.data.get("fuel_cost_current_month")


class FuelTrackerFuelCostCurrentYearSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:calendar-range"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fuel_cost_current_year"
        self._attr_name = f"{self._car_name} Fuel Cost (This Year)"

    @property
    def native_value(self):
        return self.coordinator.data.get("fuel_cost_current_year")


class FuelTrackerTotalServiceCostSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:wrench-cog"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_service_cost"
        self._attr_name = f"{self._car_name} Total Service Cost"

    @property
    def native_value(self):
        return self.coordinator.data.get("total_service_cost")


class FuelTrackerTotalExpenseSensor(_BaseFuelTrackerSensor):
    """Fuel + service combined, lifetime."""

    _attr_icon = "mdi:cash-multiple"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_expense"
        self._attr_name = f"{self._car_name} Total Expense"

    @property
    def native_value(self):
        return self.coordinator.data.get("total_expense")

    @property
    def extra_state_attributes(self):
        return {
            "total_fuel_cost": self.coordinator.data.get("total_fuel_cost"),
            "total_service_cost": self.coordinator.data.get("total_service_cost"),
        }


class FuelTrackerDaysSinceTireCheckSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:car-tire-alert"
    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_days_since_tire_check"
        self._attr_name = f"{self._car_name} Days Since Tire Check"

    @property
    def native_value(self):
        return self.coordinator.data.get("days_since_tire_check")

    @property
    def extra_state_attributes(self):
        return {"last_checked": self.coordinator.data.get("tire_last_checked")}


class FuelTrackerLastServiceSensor(_BaseFuelTrackerSensor):
    _attr_icon = "mdi:wrench"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_service"
        self._attr_name = f"{self._car_name} Last Service"

    @property
    def native_value(self):
        last = self.coordinator.data.get("last_service")
        return last["date"] if last else None

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("last_service") or {}
