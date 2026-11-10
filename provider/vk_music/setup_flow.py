"""Secure setup flow for VK Music credentials; never asks for a VK password."""
from __future__ import annotations
from dataclasses import replace
from typing import TYPE_CHECKING
from music_assistant.models.setup_flow import SetupFlowError
from music_assistant_models.config_entries import ConfigEntry
from music_assistant_models.enums import ConfigEntryType
from . import CONF_TOKEN, CONF_USER_AGENT
if TYPE_CHECKING:
    from music_assistant.models.setup_flow import SetupSession
_ENTRIES = (
    ConfigEntry(key=CONF_TOKEN, type=ConfigEntryType.SECURE_STRING, required=True),
    ConfigEntry(key=CONF_USER_AGENT, type=ConfigEntryType.STRING, required=True),
)
async def run_setup(session: SetupSession) -> None:
    """Collect existing access token and client User-Agent."""
    data = dict(session.context.setup_data)
    errors = None
    while True:
        entries = [replace(entry, value=data.get(entry.key, entry.value)) for entry in _ENTRIES]
        data.update(await session.form(entries, step_id="credentials", errors=errors, last_step=True))
        try:
            await session.finish(data)
            return
        except SetupFlowError as err:
            errors = {"base": err}
