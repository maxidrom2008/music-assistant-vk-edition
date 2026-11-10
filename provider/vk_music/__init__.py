"""VK Music provider for Music Assistant 2.10.9.

Uses an existing VK access token. It never collects passwords, automates login,
downloads audio to disk, or bypasses service access controls.
"""
from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.enums import ContentType, ImageType, MediaType, ProviderFeature, StreamType
from music_assistant_models.errors import LoginFailed, MediaNotFoundError, SetupFailedError
from music_assistant_models.media_items import (
    Album,
    AudioFormat,
    Artist,
    BrowseFolder,
    ItemMapping,
    MediaItemImage,
    Playlist,
    ProviderMapping,
    SearchResults,
    Track,
    UniqueList,
)
from music_assistant_models.streamdetails import StreamDetails
from vkpymusic import Service
from vkpymusic.vk_api import VkApiException

if TYPE_CHECKING:
    from collections.abc import Sequence
    from music_assistant import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant_models.config_entries import ProviderConfig
    from music_assistant_models.media_items import MediaItemType
    from music_assistant_models.provider import ProviderManifest

CONF_TOKEN = "token"
CONF_USER_AGENT = "user_agent"
SUPPORTED_FEATURES = {
    ProviderFeature.SEARCH,
    ProviderFeature.BROWSE,
    ProviderFeature.ARTIST_ALBUMS,
    ProviderFeature.ARTIST_TOPTRACKS,
}


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize the provider and its secure account configuration."""
    return VKMusicProvider(mass, manifest, config, SUPPORTED_FEATURES)


class VKMusicProvider(MusicProvider):
    """VK track search, artist discovery and playlist/album browsing."""

    _service: Service

    @property
    def is_streaming_provider(self) -> bool:
        """VK is an online music provider."""
        return True

    @property
    def max_concurrent_streams(self) -> int:
        """Use a conservative per-account stream limit."""
        return 2

    async def handle_async_init(self) -> None:
        """Create the API client and validate the saved token."""
        token = str(self.get_setup_value(CONF_TOKEN) or "")
        user_agent = str(self.get_setup_value(CONF_USER_AGENT) or "")
        if not token or not user_agent:
            raise LoginFailed("VK access token and User-Agent are required")
        self._service = Service(user_agent=user_agent, token=token)
        try:
            valid = await self._service.is_token_valid_async()
        except Exception as err:
            raise SetupFailedError(
                f"Could not validate VK credentials ({type(err).__name__})"
            ) from err
        if not valid:
            raise LoginFailed("VK access token is invalid or expired")

    def _mapping(self, item_id: str) -> set[ProviderMapping]:
        return {
            ProviderMapping(
                item_id=item_id,
                provider_domain=self.domain,
                provider_instance=self.instance_id,
            )
        }

    @staticmethod
    def _encode_collection_id(entry, media_type: MediaType) -> str:
        """Encode VK collection identifiers and metadata without exposing delimiters."""
        payload = {
            "owner": str(entry.owner_id),
            "playlist": str(entry.playlist_id),
            "key": str(entry.access_key),
            "name": str(entry.title or ""),
            "description": str(getattr(entry, "description", "") or ""),
            "photo": str(getattr(entry, "photo", "") or ""),
            "type": media_type.value,
        }
        packed = base64.urlsafe_b64encode(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        ).decode().rstrip("=")
        return f"vk:{packed}"

    @staticmethod
    def _decode_collection_id(item_id: str) -> dict[str, str]:
        """Decode a VK collection id and its cached descriptive metadata."""
        try:
            packed = item_id.removeprefix("vk:")
            packed += "=" * (-len(packed) % 4)
            payload = json.loads(base64.urlsafe_b64decode(packed).decode())
            if not payload.get("owner") or not payload.get("playlist") or "key" not in payload:
                raise ValueError("missing collection fields")
            return payload
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as err:
            raise MediaNotFoundError("Invalid VK collection identifier") from err

    def _parse_song(self, song) -> Track:
        """Convert VK audio metadata into a Music Assistant track."""
        item_id = f"{song.owner_id}_{song.track_id}"
        artist_items = UniqueList(
            [
                ItemMapping(
                    item_id=f"artist:{song.artist.casefold()}",
                    provider=self.instance_id,
                    name=song.artist,
                    media_type=MediaType.ARTIST,
                )
            ]
            if song.artist
            else []
        )
        return Track(
            item_id=item_id,
            provider=self.instance_id,
            name=song.title or "Unknown title",
            artists=artist_items,
            duration=max(0, int(song.duration or 0)),
            provider_mappings=self._mapping(item_id),
        )

    def _parse_artist(self, name: str) -> Artist:
        """Represent a VK artist by a normalized search identity."""
        item_id = f"artist:{name.casefold()}"
        return Artist(
            item_id=item_id,
            provider=self.instance_id,
            name=name,
            provider_mappings=self._mapping(item_id),
        )

    def _parse_vk_collection(self, entry, media_type: MediaType) -> Album | Playlist:
        """Convert the VK library's playlist-shaped album and playlist objects."""
        item_id = self._encode_collection_id(entry, media_type)
        mapping = self._mapping(item_id)
        if media_type == MediaType.ALBUM:
            item = Album(
                item_id=item_id,
                provider=self.instance_id,
                name=entry.title or "Untitled album",
                provider_mappings=mapping,
            )
        else:
            item = Playlist(
                item_id=item_id,
                provider=self.instance_id,
                name=entry.title or "Untitled playlist",
                owner=str(entry.owner_id),
                provider_mappings=mapping,
            )
        if description := getattr(entry, "description", None):
            item.metadata.description = description
        if photo := getattr(entry, "photo", None):
            item.metadata.images = UniqueList(
                [MediaItemImage(type=ImageType.THUMB, path=photo, provider=self.instance_id, remotely_accessible=True)]
            )
        return item

    async def search(
        self, search_query: str, media_types: list[MediaType], limit: int = 5
    ) -> SearchResults:
        """Search VK tracks, playlists and albums; derive artists from track matches."""
        results = SearchResults()
        query = search_query.strip()
        if not query:
            return results
        safe_limit = min(max(limit, 1), 30)
        if MediaType.TRACK in media_types or MediaType.ARTIST in media_types:
            try:
                songs = await self._service.search_songs_by_text_async(query, count=safe_limit)
                if MediaType.TRACK in media_types:
                    results.tracks = [self._parse_song(song) for song in songs]
                if MediaType.ARTIST in media_types:
                    seen: set[str] = set()
                    artists: list[Artist] = []
                    for song in songs:
                        if not song.artist:
                            continue
                        key = song.artist.casefold()
                        if key not in seen:
                            seen.add(key)
                            artists.append(self._parse_artist(song.artist))
                    results.artists = artists[:safe_limit]
            except VkApiException as err:
                self.logger.warning("VK track search denied or failed (code %s)", getattr(err, "error_code", "unknown"))
            except Exception as err:
                self.logger.warning("Unexpected VK track search failure (%s)", type(err).__name__)
        if MediaType.ALBUM in media_types:
            try:
                albums = await self._service.search_albums_by_text_async(query, count=safe_limit)
                results.albums = [
                    self._parse_vk_collection(item, MediaType.ALBUM) for item in albums
                ]
            except VkApiException as err:
                self.logger.warning("VK album search denied or failed (code %s)", getattr(err, "error_code", "unknown"))
            except Exception as err:
                self.logger.warning("Unexpected VK album search failure (%s)", type(err).__name__)
        if MediaType.PLAYLIST in media_types:
            try:
                playlists = await self._service.search_playlists_by_text_async(query, count=safe_limit)
                results.playlists = [
                    self._parse_vk_collection(item, MediaType.PLAYLIST) for item in playlists
                ]
            except VkApiException as err:
                self.logger.warning("VK playlist search denied or failed (code %s)", getattr(err, "error_code", "unknown"))
            except Exception as err:
                self.logger.warning("Unexpected VK playlist search failure (%s)", type(err).__name__)
        return results

    async def get_track(self, prov_track_id: str) -> Track:
        """Retrieve current metadata for a VK track."""
        owner, separator, track = prov_track_id.partition("_")
        if not separator or not owner or not track:
            raise MediaNotFoundError(f"Invalid VK track id: {prov_track_id}")
        songs = await self._service.get_songs_by_id_async([f"{owner}_{track}"])
        if not songs:
            raise MediaNotFoundError(f"VK track not found: {prov_track_id}")
        return self._parse_song(songs[0])

    async def get_artist(self, prov_artist_id: str) -> Artist:
        """Resolve an artist identity referenced by VK tracks."""
        name = prov_artist_id.removeprefix("artist:").strip()
        if not name:
            raise MediaNotFoundError("Invalid VK artist identifier")
        return self._parse_artist(name)

    def _apply_collection_metadata(self, item: Album | Playlist, payload: dict[str, str]) -> None:
        """Restore collection text and artwork saved with a provider item id."""
        if description := payload.get("description"):
            item.metadata.description = description
        if photo := payload.get("photo"):
            item.metadata.images = UniqueList(
                [
                    MediaItemImage(
                        type=ImageType.THUMB,
                        path=photo,
                        provider=self.instance_id,
                        remotely_accessible=True,
                    )
                ]
            )

    async def get_album(self, prov_album_id: str) -> Album:
        """Resolve an album selected from VK search."""
        payload = self._decode_collection_id(prov_album_id)
        item = Album(
            item_id=prov_album_id,
            provider=self.instance_id,
            name=payload.get("name") or f"VK album {payload['playlist']}",
            provider_mappings=self._mapping(prov_album_id),
        )
        self._apply_collection_metadata(item, payload)
        return item

    async def get_playlist(self, prov_playlist_id: str) -> Playlist:
        """Resolve a playlist selected from VK search."""
        payload = self._decode_collection_id(prov_playlist_id)
        item = Playlist(
            item_id=prov_playlist_id,
            provider=self.instance_id,
            name=payload.get("name") or f"VK playlist {payload['playlist']}",
            owner=payload["owner"],
            provider_mappings=self._mapping(prov_playlist_id),
        )
        self._apply_collection_metadata(item, payload)
        return item

    async def get_album_tracks(self, prov_album_id: str) -> list[Track]:
        """Fetch the tracks belonging to a VK album."""
        payload = self._decode_collection_id(prov_album_id)
        owner, playlist, access_key = int(payload['owner']), int(payload['playlist']), payload['key']
        songs = await self._service.get_songs_by_playlist_id_async(
            owner, playlist, access_key, count=100, offset=0
        )
        return [self._parse_song(song) for song in songs]

    async def get_playlist_tracks(self, prov_playlist_id: str, page: int = 0) -> list[Track]:
        """Fetch one page of a VK playlist."""
        payload = self._decode_collection_id(prov_playlist_id)
        owner, playlist, access_key = int(payload['owner']), int(payload['playlist']), payload['key']
        songs = await self._service.get_songs_by_playlist_id_async(
            owner, playlist, access_key, count=100, offset=page * 100
        )
        return [self._parse_song(song) for song in songs]

    async def get_artist_albums(self, prov_artist_id: str) -> list[Album]:
        """Search VK albums using the artist name."""
        name = prov_artist_id.removeprefix("artist:")
        entries = await self._service.search_albums_by_text_async(name, count=30)
        return [self._parse_vk_collection(item, MediaType.ALBUM) for item in entries]

    async def get_artist_toptracks(self, prov_artist_id: str, limit: int = 25) -> list[Track]:
        """Search for the artist's tracks."""
        name = prov_artist_id.removeprefix("artist:")
        songs = await self._service.search_songs_by_text_async(name, count=min(limit, 30))
        return [self._parse_song(song) for song in songs]

    async def browse(self, path: str) -> Sequence[MediaItemType | ItemMapping | BrowseFolder]:
        """Browse the authenticated user's VK playlists."""
        if path.rstrip("/").endswith("://") or path in ("", f"{self.instance_id}://"):
            return [
                BrowseFolder(
                    item_id="my_playlists",
                    provider=self.instance_id,
                    name="My VK playlists",
                )
            ]
        if path.rstrip("/").endswith("my_playlists") or path.endswith("://my_playlists"):
            user = await self._service.get_user_info_async()
            entries = await self._service.get_playlists_by_userid_async(user.userid, count=100)
            return [
                self._parse_vk_collection(item, MediaType.PLAYLIST) for item in entries
            ]
        return []

    async def get_stream_details(self, item_id: str, media_type: MediaType) -> StreamDetails:
        """Resolve a fresh stream URL immediately before playback."""
        try:
            owner, separator, track = item_id.partition("_")
            if not separator or not owner or not track:
                raise MediaNotFoundError(f"Invalid VK track id: {item_id}")
            try:
                songs = await self._service.get_songs_by_id_async([f"{owner}_{track}"])
            except VkApiException as err:
                if getattr(err, "error_code", None) in (5, 201):
                    raise LoginFailed("VK denied access to this audio; check account entitlement") from err
                raise
            if not songs or not songs[0].url:
                raise MediaNotFoundError(f"VK did not provide an accessible stream for {item_id}")
            url = songs[0].url
            content_type = ContentType.try_parse(url.split("?", 1)[0])
            self.logger.debug(
                "VK stream metadata resolved for %s (content_type=%s)",
                item_id,
                content_type,
            )
            return StreamDetails(
                provider=self.instance_id,
                item_id=item_id,
                media_type=MediaType.TRACK,
                audio_format=AudioFormat(content_type=content_type),
                stream_type=StreamType.HTTP,
                path=url,
                can_seek=True,
                allow_seek=True,
            )
        except Exception as err:
            self.logger.exception(
                "VK playback stream resolution failed for %s (%s)",
                item_id,
                type(err).__name__,
            )
            raise
