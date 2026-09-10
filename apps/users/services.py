from __future__ import annotations

from django.utils import timezone

from .models import TelegramLoginSession, TelegramUser


class InvalidPhoneNumber(ValueError):
    pass


def register_app_user(*, full_name: str, phone_number: str) -> TelegramUser:
    """
    Record (or update) a mobile-app signup as a customer card.

    Matched by phone_tail against the same pool of cards the Telegram bot
    reads from, so a person who later opens the bot with this number links
    onto this exact card instead of getting a duplicate — the phone_tail
    matching is what the bot's own /start flow already relies on.
    """
    normalized = TelegramUser.normalize_phone(phone_number)
    if normalized is None:
        raise InvalidPhoneNumber("Telefon raqam noto'g'ri formatda")

    tail = TelegramUser.phone_tail_of(normalized)
    existing = TelegramUser.objects.filter(phone_tail=tail).first()
    if existing is not None:
        # A card that already has a name (typed by staff, or completed via the
        # bot) knows more about this person than a bare app signup does —
        # don't clobber it. Only fill in what's missing.
        if full_name and not existing.full_name:
            existing.full_name = full_name
            existing.save(update_fields=["full_name"])
        return existing

    return TelegramUser.objects.create(
        full_name=full_name,
        phone_number=normalized,
        source=TelegramUser.RegistrationSource.APP,
        registration_status=TelegramUser.RegistrationStatus.PENDING,
    )


def create_login_session() -> TelegramLoginSession:
    """Step 1 of app login-via-Telegram: a fresh, pending, single-use token."""
    # Opportunistic cleanup — cheap at this volume, and means no separate
    # Celery beat entry is needed just to keep this table from growing.
    TelegramLoginSession.objects.filter(expires_at__lt=timezone.now()).delete()
    return TelegramLoginSession.objects.create()


def get_login_session(token: str) -> TelegramLoginSession | None:
    """A still-live session for this token, or None (missing/expired)."""
    session = TelegramLoginSession.objects.filter(token=token).first()
    if session is None or session.is_expired:
        return None
    return session


def consume_confirmed_login_session(token: str) -> TelegramUser | None:
    """
    The confirmed customer for this token, deleting the session so the same
    token can never be redeemed twice.

    Returns None for anything that isn't a live, confirmed session — missing,
    expired, or still pending — so the caller can't tell those apart from the
    token value alone.
    """
    session = TelegramLoginSession.objects.filter(token=token).select_related("user").first()
    if session is None:
        return None
    if session.is_expired:
        session.delete()
        return None
    if session.status != TelegramLoginSession.Status.CONFIRMED or session.user is None:
        return None
    user = session.user
    session.delete()
    return user


def confirm_login_session(token: str, user_id: int) -> bool:
    """
    Mark a pending session confirmed by this customer.

    Called either from the bot's confirm button (an already-registered
    customer) or right after registration finishes for someone who opened the
    deep link cold — see bot/handlers/auth.py. A no-op (returns False) for a
    token that's missing, expired, or already confirmed, so a stale button
    tap or a double-run of registration can't do anything.
    """
    updated = TelegramLoginSession.objects.filter(
        token=token,
        status=TelegramLoginSession.Status.PENDING,
        expires_at__gt=timezone.now(),
    ).update(
        status=TelegramLoginSession.Status.CONFIRMED,
        user_id=user_id,
        confirmed_at=timezone.now(),
    )
    return bool(updated)
