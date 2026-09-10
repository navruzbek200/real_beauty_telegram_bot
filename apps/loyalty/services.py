"""
Everything that moves points. Handlers, signals and the CRM all go through
here so the balance, the lifetime total and the tier can never disagree.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import F

from apps.loyalty.models import (
    LoyaltyAccount,
    LoyaltySettings,
    PointsTransaction,
    Reward,
    RewardRedemption,
)
from apps.users.models import TelegramUser

logger = logging.getLogger(__name__)

_TIER_LABEL_KEY = {
    LoyaltyAccount.Tier.BRONZE: "loyalty.tier.bronze",
    LoyaltyAccount.Tier.SILVER: "loyalty.tier.silver",
    LoyaltyAccount.Tier.GOLD: "loyalty.tier.gold",
    LoyaltyAccount.Tier.PLATINUM: "loyalty.tier.platinum",
}

REASON_LABEL_KEY = {
    PointsTransaction.Reason.REGISTRATION: "loyalty.reason.registration",
    PointsTransaction.Reason.PURCHASE: "loyalty.reason.purchase",
    PointsTransaction.Reason.FEEDBACK: "loyalty.reason.feedback",
    PointsTransaction.Reason.PROGRESS: "loyalty.reason.progress",
    PointsTransaction.Reason.REFERRAL: "loyalty.reason.referral",
    PointsTransaction.Reason.BIRTHDAY: "loyalty.reason.birthday",
    PointsTransaction.Reason.QUIZ: "loyalty.reason.quiz",
    PointsTransaction.Reason.REDEEM: "loyalty.reason.redeem",
    PointsTransaction.Reason.MANUAL: "loyalty.reason.manual",
}


@dataclass(frozen=True)
class TierInfo:
    """Where a customer stands, ready to render."""

    code: str
    label_key: str
    cashback: int
    lifetime: int
    next_code: str | None
    next_label_key: str | None
    next_at: int | None

    @property
    def remaining(self) -> int:
        if self.next_at is None:
            return 0
        return max(0, self.next_at - self.lifetime)

    @property
    def progress(self) -> float:
        """0.0–1.0 towards the next tier; 1.0 once there is no next tier."""
        if self.next_at is None or self.next_at <= 0:
            return 1.0
        return min(1.0, self.lifetime / self.next_at)


def tier_label_key(code: str) -> str:
    return _TIER_LABEL_KEY.get(code, "loyalty.tier.bronze")


def tier_for(lifetime: int, settings: LoyaltySettings | None = None) -> TierInfo:
    """Resolve a lifetime total into its tier and the gap to the next one."""
    conf = settings or LoyaltySettings.get()
    ladder = conf.tiers()

    index = 0
    for position, (_code, threshold, _cashback) in enumerate(ladder):
        if lifetime >= threshold:
            index = position
    code, _threshold, cashback = ladder[index]

    if index + 1 < len(ladder):
        next_code, next_at, _ = ladder[index + 1]
    else:
        next_code, next_at = None, None

    return TierInfo(
        code=code,
        label_key=tier_label_key(code),
        cashback=cashback,
        lifetime=lifetime,
        next_code=next_code,
        next_label_key=tier_label_key(next_code) if next_code else None,
        next_at=next_at,
    )


def get_account(user: TelegramUser) -> LoyaltyAccount:
    account, _ = LoyaltyAccount.objects.get_or_create(user=user)
    return account


@dataclass(frozen=True)
class AwardResult:
    """What `award` did — nothing at all is a normal, expected outcome."""

    awarded: bool
    points: int
    balance: int
    tier_changed: bool
    tier: TierInfo


def award(
    user: TelegramUser,
    reason: str,
    *,
    reference: str = "",
    points: int | None = None,
    note: str = "",
    notify: bool = True,
) -> AwardResult:
    """
    Credit points for `reason`, once per `reference`.

    A repeat call with the same reference is a no-op rather than an error: the
    callers are signals and retried tasks, and "already paid for this" is the
    normal case, not a failure.
    """
    settings = LoyaltySettings.get()
    amount = settings.points_for(reason) if points is None else points

    if not settings.is_enabled or amount <= 0:
        account = get_account(user)
        return AwardResult(
            False, 0, account.balance, False, tier_for(account.lifetime_points, settings)
        )

    get_account(user)  # outside the lock: creating and locking in one go races
    try:
        with transaction.atomic():
            account = LoyaltyAccount.objects.select_for_update().get(user=user)
            PointsTransaction.objects.create(
                user=user,
                points=amount,
                reason=reason,
                reference=reference,
                note=note,
            )
            before = tier_for(account.lifetime_points, settings)
            LoyaltyAccount.objects.filter(pk=account.pk).update(
                balance=F("balance") + amount,
                lifetime_points=F("lifetime_points") + amount,
            )
            account.refresh_from_db(fields=["balance", "lifetime_points"])
            after = tier_for(account.lifetime_points, settings)
            if after.code != account.tier:
                account.tier = after.code
                account.save(update_fields=["tier", "updated_at"])
    except IntegrityError:
        # Same reference already credited — the unique constraint doing its job.
        account = get_account(user)
        return AwardResult(
            False, 0, account.balance, False, tier_for(account.lifetime_points, settings)
        )

    tier_changed = after.code != before.code
    if notify:
        _notify(user, amount, reason, account.balance, after if tier_changed else None)
    return AwardResult(True, amount, account.balance, tier_changed, after)


def spend(
    user: TelegramUser, points: int, *, reason: str, note: str = "", reference: str = ""
) -> bool:
    """Deduct points if the balance covers it. Never lets a balance go negative."""
    with transaction.atomic():
        account = LoyaltyAccount.objects.select_for_update().filter(user=user).first()
        if account is None or account.balance < points:
            return False
        PointsTransaction.objects.create(
            user=user, points=-points, reason=reason, note=note, reference=reference
        )
        LoyaltyAccount.objects.filter(pk=account.pk).update(
            balance=F("balance") - points
        )
    return True


class RedeemError(Exception):
    """Raised when a reward cannot be claimed; `code` says why."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def redeem(user: TelegramUser, reward_id: int) -> RewardRedemption:
    """
    Turn points into a reward code.

    Stock, balance, the deduction and the code are all settled inside one
    transaction with the reward row locked — two customers racing for the last
    item must not both walk away with a code.
    """
    with transaction.atomic():
        reward = Reward.objects.select_for_update().filter(pk=reward_id).first()
        if reward is None or not reward.is_available:
            raise RedeemError("unavailable")

        account = LoyaltyAccount.objects.select_for_update().filter(user=user).first()
        balance = account.balance if account else 0
        if balance < reward.cost_points:
            raise RedeemError("not_enough")

        redemption = RewardRedemption.objects.create(
            user=user,
            reward=reward,
            code=_unique_code(reward.code_prefix),
            points_spent=reward.cost_points,
        )
        PointsTransaction.objects.create(
            user=user,
            points=-reward.cost_points,
            reason=PointsTransaction.Reason.REDEEM,
            reference=f"redemption:{redemption.pk}",
            note=reward.title[:200],
        )
        LoyaltyAccount.objects.filter(pk=account.pk).update(
            balance=F("balance") - reward.cost_points
        )
        if reward.stock is not None:
            Reward.objects.filter(pk=reward.pk).update(stock=F("stock") - 1)
    return redemption


def _unique_code(prefix: str) -> str:
    for _ in range(10):
        code = RewardRedemption.make_code(prefix)
        if not RewardRedemption.objects.filter(code=code).exists():
            return code
    raise RedeemError("unavailable")  # pragma: no cover — 36^6 collisions in a row


def _notify(
    user: TelegramUser,
    points: int,
    reason: str,
    balance: int,
    tier_up: TierInfo | None,
) -> None:
    """
    Tell the customer their points moved.

    Best-effort by design: a blocked chat or a Telegram hiccup must not roll
    back points the customer has genuinely earned.
    """
    if not user.telegram_id:
        return
    from bot.i18n import t
    from core.telegram import send_message

    lang = user.language
    text = t(
        "loyalty.earned",
        lang,
        points=points,
        reason=t(REASON_LABEL_KEY.get(reason, "loyalty.reason.manual"), lang),
        total=balance,
    )
    if tier_up is not None:
        text += "\n\n" + t(
            "loyalty.tier_up",
            lang,
            tier=t(tier_up.label_key, lang),
            cashback=tier_up.cashback,
        )
    try:
        send_message(user.telegram_id, text, parse_mode="HTML")
    except Exception:  # noqa: BLE001 — delivery is not worth losing points over
        logger.info("Could not notify %s about %+d points", user.telegram_id, points)
