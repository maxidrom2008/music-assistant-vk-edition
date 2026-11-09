# Music Assistant — VK Edition

> Work in progress. This repository does not yet contain a working VK Music provider or an installable Home Assistant app.

A separate Home Assistant OS app build of Music Assistant Server, initially targeting **2.10.9 / amd64**, with an additional VK Music music-source provider. The stock Music Assistant app and its data must remain untouched during development and testing.

## Goals

- Search VK Music tracks, artists, albums and playlists.
- Browse a user's VK Music library where the account/API permits it.
- Resolve and play tracks through Music Assistant's normal stream pipeline.
- Keep credentials in Music Assistant's encrypted provider setup data; never commit tokens, cookies, passwords or device identifiers.
- Package the server as a separate HAOS app/repository so it can be tested side-by-side before any migration.

## Compatibility baseline

The provider API must match the official Music Assistant **2.10.9** source tree. The provider will follow that release's `_demo_music_provider` template and its setup-flow contract. The official 2.10.9 provider tree does not include a VK provider.

The HAOS app packaging will be based on the official `music-assistant/home-assistant-addon` configuration, with a separate app slug and data directory. The official app's host-networking requirements and permissions need to be preserved where necessary for player discovery.

## VK API status and limitations

VK's music-catalog endpoints are not documented as a public, stable API. Third-party technical documentation describes internal endpoints used by VK clients, but those interfaces, authentication requirements, stream URLs and subscription checks can change without notice. This project must not bypass DRM, subscription checks, geographic restrictions or other access controls. A valid account/subscription does not guarantee that an unofficial client is supported by VK.

Before implementing playback, verify that permitted account access can provide:
1. catalog search and metadata;
2. playlist/library access;
3. a playable stream URL for entitled tracks;
4. stable error handling for expired sessions and unavailable content.

If only metadata works, the provider must not advertise playback as supported.

## Development stages

1. Verify the exact MA 2.10.9 provider loader, manifest, setup flow and stream contract.
2. Validate the VK authentication/API approach without placing credentials in source code or CI.
3. Implement and test search and metadata.
4. Implement stream resolution only if it works without bypassing access controls.
5. Build a separate amd64 HAOS app image and test it without changing the stock app or its data.
6. Document backup, install, rollback and upgrade steps.

## Security

- Never put secrets in Git, issues, logs, screenshots or GitHub Actions artifacts.
- Do not request or store a VK password, SMS/2FA code or browser cookies in this repository.
- Use only the minimum account data needed and keep all authentication local to the Music Assistant instance.
- Keep the stock Music Assistant app installed and backed up until the custom app passes testing.

## Current status

- [x] Private project repository created.
- [x] MA Server 2.10.9 provider template inspected.
- [x] Official HAOS app configuration inspected.
- [ ] VK authentication and API feasibility verified.
- [ ] VK provider implemented.
- [ ] Separate HAOS app image built and tested.
