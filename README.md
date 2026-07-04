# Car and Fuel Tracker (beta v0)

Custom Home Assistant integration to track vehicle profiles, fuel fill-ups,
and service/maintenance events for one or more cars. Each car is a config
entry → shows up as its own **device** with a set of sensors. Data is
written locally (HA statistics) and, optionally, synced to Google Sheets.

This is a **beta / revision zero** build — functional core, expect rough edges.

## What's included

- `custom_components/car_fuel_tracker/` — the integration (domain: `car_fuel_tracker`)
- Config flow: Settings → Devices & Services → Add Integration →
  **Car and Fuel Tracker** → enter car name + full vehicle profile (brand,
  model, year, color, purchase cost, starting odometer, default fuel grade,
  free-text comment), and optionally a Google Sheets config entry ID + sheet
  ID to sync to.
- Three services:
  - `car_fuel_tracker.log_fillup`
  - `car_fuel_tracker.log_service`
  - `car_fuel_tracker.retire_car` — freezes the car (sold/crashed/retired):
    no further fillups or service entries accepted afterward.
- Per-car sensors (all under one device):
  - **Car Info** — state is "Brand Model", attributes: brand, model, year,
    color, purchase_cost, starting_odometer, comment
  - **Status** — "active" or "retired", attributes: retired_date,
    retirement_reason, final_odometer
  - Last Fillup (+ full attribute set: odometer, volume, fuel_grade, cost,
    full_tank, station_name, lat/lon, tire_pressure_checked)
  - Odometer
  - Consumption (L/100km — only calculated between two full-tank fills)
  - Cost per km (last fill)
  - Cost per km (last 10 fills / 180 days / lifetime) — three separate sensors
  - Days Since Tire Check
  - Last Service

## Installation

1. Push this repo to your own GitHub account.
2. In HA: HACS → the "⋮" menu → **Custom repositories** → add your repo URL,
   category "Integration".
3. Install "Car and Fuel Tracker" from HACS, restart HA.
4. Settings → Devices & Services → Add Integration → search "Car and Fuel Tracker".
5. Repeat step 4 once per car, filling in the vehicle profile form.

## Retiring a car

Call the `car_fuel_tracker.retire_car` service (e.g. from a dashboard button
or Developer Tools → Actions) with the car name, an optional reason
("sold", "crashed", "traded in"), and an optional final odometer reading. From
that point on, `log_fillup` and `log_service` for that car will raise an
error — its history stays visible and intact, but frozen. There's currently
no "un-retire" action in this beta; if you need to reverse it, delete and
re-add the storage entry manually (ask me and I'll add an un-retire service
in the next iteration if useful).

## Google Sheets sync (optional)

1. Set up HA's native **Google Sheets** integration first (Settings → Devices &
   Services → Add Integration → Google Sheets) and note its config entry ID
   (Developer Tools → Actions → `google_sheets.append_sheet` will show you
   available config entries).
2. When adding a car, paste that config entry ID and the target Sheet ID into
   the optional fields (or add later via the car's "Configure" options).
3. If left blank, Car and Fuel Tracker just runs locally — Sheets sync is
   best-effort and never blocks local sensor updates if it fails.
4. Retirement events also push a row to a "retirement" tab if Sheets is linked.

## Example: automation to capture GPS + trigger the fill-up form

Assumes a `person.eduardo` entity from the HA Companion App with location
tracking enabled, and an `input_boolean.trigger_fillup_form` you press at the
pump.

```yaml
automation:
  - alias: "Car Fuel Tracker - capture GPS on fillup trigger"
    trigger:
      - platform: state
        entity_id: input_boolean.trigger_fillup_form
        to: "on"
    action:
      - service: input_text.set_value
        target:
          entity_id: input_text.fillup_latitude
        data:
          value: "{{ state_attr('person.eduardo', 'latitude') }}"
      - service: input_text.set_value
        target:
          entity_id: input_text.fillup_longitude
        data:
          value: "{{ state_attr('person.eduardo', 'longitude') }}"
```

## Example: script to submit a fill-up from dashboard input_helpers

```yaml
script:
  submit_fillup:
    alias: "Submit Fuel Fillup"
    sequence:
      - service: car_fuel_tracker.log_fillup
        data:
          car: "{{ states('input_select.fillup_car') }}"
          odometer: "{{ states('input_number.fillup_odometer') | float }}"
          volume: "{{ states('input_number.fillup_volume') | float }}"
          cost_per_liter: "{{ states('input_number.fillup_cost_per_liter') | float }}"
          fuel_grade: "{{ states('input_select.fillup_fuel_grade') }}"
          full_tank: "{{ is_state('input_boolean.fillup_full_tank', 'on') }}"
          tire_pressure_checked: "{{ is_state('input_boolean.fillup_tire_check', 'on') }}"
          station_name: "{{ states('input_text.fillup_station_name') }}"
          latitude: "{{ states('input_text.fillup_latitude') }}"
          longitude: "{{ states('input_text.fillup_longitude') }}"

  retire_selected_car:
    alias: "Retire Car"
    sequence:
      - service: car_fuel_tracker.retire_car
        data:
          car: "{{ states('input_select.fillup_car') }}"
          retirement_reason: "{{ states('input_text.retirement_reason') }}"
```

## Example: minimal dashboard card

```yaml
type: entities
title: Civic - Fuel Log
entities:
  - input_select.fillup_car
  - input_number.fillup_odometer
  - input_number.fillup_volume
  - input_number.fillup_cost_per_liter
  - input_select.fillup_fuel_grade
  - input_boolean.fillup_full_tank
  - input_boolean.fillup_tire_check
  - input_text.fillup_station_name
  - type: button
    name: Submit Fillup
    icon: mdi:gas-station
    tap_action:
      action: call-service
      service: script.submit_fillup
  - type: button
    name: Retire This Car
    icon: mdi:car-off
    tap_action:
      action: call-service
      service: script.retire_selected_car
      confirmation:
        text: "This freezes the car's data permanently. Continue?"
```

```yaml
type: glance
title: Civic - Status
entities:
  - sensor.civic_car_info
  - sensor.civic_status
  - sensor.civic_odometer
  - sensor.civic_consumption
  - sensor.civic_days_since_tire_check
```

## Known beta v0 limitations / next iteration candidates

- No validation yet on odometer going backwards (e.g. car swap, meter reset).
- `log_fillup`/`log_service`/`retire_car` match cars by name string — case-
  insensitive but exact spelling still matters when calling from
  scripts/automations.
- Google Sheets column headers must be created manually in the sheet to match
  the field names sent (no auto-header creation yet).
- No "un-retire" service yet — retirement is currently one-way in this beta.
- No HACS-native UI for the fill-up form itself — you still build the
  input_helpers + script/dashboard button combo shown above. A custom
  Lovelace card for this is a good v0.2 candidate.
- Consumption-by-fuel-grade comparison sensor not built yet — data already
  supports it, just needs a new derived sensor.
