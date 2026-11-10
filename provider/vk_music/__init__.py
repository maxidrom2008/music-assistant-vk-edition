"""VK Music provider for Music Assistant 2.10.9.

Uses a user-supplied VK access token and VKpyMusic's asynchronous API client.
No password collection, credential automation, media downloads, or DRM bypass.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.enums import ContentType, MediaType, ProviderFeature, StreamType
from music_assistant_models.errors import LoginFailed, MediaNotFoundError, SetupFailedError
from music_assistant_models.media_items import AudioFormat, ProviderMapping, SearchResults, Track
from music_assistant_models.streamdetails import StreamDetails
from vkpymusic import Service
from vkpymusic.vk_api import VkApiException

if TYPE_CHECKING:
    from music_assistant import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant_models.config_entries import ProviderConfig
    from music_assistant_models.provider import ProviderManifest

CONF_TOKEN = "token"
CONF_USER_AGENT = "user_agent"
SUPPORTED_FEATURES = {ProviderFeature.SEARCH}

async def setup(mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig) -> ProviderInstanceType:
    """Initialize the provider after validating the saved VK token."""
    return VKMusicProvider(mass, manifest, config, SUPPORTED_FEATURES)

class VKMusicProvider(MusicProvider):
    """VK Music catalog search and entitled audio playback."""

    _service: Service

    @property
    def is_streaming_provider(self) -> bool:
        return True

    @property
    def max_concurrent_streams(self) -> int:
        """Keep concurrency conservative for the account-backed source."""
        return 2

    async def handle_async_init(self) -> None:
        """Create the VK API client and verify the supplied token."""
        token = str(self.get_setup_value(CONF_TOKEN) or "")
        user_agent = str(self.get_setup_value(CONF_USER_AGENT) or "")
        if not token or not user_agent:
            raise LoginFailed("VK access token and user-agent are required")
        self._service = Service(user_agent=user_agent, token=token)
        try:
            valid = await self._service.is_token_valid_async()
        except Exception as err:
            raise SetupFailedError(f"Could not validate VK token: {type(err).__name__}") from err
        if not valid:
            raise LoginFailed("VK access token is invalid or expired")

    async def search(self, search_query: str, media_types: list[MediaType], limit: int = 5) -> SearchResults:
        """Search VK audio tracks."""
        result = SearchResults()
        if MediaType.TRACK not in media_types or not search_query.strip():
            return result
        try:
            songs = await self._service.search_songs_by_text_async(search_query.strip(), count=min(max(limit, 1), 30))
        except VkApiException as err:
            self.logger.warning("VK search failed (code %s)", getattr(err, "error_code", "unknown"))
            return result
        except Exception:
            self.logger.exception("VK search request failed")
            return result
        result.tracks = [self._parse_song(song) for song in songs if song.track_id and song.owner_id]
        return result

    def _parse_song(self, song) -> Track:
        """Map a VK song to a Music Assistant track without exposing its audio URL."""
        item_id = f"{song.owner_id}_{song.track_id}"
        return Track(
            item_id=item_id,
            provider=self.instance_id,
            name=song.title or "Unknown title",
            artists=[song.artist] if song.artist else [],
            duration=int(song.duration or 0),
            provider_mappings={
                ProviderMapping(
                    item_id=item_id,
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                )
            },
        )

    async def get_track(self, prov_track_id: str) -> Track:
        """Resolve a VK track identifier to its current metadata."""
        owner_id, separator, track_id = prov_track_id.partition("_")
        if not separator or not owner_id or not track_id:
            raise MediaNotFoundError(f"Invalid VK track id: {prov_track_id}")
        songs = await self._service.get_songs_by_id_async([f"{owner_id}_{track_id}"])
        if not songs:
            raise MediaNotFoundError(f"VK track not found: {prov_track_id}")
        return self._parse_song(songs[0])

    async def get_stream_details(self, item_id: str, media_type: MediaType) -> StreamDetails:
        """Resolve a fresh authorized audio URL immediately before playback."""
        owner_id, separator, track_id = item_id.partition("_")
        if not separator or not owner_id or not track_id:
            raise MediaNotFoundError(f"Invalid VK track id: {item_id}")
        try:
            songs = await self._service.get_songs_by_id_async([f"{owner_id}_{track_id}"])
        except VkApiException as err:
            if getattr(err, "error_code", None) in (5, 201):
                raise LoginFailed("VK denied access to this audio; check account entitlement") from err
            raise
        if not songs or not songs[0].url:
            raise MediaNotFoundError(f"VK did not provide an accessible stream for {item_id}")
        url = songs[0].url
        content_type = ContentType.try_parse(url.split("?", 1)[0])
        return StreamDetails(
            provider=self.instance_id,
            item_id=item_id,
            media_type=MediaType.TRACK,
            audio_format=AudioFormat(content_type=content_type or ContentType.UNKNOWN),
            stream_type=StreamType.HTTP,
            path=url,
            can_seek=True,
            allow_seek=True,
            is_realtime=True,
        )
