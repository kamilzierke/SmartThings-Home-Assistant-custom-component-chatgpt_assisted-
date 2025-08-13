# SmartThings Components (per-component entities) for Home Assistant

This is a **custom Home Assistant integration** that exposes **all components and capabilities** of a SmartThings device as separate entities in HA.

Unlike the official SmartThings integration (which primarily maps the `main` component and a limited set of capabilities), this integration automatically discovers **every component** (e.g., `freezer`, `cooler`, `onedoor`, `cvroom`, etc.) and creates entities for all supported attributes.

It’s designed for devices like **Samsung refrigerators** and other multi-component SmartThings devices where important metrics and controls are hidden behind sub-components.

---

## Features

- **Automatic per-component entity creation**
  - Sensors for all numeric attributes
  - Temperature sensors with °C unit
  - Binary sensors for all boolean attributes and contact sensors
  - Number entities for `thermostatCoolingSetpoint` (with read/write support and range detection)
  - Switches for `powerCool` / `powerFreeze` capabilities (activate/deactivate)

- **Full component visibility**
  - Exposes data from *all* components, not just `main`
  - Works with complex devices like multi-zone refrigerators, air conditioners, and heat pumps

- **Device grouping**
  - All entities are grouped under a single HA device for easier management

- **Configurable polling interval**
  - Adjustable in integration options without reinstallation

---

## Requirements

- **Home Assistant 2025.8** or newer
- A **SmartThings Personal Access Token (PAT)** with:
  - `Devices: Read`
  - `Devices: Execute` (for sending commands)

---

## Installation

### HACS (recommended)
1. In HACS → Custom Repositories → add your repo URL, category: `integration`.
2. Search for **SmartThings Components (per-component entities)** and install.
3. Restart Home Assistant.

### Manual
1. Download the latest release ZIP.
2. Extract it into:

config/custom_components/st_components/

3. Restart Home Assistant.

---

## Setup

1. In Home Assistant → Settings → Integrations → **Add Integration**.
2. Search for **SmartThings Components (per-component entities)**.
3. Enter:
- **Personal Access Token** (with or without `Bearer` prefix)
- **Device ID** (from SmartThings)
- **Polling interval** in seconds (default: `30`)

> **How to get a Personal Access Token:**
> - Go to [account.smartthings.com/tokens](https://account.smartthings.com/tokens)
> - Click **Generate New Token**
> - Give it a name, enable `Devices: Read` and `Devices: Execute`, and save.
> - Copy the token.

> **How to get a Device ID:**
> - Go to [my.smartthings.com](https://my.smartthings.com)
> - Click your device → Details → copy the **Device ID**
> - Or use the SmartThings API:
>   ```bash
>   curl -H "Authorization: Bearer <PAT>" https://api.smartthings.com/v1/devices
>   ```

---

## Entities created

Depending on your device capabilities, the integration may create:

- **Temperature sensors**

sensor.st_freezer_temperature
sensor.st_cooler_temperature
sensor.st_onedoor_temperature

- **Numeric sensors** for energy, humidity, etc.
- **Binary sensors** for door status, power state
- **Number entities** for temperature setpoints (read/write)
- **Switches** for special modes like Power Cool / Power Freeze

---

## Limitations

- Uses **polling** (REST API) — update rate is limited by your polling interval.
- SmartThings rate limits apply (default interval: 30 seconds is safe).
- Units for non-temperature sensors are not auto-detected — they appear as raw numeric values unless manually mapped in code.

---

## Roadmap

- Unit mapping for more capabilities (e.g., W, kWh, %, L)
- Optional entity filtering in config flow
- OAuth/Webhook mode for real-time updates

---

## License

MIT License — free for personal and commercial use.

---

**Disclaimer:**  
This integration is not affiliated with or endorsed by Samsung or SmartThings. Use at your own risk.
