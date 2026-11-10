# VK Music provider

VK Music provider for Music Assistant Server 2.10.9.

## Setup

In Music Assistant open **Settings → Music Providers → Add provider → VK Music**. Enter your VK phone/email and password. The setup flow then follows the challenge returned by VK: SMS code, last digits of a verification call, an app code, or a code/device approval for other methods. On success, the flow stores only the VK access token and the User-Agent supplied by vkpymusic's mobile client. The password and one-time codes are not persisted.

## Implemented

- Track search.
- Artist results derived from matching track results, with artist top-track and album lookup.
- Search results are limited to 30 items per media type in the current provider version.
- Album and playlist search.
- Browse the authenticated user's audio library and playlists with 100-item offset pagination.
- Browse recently played tracks through `vkpymusic` 4.0.2 `get_recent_songs_async` when VK exposes that catalog block.
- Retrieve tracks from selected albums and playlists.
- Resolve an audio URL immediately before playback and hand it to Music Assistant's normal HTTP stream pipeline.

## Browsing behavior

Personal tracks and playlist collections are fetched in pages of up to 100 items. A next-page folder is shown when a full page is returned. Recently played uses the `Service.get_recent_songs_async()` catalog method shipped by `vkpymusic` 4.0.2; the private VK catalog may return an empty list or an access error depending on the account.

## Authorization behavior

The setup flow uses vkpymusic 4.0.2's async request transport, but not its TokenReceiver handlers: those open Selenium/Chrome for CAPTCHA and set `force_sms=1`. The VK request no longer forces SMS; the flow follows the returned `validation_type` and repeats the request after each user response.

The older CAPTCHA response containing `captcha_sid` and `captcha_img` can be shown as an image with an answer field. The newer browser-based VK ID CAPTCHA returns `redirect_uri` and requires a browser-generated `success_token`. This flow currently reports that challenge as unsupported rather than starting a headless or hidden browser. A successful live login has not yet been verified against the user's VK account.

## Limitations

Track objects supplied by `vkpymusic` currently expose title, artist, duration and VK IDs, but not a stable album or track artwork field. Album and playlist covers/descriptions are available when VK returns them. Recently played depends on VK's private catalog endpoint and may be unavailable for some tokens or accounts.

The VK audio API used by the dependency is unofficial and may change or reject a token. A paid VK Music subscription does not guarantee every endpoint or track is available to a third-party client. This repo's CI confirms dependency installation and provider/setup-flow import, but does not verify a live VK account or real playback. Access-denied, expired-session and unavailable-track responses must not be bypassed. No password capture, DRM circumvention or audio-file download is implemented.
