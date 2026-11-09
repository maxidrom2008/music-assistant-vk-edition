# VK Music provider scaffold

This is only a loader/build scaffold. It intentionally exposes no search, browse,
library or playback features. Do not treat it as a working VK integration.

The next implementation step is to validate a permitted VK authentication flow
and catalog access, then add MA 2.10.9-compatible setup and media methods.
Never commit secrets or bypass DRM, subscription checks or access controls.
