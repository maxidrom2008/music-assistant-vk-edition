# VK Music provider

VK Music provider for Music Assistant Server 2.10.9.

## Setup

In Music Assistant open **Settings → Music Providers → Add provider → VK Music**. Enter an existing VK access token with the required VK Audio access and the matching client User-Agent. The token is entered through a secure setup field and stored in provider setup data. The integration never asks for the VK password, SMS/2FA code or browser cookies.

## Implemented

- Track search.
- Artist results derived from matching track results, with artist top-track and album lookup.
- Album and playlist search.
- Browse the authenticated user's audio library (first 100 tracks) and playlists.
- Retrieve tracks from selected albums and playlists.
- Resolve an audio URL immediately before playback and hand it to Music Assistant's normal HTTP stream pipeline.

## Limitations

The VK audio API used by the dependency is unofficial and may change or reject a token. A paid VK Music subscription does not guarantee every endpoint or track is available to a third-party client. This repo's CI confirms dependency installation and provider/setup-flow import, but does not verify a live VK account or real playback. Access-denied, expired-session and unavailable-track responses must not be bypassed. No password capture, DRM circumvention or audio-file download is implemented.
