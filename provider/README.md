# VK Music provider — development notes

This directory is intentionally not populated with executable provider code yet.

Music Assistant 2.10.9 discovers provider manifests by scanning subdirectories of
`music_assistant/providers`. The custom image copies a future `vk_music/` provider
folder into that exact installed package directory.

Before adding a manifest or enabling search/playback, verify the VK account
authentication and permitted catalog/stream access. Do not commit credentials,
cookies, tokens or device identifiers. Do not bypass DRM or subscription checks.
