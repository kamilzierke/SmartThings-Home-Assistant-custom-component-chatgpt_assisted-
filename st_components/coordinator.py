from __future__ import annotations
from datetime import timedelta, datetime, timezone
from typing import Any
import logging
import json
from aiohttp import ClientResponseError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import STApiClient

_LOGGER = logging.getLogger(__name__)


def _trim(obj: Any, limit: int = 800) -> str:
    """Zamień obiekt na krótki string do logów debug."""
    try:
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        s = str(obj)
    return (s[:limit] + "…") if len(s) > limit else s


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        return None


class STCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Koordynator zapytań do SmartThings z ochroną przed 429 i wyłączaniem refresh dla urządzeń z deltaEnergy."""

    def __init__(
        self,
        hass: HomeAssistant,
        token: str,
        device_id: str,
        scan_interval: int,
        stale_after_s: int,
        cooldown_after_429_s: int,
    ):
        base = max(5, int(scan_interval))
        super().__init__(
            hass,
            _LOGGER,
            name="st_components",
            update_interval=timedelta(seconds=base),
        )
        self._device_id = device_id
        self._client = STApiClient(async_get_clientsession(hass), token)

        self._base_interval = timedelta(seconds=base)
        self._cooldown_until: datetime | None = None
        self._stale_after_s = int(stale_after_s)
        self._cooldown_after_429_s = int(cooldown_after_429_s)

        # Gdy wykryjemy deltaEnergy w PCR → blokujemy refresh (by nie resetować sesji energii)
        self._refresh_blocked_due_to_delta = False

    # ===== Live options =====
    def update_options(self, scan_interval: int, stale_after_s: int, cooldown_after_429_s: int) -> None:
        self._base_interval = timedelta(seconds=max(5, int(scan_interval)))
        self._stale_after_s = int(stale_after_s)
        self._cooldown_after_429_s = int(cooldown_after_429_s)
        if not self._in_cooldown():
            self.update_interval = self._base_interval
        _LOGGER.info(
            "Options updated: interval=%ss, stale_after=%ss, cooldown_429=%ss",
            int(self._base_interval.total_seconds()), self._stale_after_s, self._cooldown_after_429_s
        )

    # ===== Cooldown helpers =====
    def _in_cooldown(self) -> bool:
        return self._cooldown_until is not None and datetime.now(timezone.utc) < self._cooldown_until

    def _enter_cooldown(self) -> None:
        self._cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=self._cooldown_after_429_s)
        # Podnieś interwał w trakcie cooldownu (np. do 30 s; nie schodź poniżej bazowego)
        self.update_interval = max(self._base_interval, timedelta(seconds=30))
        _LOGGER.warning(
            "SmartThings rate-limited (429). Entering cooldown until %s; interval temporarily %ss",
            self._cooldown_until,
            int(self.update_interval.total_seconds()),
        )

    def _exit_cooldown_if_needed(self) -> None:
        if self._in_cooldown():
            return
        if self._cooldown_until is not None:
            _LOGGER.info("Fetching st_components data recovered (cooldown ended at %s)", self._cooldown_until)
            self._cooldown_until = None
            self.update_interval = self._base_interval

    # ===== Refresh logic =====
    async def _maybe_refresh(self, last_end_iso: str | None) -> None:
        """Wyślij refresh tylko jeśli dane są 'stare', nie ma cooldownu i nie wykryliśmy deltaEnergy."""
        if self._refresh_blocked_due_to_delta:
            _LOGGER.debug("Refresh disabled because device reports deltaEnergy (protect energy session).")
            return

        if self._in_cooldown():
            _LOGGER.debug("Skipping refresh (in cooldown until %s)", self._cooldown_until)
            return

        end_dt = _parse_iso(last_end_iso)
        if not end_dt:
            try:
                _LOGGER.debug("Sending SmartThings refresh (no end_ts in PCR)")
                await self._client.send_command(self._device_id, "main", "refresh", "refresh", [])
            except Exception as err:
                _LOGGER.debug("Refresh not supported or failed: %s", err)
            return

        age_s = max(0, int((datetime.now(timezone.utc) - end_dt).total_seconds()))
        if age_s >= self._stale_after_s:
            try:
                _LOGGER.debug("Sending SmartThings refresh (PCR age ~%ss ≥ %s)", age_s, self._stale_after_s)
                await self._client.send_command(self._device_id, "main", "refresh", "refresh", [])
            except Exception as err:
                _LOGGER.debug("Refresh not supported or failed: %s", err)
        else:
            _LOGGER.debug("Not refreshing (PCR age ~%ss < %s)", age_s, self._stale_after_s)

    # ===== Main update =====
    async def _async_update_data(self) -> dict[str, Any]:
        _LOGGER.debug("Polling SmartThings /status for device %s", self._device_id)

        # Sprawdź poprzedni snapshot pod kątem deltaEnergy → ewentualnie zablokuj refresh,
        # zanim zdecydujemy, czy go wysyłać w tym cyklu.
        prev = self.data or {}
        prev_val = (((prev.get("components") or {}).get("main") or {})
                    .get("powerConsumptionReport") or {}).get("powerConsumption", {})
        prev_val = prev_val.get("value")
        prev_last = prev_val[-1] if isinstance(prev_val, list) and prev_val else prev_val
        if isinstance(prev_last, dict) and ("deltaEnergy" in prev_last):
            if not self._refresh_blocked_due_to_delta:
                self._refresh_blocked_due_to_delta = True
                _LOGGER.info(
                    "Detected powerConsumptionReport.deltaEnergy in device %s → disabling refresh to avoid energy reset.",
                    self._device_id,
                )

        prev_end_ts = prev_last.get("end") if isinstance(prev_last, dict) else None
        await self._maybe_refresh(prev_end_ts)

        try:
            data = await self._client.get_status(self._device_id)

            comps = (data or {}).get("components", {}) or {}
            main = comps.get("main", {}) or {}

            pcr = (main.get("powerConsumptionReport", {}) or {}).get("powerConsumption", {}) or {}
            pcr_val = pcr.get("value")
            last_pcr = pcr_val[-1] if isinstance(pcr_val, list) and pcr_val else pcr_val

            em = (main.get("energyMeter", {}) or {}).get("energy", {}) or {}
            pm = (main.get("powerMeter", {}) or {}).get("power", {}) or {}

            # Po aktualnym odczycie też aktualizujemy heurystykę blokującą refresh.
            if isinstance(last_pcr, dict) and ("deltaEnergy" in last_pcr):
                if not self._refresh_blocked_due_to_delta:
                    self._refresh_blocked_due_to_delta = True
                    _LOGGER.info(
                        "Detected powerConsumptionReport.deltaEnergy in device %s → disabling refresh to avoid energy reset.",
                        self._device_id,
                    )

            end_ts = last_pcr.get("end") if isinstance(last_pcr, dict) else None
            end_dt = _parse_iso(end_ts)
            if end_dt:
                age_s = max(0, int((datetime.now(timezone.utc) - end_dt).total_seconds()))
                if age_s > 600:
                    _LOGGER.warning("ST PCR data appears stale: last end=%s (age ~%ss)", end_ts, age_s)

            _LOGGER.debug(
                "ST /status snapshot | PCR last=%s | energyMeter=%s | powerMeter=%s",
                _trim(last_pcr), _trim(em), _trim(pm),
            )

            # sukces → spróbuj wyjść z cooldownu i przywrócić interwał
            self._exit_cooldown_if_needed()
            return data or {}

        except ClientResponseError as err:
            if err.status == 429:
                self._enter_cooldown()
            _LOGGER.error("Error fetching st_components data: %s", err)
            raise UpdateFailed(str(err)) from err

        except Exception as err:
            _LOGGER.warning("SmartThings /status failed for %s: %s", self._device_id, err)
            raise UpdateFailed(str(err)) from err

    @property
    def device_id(self) -> str:
        return self._device_id

    async def command(self, component: str, capability: str, command: str, arguments=None) -> dict:
        return await self._client.send_command(self._device_id, component, capability, command, arguments or [])
