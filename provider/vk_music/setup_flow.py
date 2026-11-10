"""Interactive VK authorization flow for Music Assistant."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from music_assistant.models.setup_flow import AbortFlow, SetupFlowError
from music_assistant_models.config_entries import ConfigEntry
from music_assistant_models.enums import ConfigEntryType
from vkpymusic import Service, VkMobileClient

from . import CONF_TOKEN, CONF_USER_AGENT
from .auth import VKAuthChallenge, VKAuthError, request_vk_token, request_vk_validation

if TYPE_CHECKING:
    from music_assistant.models.setup_flow import SetupSession


_CREDENTIAL_ENTRIES = (
    ConfigEntry(
        key="login",
        type=ConfigEntryType.STRING,
        label="Телефон или email VK",
        required=True,
    ),
    ConfigEntry(
        key="password",
        type=ConfigEntryType.SECURE_STRING,
        label="Пароль VK",
        required=True,
    ),
)


class _InvalidCredentials(Exception):
    """VK rejected the supplied login or password."""


class _RateLimited(Exception):
    """VK temporarily blocked further login attempts."""


class _BrowserCaptchaRequired(Exception):
    """VK returned its browser-based CAPTCHA flow."""


def _validation_mode(validation_type: str) -> str:
    """Classify the challenge without assuming a specific delivery channel."""
    value = validation_type.casefold()
    if any(part in value for part in ("push", "max", "approve", "confirm", "message")):
        return "approval_or_code"
    return "code"


async def _prompt_validation(
    session: SetupSession,
    details: dict[str, Any],
    *,
    errors: dict[str, str] | None = None,
) -> tuple[str | None, bool]:
    """Ask for a code, or allow a code/push-style approval for unknown methods."""
    validation_type = str(details.get("validation_type") or "")
    phone_mask = str(details.get("phone_mask") or "").strip()

    if validation_type == "2fa_sms":
        label = "Код из SMS"
        description = f"VK отправил код на {phone_mask}." if phone_mask else "Введите код, который отправил VK."
    elif validation_type == "2fa_callreset":
        label = "Последние 4 цифры входящего звонка"
        description = "Введите последние четыре цифры номера входящего звонка от VK."
    elif validation_type == "2fa_app":
        label = "Код из приложения VK"
        description = "Введите одноразовый код из приложения-аутентификатора VK."
    else:
        label = "Код подтверждения"
        description = (
            f"VK выбрал способ подтверждения «{validation_type}». "
            "Введите присланный код или подтвердите вход в приложении и отметьте это ниже."
            if validation_type
            else "Введите код VK или подтвердите вход в приложении."
        )

    mode = _validation_mode(validation_type)
    entries = [
        ConfigEntry(
            key="code",
            type=ConfigEntryType.SECURE_STRING,
            label=label,
            description=description,
            required=mode == "code",
        )
    ]
    if mode == "approval_or_code":
        entries.append(
            ConfigEntry(
                key="approved",
                type=ConfigEntryType.BOOLEAN,
                label="Я подтвердил вход в VK или MAX",
                description="Отметьте после подтверждения запроса на другом устройстве.",
                default_value=False,
                required=False,
            )
        )

    current_errors = errors
    while True:
        values = await session.form(
            entries,
            step_id="verification",
            errors=current_errors,
            last_step=False,
        )
        code = str(values.get("code") or "").strip() or None
        approved = bool(values.get("approved", False))
        if mode == "code" or code or approved:
            return code, approved
        current_errors = {
            "base": "Введите код или подтвердите вход в приложении."
        }


async def _authenticate(session: SetupSession, login: str, password: str) -> str:
    """Drive VK's challenge/response loop until a token is issued."""
    code: str | None = None
    captcha_sid: str | None = None
    captcha_answer: str | None = None
    pending_validation: dict[str, Any] | None = None
    requested_validation_sid: str | None = None

    while True:
        try:
            return await request_vk_token(
                login,
                password,
                code=code,
                captcha_sid=captcha_sid,
                captcha_answer=captcha_answer,
            )
        except VKAuthChallenge as challenge:
            details = challenge.details
            error = str(details.get("error") or "")
            error_type = str(details.get("error_type") or "")

            # A challenge response consumes the submitted code/captcha answer.
            code = None
            captcha_sid = None
            captcha_answer = None

            if error == "invalid_client":
                raise _InvalidCredentials from challenge
            if error == "9;Flood control" or error_type == "password_bruteforce_attempt":
                raise _RateLimited from challenge

            if error == "need_validation":
                validation_type = str(details.get("validation_type") or "")
                sid = str(details.get("validation_sid") or "")
                pending_validation = details

                # Match TokenReceiver's behavior: ask VK to start the
                # challenge for every validation_sid, regardless of channel.
                if sid and sid != requested_validation_sid:
                    await request_vk_validation(sid)
                    requested_validation_sid = sid

                code, _approved = await _prompt_validation(session, details)
                continue

            if error == "invalid_request" and pending_validation is not None:
                code, _approved = await _prompt_validation(
                    session,
                    pending_validation,
                    errors={"code": "VK не принял код. Проверьте его и попробуйте ещё раз."},
                )
                continue

            if error == "need_captcha":
                captcha_sid_value = details.get("captcha_sid")
                captcha_img = details.get("captcha_img")
                if captcha_sid_value and captcha_img:
                    captcha_entries = [
                        ConfigEntry(
                            key="captcha_image",
                            type=ConfigEntryType.IMAGE,
                            label="Капча VK",
                            default_value=str(captcha_img),
                            required=False,
                        ),
                        ConfigEntry(
                            key="captcha_answer",
                            type=ConfigEntryType.STRING,
                            label="Ответ на капчу",
                            required=True,
                        ),
                    ]
                    values = await session.form(
                        captcha_entries,
                        step_id="captcha",
                        last_step=False,
                    )
                    captcha_sid = str(captcha_sid_value)
                    captcha_answer = str(values.get("captcha_answer") or "").strip()
                    continue

                # New VK ID CAPTCHA returns redirect_uri and expects a
                # browser-generated success_token. It is not a text CAPTCHA.
                raise _BrowserCaptchaRequired from challenge

            raise VKAuthError(
                f"VK returned an unsupported authorization response: {error or error_type or 'unknown'}"
            ) from challenge


async def run_setup(session: SetupSession) -> None:
    """Collect temporary credentials, complete VK challenges, and save only the token."""
    errors: dict[str, str] | None = None

    while True:
        values = await session.form(
            list(_CREDENTIAL_ENTRIES),
            step_id="credentials",
            errors=errors,
            last_step=False,
        )
        login = str(values.get("login") or "").strip()
        password = str(values.get("password") or "")

        try:
            if not login or not password:
                errors = {"base": "Введите логин и пароль VK."}
                continue

            try:
                token = await _authenticate(session, login, password)
            except _InvalidCredentials:
                errors = {"base": "VK не принял логин или пароль. Проверьте данные и попробуйте ещё раз."}
                continue
            except _RateLimited as err:
                raise AbortFlow("rate_limited") from err
            except _BrowserCaptchaRequired:
                # VK ID CAPTCHA needs a browser-generated success_token. Do not
                # launch Selenium on the HA host; retain a manual-token fallback.
                fallback = await session.form(
                    [
                        ConfigEntry(
                            key="manual_token",
                            type=ConfigEntryType.SECURE_STRING,
                            label="VK access token",
                            required=True,
                        )
                    ],
                    step_id="token_fallback",
                    last_step=True,
                )
                token = str(fallback.get("manual_token") or "").strip()
            except VKAuthError as err:
                raise AbortFlow("auth_failed") from err

            user_agent = VkMobileClient.user_agent
            service = Service(user_agent=user_agent, token=token)
            if not await service.is_token_valid_async():
                raise AbortFlow("token_validation_failed")

            try:
                # Password and login are deliberately excluded from setup_data.
                await session.finish(
                    {
                        CONF_TOKEN: token,
                        CONF_USER_AGENT: user_agent,
                    }
                )
                return
            except SetupFlowError as err:
                errors = {"base": str(err)}
        finally:
            # These values are short-lived inputs; only the access token and
            # client User-Agent are persisted by session.finish().
            password = ""
