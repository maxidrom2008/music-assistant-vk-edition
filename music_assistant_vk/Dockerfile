FROM ghcr.io/music-assistant/server:2.10.9
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
LABEL org.opencontainers.image.source="https://github.com/maxidrom2008/music-assistant-vk-edition"
RUN uv pip install --python /app/venv/bin/python --no-cache-dir 'vkpymusic==4.0.2' \
    && /app/venv/bin/python -c 'import vkpymusic; print("VKpyMusic dependency installed")'
COPY provider/vk_music /tmp/vk_music_provider
RUN SITE_PACKAGES="$(/app/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && mkdir -p "$SITE_PACKAGES/music_assistant/providers/vk_music" \
    && cp -a /tmp/vk_music_provider/. "$SITE_PACKAGES/music_assistant/providers/vk_music/" \
    && rm -rf /tmp/vk_music_provider \
    && /app/venv/bin/python -c 'import importlib, json, pathlib; m=importlib.import_module("music_assistant.providers.vk_music"); manifest=json.loads((pathlib.Path(m.__file__).with_name("manifest.json")).read_text()); assert manifest["domain"] == "vk_music"; assert callable(m.setup); import vkpymusic; import music_assistant.providers.vk_music.setup_flow; print("VK provider and setup flow import checks passed")' \
    && /app/venv/bin/python -c 'from types import SimpleNamespace; from music_assistant_models.enums import MediaType; from music_assistant.providers.vk_music import VKMusicProvider as P; x=SimpleNamespace(owner_id=1, playlist_id=2, access_key="", title="Collection", description="", photo=""); item_id=P._encode_collection_id(x, MediaType.PLAYLIST); data=P._decode_collection_id(item_id); assert (data["owner"], data["playlist"], data["key"], data["name"]) == ("1", "2", "", "Collection"); print("VK collection identifier round-trip check passed")'
