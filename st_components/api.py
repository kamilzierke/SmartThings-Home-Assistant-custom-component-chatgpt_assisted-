
from __future__ import annotations
import aiohttp
from typing import Any

SMARTTHINGS_BASE = "https://api.smartthings.com/v1"

class STApiClient:
    def __init__(self, session: aiohttp.ClientSession, token: str):
        self._session = session
        # Accept "Bearer ..." or raw token; always send Bearer
        tok = token.strip()
        if not tok.lower().startswith("bearer "):
            tok = "Bearer " + tok
        self._headers = {"Authorization": tok}

    async def get_status(self, device_id: str) -> dict[str, Any]:
        url = f"{SMARTTHINGS_BASE}/devices/{device_id}/status"
        async with self._session.get(url, headers=self._headers, timeout=20) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def send_command(self, device_id: str, component: str, capability: str, command: str, arguments: list | None = None) -> dict:
        url = f"{SMARTTHINGS_BASE}/devices/{device_id}/commands"
        payload = {
            "commands": [{
                "component": component,
                "capability": capability,
                "command": command,
                "arguments": arguments or []
            }]
        }
        async with self._session.post(url, headers=self._headers, json=payload, timeout=20) as resp:
            resp.raise_for_status()
            return await resp.json()
