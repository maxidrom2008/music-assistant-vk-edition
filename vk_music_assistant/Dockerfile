# Experimental wrapper around the official Music Assistant 2.10.9 image.
# The provider source is copied into the installed Music Assistant package.
FROM ghcr.io/music-assistant/server:2.10.9

# The official 2.10.9 server uses Python 3.14 in its virtual environment.
# Keep the provider folder in this repository at ./provider/vk_music.
COPY provider/vk_music /app/venv/lib/python3.14/site-packages/music_assistant/providers/vk_music
