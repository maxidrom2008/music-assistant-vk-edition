# VK Music provider

VK Music provider for Music Assistant Server 2.10.9.

## Setup

In Music Assistant open **Settings → Music Providers → Add provider → VK Music**. Enter an existing VK access token with the required VK Audio access and the matching client User-Agent. The token is entered through a secure setup field and stored in provider setup data. The integration never asks for the VK password, SMS/2FA code or browser cookies.

## Implemented

- Track search.
- Artist results derived from matching track results, with artist top-track and album lookup.
- Search results are limited to 30 items per media type in the current provider version.
- Album and playlist search.
- Browse the authenticated user's audio library and playlists with 100-item offset pagination.
- Browse recently played tracks through `vkpymusic` 4.0.2 `get_recent_songs_async` when VK exposes that catalog block.
- Retrieve tracks from selected albums and playlists.
- Resolve an audio URL immediately before playback and hand it to Music Assistant's normal HTTP stream pipeline.

## Limitations

Track objects supplied by `vkpymusic` currently expose title, artist, duration and VK IDs, but not a stable album or track artwork field. Album and playlist covers/descriptions are available when VK returns them. Recently played depends on VK's private catalog endpoint and may be unavailable for some tokens or accounts.

The VK audio API used by the dependency is unofficial and may change or reject a token. A paid VK Music subscription does not guarantee every endpoint or track is available to a third-party client. This repo's CI confirms dependency installation and provider/setup-flow import, but does not verify a live VK account or real playback. Access-denied, expired-session and unavailable-track responses must not be bypassed. No password capture, DRM circumvention or audio-file download is implemented.
