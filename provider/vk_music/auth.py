"""VK OAuth helpers for the interactive Music Assistant setup flow.

The helpers deliberately avoid vkpymusic.TokenReceiver: its default handlers
open Selenium/Chrome for CAPTCHA and force SMS for 2FA. The setup flow owns
the interaction instead, while the library still supplies the VK request
builders and async transport.
"""
from __future__ import annotations

from typing import Any

from vkpymusic import VkMobileClient
from vkpymusic.vk_api import (
    VkApiException,
    VkApiRequestBuilder,
    make_request_async,
)


class VKAuthChallenge(Exception):
    """An interactive challenge returned by the VK OAuth endpoint."""

    def __init__(self, details: dict[str, Any]) -> None:
        """Store the raw challenge details for the setup flow."""
        super().__init__(str(details.get("error") or "VK authentication challenge"))
        self.details = details


class VKAuthError(Exception):
    """A terminal or unsupported VK authorization error."""


async def request_vk_token(
    login: str,
    password: str,
    *,
    code: str | None = None,
    captcha_sid: str | None = None,
    captcha_answer: str | None = None,
    captcha_success_token: str | None = None,
) -> str:
    """Make one VK password-grant request and return its access token.

    Unlike vkpymusic 4.0.2 TokenReceiver, this request does not set
    force_sms=1. VK can therefore return the validation method it selected.
    """
    request = VkApiRequestBuilder.build_req_auth(
        login=login,
        password=password,
        client=VkMobileClient,
        code=code,
    )
    # vkpymusic 4.0.2 hard-codes force_sms=1 in build_req_auth().
    # Remove that preference so VK can choose the appropriate challenge.
    request.params.pop("force_sms", None)

    if captcha_sid and captcha_answer:
        # Legacy image CAPTCHA shape.
        request.params["captcha_sid"] = captcha_sid
        request.params["captcha_key"] = captcha_answer
    if captcha_success_token:
        # New VK ID CAPTCHA shape. The current setup flow does not obtain this
        # value yet, but keeping the request helper ready avoids a second fork.
        request.params["success_token"] = captcha_success_token

    try:
        response = await make_request_async(request)
    except VkApiException as err:
        details = err.details if isinstance(err.details, dict) else {}
        if details.get("error"):
            raise VKAuthChallenge(details) from err
        raise VKAuthError(f"VK API rejected the authentication request ({err.error_code})") from err

    token = response.data.get("access_token")
    if not token:
        raise VKAuthError("VK returned a response without an access token")
    return str(token)


async def request_vk_validation(sid: str) -> dict[str, Any]:
    """Ask VK to send/start the selected phone-based validation challenge."""
    request = VkApiRequestBuilder.build_req_2fa_code(
        client=VkMobileClient,
        sid=sid,
    )
    try:
        response = await make_request_async(request)
    except VkApiException as err:
        details = err.details if isinstance(err.details, dict) else {}
        message = details.get("error_msg") or details.get("error") or err.error_msg
        raise VKAuthError(f"VK could not start the selected verification method: {message}") from err
    return response.data if isinstance(response.data, dict) else {}
