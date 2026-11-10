# VK Music provider

Adds VK track search and authorized playback to Music Assistant 2.10.9.

## Setup
Add **VK Music** in Settings → Music Providers. Supply an existing VK access token permitted to access VK audio and its matching client User-Agent. Music Assistant stores secure setup values in its provider configuration. This integration never asks for a VK password or performs password/2FA login.

A paid subscription does not guarantee that every token type or API method is accepted by VK.

## Current scope
- Search tracks.
- Resolve a fresh audio URL at playback time.
- Return stream details to Music Assistant; audio URLs are not embedded in catalog results.

Artist/album/playlist browsing and library sync are not advertised yet. VK may deny access to individual tracks or return expiring URLs. No DRM, subscription, region, or access-control bypass is implemented; this provider does not download or store audio.
