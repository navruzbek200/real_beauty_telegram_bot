"""
Bot-side access to the points/referral economy.

The economy itself lives in `apps.loyalty` (idempotent crediting, tiers,
cashback, redemption). This module is only the async, Telegram-facing skin over
it: it resolves chat ids to customers, awards the two points events the bot is
responsible for (finishing registration, bringing a friend), and renders a
customer's standing so a handler never has to touch the ORM directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.conf import settings

from apps.loyalty import services as loyalty
from apps.loyalty.models import LoyaltySettings, PointsTransaction, Reward
from apps.users.models import TelegramUser

logger = logging.getLogger(__name__)


def _bot_username() -> str:
    return getattr(settings, "BOT_USERNAME", "") or "RealBeautyBot"


def customer_invite_link(telegram_id: int) -> str:
    """The deep link a customer shares to earn referral points."""
    return f"https://t.me/{_bot_username()}?start=inv_{telegram_id}"


@dataclass(frozen=True)
class LoyaltySummary:
    enabled: bool
    balance: int
    lifetime: int
    tier_label_key: str
    cashback: int
    next_label_key: str | None
    remaining: int
    referral_points: int
    invite_link: str


@sync_to_async
def program_enabled() -> bool:
    return LoyaltySettings.get().is_enabled


@sync_to_async
def get_summary(telegram_id: int) -> LoyaltySummary | None:
    """A customer's balance, tier and personal invite link — or None if unknown."""
    user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
    if user is None:
        return None
    conf = LoyaltySettings.get()
    account = loyalty.get_account(user)
    info = loyalty.tier_for(account.lifetime_points, conf)
    return LoyaltySummary(
        enabled=conf.is_enabled,
        balance=account.balance,
        lifetime=account.lifetime_points,
        tier_label_key=info.label_key,
        cashback=info.cashback,
        next_label_key=info.next_label_key,
        remaining=info.remaining,
        referral_points=conf.points_referral,
        invite_link=customer_invite_link(telegram_id),
    )


def share_url(invite_link: str, text: str) -> str:
    """Telegram's native share sheet, pre-filled with the invite link + pitch."""
    return f"https://t.me/share/url?url={quote(invite_link)}&text={quote(text)}"


@sync_to_async
def award_registration(user_pk: int) -> None:
    """Credit the one-off "finished signing up" points. Idempotent per user."""
    user = TelegramUser.objects.filter(pk=user_pk).first()
    if user is None:
        return
    loyalty.award(
        user,
        PointsTransaction.Reason.REGISTRATION,
        reference=f"registration:{user_pk}",
    )


@sync_to_async
def award_referral(inviter_pk: int, new_user_pk: int) -> bool:
    """
    Credit the inviter for a friend who just finished registering.

    Guards the obvious abuse: you cannot refer yourself, the inviter has to be
    a real completed customer, and the reference ties the award to *this* new
    customer so a re-run of registration can never pay twice.

    On success the inviter gets a dedicated "your friend joined" message — the
    plain "+points" note alone read like nothing had happened, which is exactly
    why a shop testing referrals thought points were never credited.
    """
    if inviter_pk == new_user_pk:
        return False
    inviter = TelegramUser.objects.filter(
        pk=inviter_pk,
        registration_status=TelegramUser.RegistrationStatus.COMPLETED,
    ).first()
    if inviter is None:
        return False
    result = loyalty.award(
        inviter,
        PointsTransaction.Reason.REFERRAL,
        reference=f"referral:{new_user_pk}",
        notify=False,  # replaced by the clearer, referral-specific message below
    )
    if result.awarded and inviter.telegram_id:
        from bot.i18n import t
        from core.telegram import send_message

        try:
            send_message(
                inviter.telegram_id,
                t("loyalty.referral_joined", inviter.language, points=result.points),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001 — a lost message must not undo the points
            logger.info("Could not notify inviter %s of a referral", inviter.telegram_id)
    return result.awarded


@sync_to_async
def resolve_inviter_pk(telegram_id: int) -> int | None:
    """Turn an `inv_<telegram_id>` payload into the inviter's customer pk."""
    inviter = TelegramUser.objects.filter(
        telegram_id=telegram_id,
        registration_status=TelegramUser.RegistrationStatus.COMPLETED,
    ).first()
    return inviter.pk if inviter else None


@sync_to_async
def list_active_rewards() -> list[Reward]:
    return [r for r in Reward.objects.all() if r.is_available]


@sync_to_async
def get_reward(reward_id: int) -> Reward | None:
    return Reward.objects.filter(pk=reward_id).first()


@dataclass(frozen=True)
class RedeemOutcome:
    ok: bool
    code: str | None = None
    error: str | None = None


@sync_to_async
def redeem_reward(telegram_id: int, reward_id: int) -> RedeemOutcome:
    user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
    if user is None:
        return RedeemOutcome(False, error="unavailable")
    try:
        redemption = loyalty.redeem(user, reward_id)
    except loyalty.RedeemError as exc:
        return RedeemOutcome(False, error=exc.code)
    return RedeemOutcome(True, code=redemption.code)
