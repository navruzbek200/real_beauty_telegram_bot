from __future__ import annotations

import secrets

from django.core.cache import cache

from . import eskiz

_CODE_TTL = 5 * 60  # how long a code stays valid
_RESEND_COOLDOWN = 60  # minimum gap between two sends to the same number
_MAX_ATTEMPTS = 5  # wrong-code guesses allowed before the code is burned
_MAX_SENDS_PER_DAY = 5  # cap on how many SMS one number can trigger per day
_DAY = 24 * 60 * 60


class OtpCooldown(Exception):
    """A code was already sent recently; wait before requesting another."""


class OtpRateLimited(Exception):
    """Too many codes requested for this number today."""


class OtpInvalid(Exception):
    """Code missing, expired, or attempts exhausted."""


def _code_key(phone: str) -> str:
    return f"otp:code:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"otp:cooldown:{phone}"


def _attempts_key(phone: str) -> str:
    return f"otp:attempts:{phone}"


def _sends_key(phone: str) -> str:
    return f"otp:sends:{phone}"


def generate_and_send_code(phone_number: str) -> None:
    if cache.get(_cooldown_key(phone_number)):
        raise OtpCooldown

    sends = cache.get(_sends_key(phone_number), 0)
    if sends >= _MAX_SENDS_PER_DAY:
        raise OtpRateLimited

    code = f"{secrets.randbelow(900000) + 100000}"
    cache.set(_code_key(phone_number), code, _CODE_TTL)
    cache.set(_cooldown_key(phone_number), True, _RESEND_COOLDOWN)
    cache.delete(_attempts_key(phone_number))
    # First send in the window creates the counter; increments after keep the
    # original TTL rather than resetting the 24h clock on every SMS.
    if sends == 0:
        cache.set(_sends_key(phone_number), 1, _DAY)
    else:
        try:
            cache.incr(_sends_key(phone_number))
        except ValueError:
            cache.set(_sends_key(phone_number), 1, _DAY)

    eskiz.send_sms(
        phone_number,
        f"Real Beauty tasdiqlash kodi: {code}. Hech kimga aytmang.",
    )


def verify_code(phone_number: str, code: str) -> bool:
    """Returns True and burns the code on a match; raises OtpInvalid otherwise."""
    # Guard before compare_digest: non-ASCII input makes it raise TypeError,
    # turning a bad guess into a 500.
    if not code.isascii() or not code.isdigit():
        raise OtpInvalid("wrong_code")
    stored = cache.get(_code_key(phone_number))
    if stored is None:
        raise OtpInvalid("expired_or_missing")

    attempts_key = _attempts_key(phone_number)
    attempts = cache.get(attempts_key, 0)
    if attempts >= _MAX_ATTEMPTS:
        cache.delete(_code_key(phone_number))
        raise OtpInvalid("too_many_attempts")

    if not secrets.compare_digest(stored, code):
        try:
            cache.incr(attempts_key)
        except ValueError:
            cache.set(attempts_key, 1, _CODE_TTL)
        raise OtpInvalid("wrong_code")

    cache.delete(_code_key(phone_number))
    cache.delete(attempts_key)
    return True
