# Experimental wrapper around the official Music Assistant 2.10.9 image.
# Keep the base image and its entrypoint/data layout unchanged.
FROM ghcr.io/music-assistant/server:2.10.9

# Copy the provider into a temporary location, then use the image's own Python
# interpreter to locate site-packages. Do not hardcode Python minor versions.
COPY provider/vk_music /tmp/vk_music_provider

RUN SITE_PACKAGES="$(/app/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && mkdir -p "$SITE_PACKAGES/music_assistant/providers/vk_music" \
    && cp -a /tmp/vk_music_provider/. "$SITE_PACKAGES/music_assistant/providers/vk_music/" \
    && rm -rf /tmp/vk_music_provider \
    && /app/venv/bin/python -c 'import importlib.util, sysconfig; p=sysconfig.get_path("purelib") + "/music_assistant/providers/vk_music/__init__.py"; s=importlib.util.spec_from_file_location("vk_music_check", p); assert s and s.loader; print("VK provider source copied:", p)'
