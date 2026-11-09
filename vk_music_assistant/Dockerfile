# Experimental wrapper around the official Music Assistant 2.10.9 image.
# Keep the base image and its entrypoint/data layout unchanged.
FROM ghcr.io/music-assistant/server:2.10.9

# Link the GHCR package to this source repository for package provenance/access management.
LABEL org.opencontainers.image.source="https://github.com/maxidrom2008/music-assistant-vk-edition"

# Copy the provider into a temporary location, then use the image's own Python
# interpreter to locate site-packages. Do not hardcode Python minor versions.
COPY provider/vk_music /tmp/vk_music_provider

RUN SITE_PACKAGES="$(/app/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && mkdir -p "$SITE_PACKAGES/music_assistant/providers/vk_music" \
    && cp -a /tmp/vk_music_provider/. "$SITE_PACKAGES/music_assistant/providers/vk_music/" \
    && rm -rf /tmp/vk_music_provider \
    && /app/venv/bin/python -c 'import importlib, json, pathlib; m=importlib.import_module("music_assistant.providers.vk_music"); manifest=json.loads((pathlib.Path(m.__file__).with_name("manifest.json")).read_text()); assert manifest["domain"] == "vk_music"; assert callable(m.setup); assert m.SUPPORTED_FEATURES == set(); print("VK provider import and manifest check passed")'
