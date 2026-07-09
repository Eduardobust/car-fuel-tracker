"""Constants for the Car and Fuel Tracker integration."""

DOMAIN = "car_fuel_tracker"

# Config entry keys (one config entry = one car)
CONF_CAR_NAME = "car_name"
CONF_STARTING_ODOMETER = "starting_odometer"
CONF_DEFAULT_FUEL_GRADE = "default_fuel_grade"
CONF_GOOGLE_SHEETS_ENTRY_ID = "google_sheets_entry_id"
CONF_GOOGLE_SHEET_ID = "google_sheet_id"

# Car profile keys (static-ish info captured when the car is added)
CONF_BRAND = "brand"
CONF_MODEL = "model"
CONF_YEAR = "year"
CONF_COLOR = "color"
CONF_PURCHASE_COST = "purchase_cost"
CONF_COMMENT = "comment"

FUEL_GRADES = ["regular", "premium", "diesel", "ethanol", "other"]

# Display unit for the Consumption sensor (raw calc is always stored as L/100km internally)
CONF_CONSUMPTION_UNIT = "consumption_unit"
CONSUMPTION_UNIT_L_100KM = "l_100km"
CONSUMPTION_UNIT_KM_PER_L = "km_per_l"
CONSUMPTION_UNIT_MPG_US = "mpg_us"
CONSUMPTION_UNIT_MPG_UK = "mpg_uk"
CONSUMPTION_UNITS = [
    CONSUMPTION_UNIT_L_100KM,
    CONSUMPTION_UNIT_KM_PER_L,
    CONSUMPTION_UNIT_MPG_US,
    CONSUMPTION_UNIT_MPG_UK,
]
CONSUMPTION_UNIT_LABELS = {
    CONSUMPTION_UNIT_L_100KM: "L/100km",
    CONSUMPTION_UNIT_KM_PER_L: "km/L",
    CONSUMPTION_UNIT_MPG_US: "mpg (US)",
    CONSUMPTION_UNIT_MPG_UK: "mpg (UK)",
}

# Rolling average windows for cost-per-km
AVG_WINDOW_10_FILLS = "10_fills"
AVG_WINDOW_180_DAYS = "180_days"
AVG_WINDOW_LIFETIME = "lifetime"
AVG_WINDOWS = [AVG_WINDOW_10_FILLS, AVG_WINDOW_180_DAYS, AVG_WINDOW_LIFETIME]

# Storage
STORAGE_VERSION = 1
STORAGE_KEY_FMT = "fuel_tracker_{entry_id}"

# Services
SERVICE_LOG_FILLUP = "log_fillup"
SERVICE_LOG_SERVICE = "log_service"
SERVICE_RETIRE_CAR = "retire_car"
SERVICE_UNRETIRE_CAR = "unretire_car"

ATTR_CAR = "car"
ATTR_ODOMETER = "odometer"
ATTR_VOLUME = "volume"
ATTR_COST_PER_LITER = "cost_per_liter"
ATTR_FUEL_GRADE = "fuel_grade"
ATTR_FULL_TANK = "full_tank"
ATTR_TIRE_PRESSURE_CHECKED = "tire_pressure_checked"
ATTR_STATION_NAME = "station_name"
ATTR_STATION_BRAND = "station_brand"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"

ATTR_SERVICE_TYPE = "service_type"
ATTR_COST = "cost"
ATTR_NOTES = "notes"

ATTR_RETIREMENT_REASON = "retirement_reason"
ATTR_FINAL_ODOMETER = "final_odometer"

CAR_STATUS_ACTIVE = "active"
CAR_STATUS_RETIRED = "retired"
