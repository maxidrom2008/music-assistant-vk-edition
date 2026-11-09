"""Experimental VK Music provider placeholder for Music Assistant 2.10.9.

This module deliberately advertises no music features yet. Catalog access,
authentication and playback must be implemented and tested before enabling them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant.models.music_provider import MusicProvider

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant_models.config_entries import ProviderConfig
    from music_assistant_models.provider import ProviderManifest

SUPPORTED_FEATURES: set = set()


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Set up the experimental provider without claiming unsupported features."""
    return VKMusicProvider(mass, manifest, config, SUPPORTED_FEATURES)


class VKMusicProvider(MusicProvider):
    """Scaffold only; search and playback are intentionally not implemented."""

    @property
    def is_streaming_provider(self) -> bool:
        """VK is intended to be a streaming/catalog provider."""
        return True
