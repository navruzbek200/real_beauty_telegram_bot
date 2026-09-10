"""
The loyalty program: points in, points out, and the tier in between.

Shape of the thing:

* **Earning** — every action the shop wants more of (buying, rating, sending
  a result photo, bringing a friend, taking the skin quiz) credits points. How
  many is not hard-coded; it is a row in `LoyaltySettings` so the shop can tune
  the economy without a deploy.
* **Tier** — four levels driven by *lifetime* points, never by the spendable
  balance. If tiers dropped when somebody redeemed a reward, spending points
  would be a punishment and nobody would do it.
* **Spending** — points buy a `Reward`, which hands the customer a one-off
  promo code to show at the till. Nothing is deducted without a code coming
  back, and nothing is issued without points being deducted: both happen in
  one transaction.
* **Cashback** — the tier's percentage. Deliberately informational: the till
  is offline, so the bot's job is to tell the customer (and the seller) what
  they have earned, not to move money.
"""

from __future__ import annotations

import secrets
import string
from typing import Any

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone


class LoyaltySettings(models.Model):
    """Singleton — the whole points economy on one screen."""

    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Bonus dasturi yoqilgan",
        help_text="O'chirilsa botdagi «Bonuslarim» bo'limi ko'rinmaydi va "
        "ball yig'ilmaydi.",
    )

    points_registration = models.PositiveSmallIntegerField(
        default=50,
        verbose_name="Ro'yxatdan o'tgani uchun",
        help_text="Mijoz botda ro'yxatdan o'tishni tugatganda beriladi.",
    )
    points_purchase = models.PositiveSmallIntegerField(
        default=100,
        verbose_name="Har bir xarid uchun",
        help_text="Mijozga mahsulot biriktirilganda beriladi.",
    )
    points_feedback = models.PositiveSmallIntegerField(
        default=30, verbose_name="Mahsulotga baho bergani uchun"
    )
    points_progress = models.PositiveSmallIntegerField(
        default=50, verbose_name="Oldin/keyin rasmi uchun"
    )
    points_referral = models.PositiveSmallIntegerField(
        default=150,
        verbose_name="Do'stini taklif qilgani uchun",
        help_text="Taklif qilingan do'st ro'yxatdan o'tib bo'lgach beriladi.",
    )
    points_birthday = models.PositiveSmallIntegerField(
        default=200, verbose_name="Tug'ilgan kun sovg'asi"
    )
    points_quiz = models.PositiveSmallIntegerField(
        default=20, verbose_name="Teri testini topshirgani uchun"
    )

    # Tier thresholds are lifetime totals; bronze always starts at 0. Cashback
    # doubles as the "e'lon qilinadigan chegirma" (announced discount) the
    # shop shows off per tier — capped at 100% since anything past that is a
    # typo, not a promotion.
    bronze_cashback = models.PositiveSmallIntegerField(
        default=3,
        validators=[MaxValueValidator(100)],
        verbose_name="Bronza keshbek / chegirma (%)",
    )
    silver_from = models.PositiveIntegerField(
        default=1000, verbose_name="Kumush darajasi (balldan)"
    )
    silver_cashback = models.PositiveSmallIntegerField(
        default=5,
        validators=[MaxValueValidator(100)],
        verbose_name="Kumush keshbek / chegirma (%)",
    )
    gold_from = models.PositiveIntegerField(
        default=3000, verbose_name="Oltin darajasi (balldan)"
    )
    gold_cashback = models.PositiveSmallIntegerField(
        default=7,
        validators=[MaxValueValidator(100)],
        verbose_name="Oltin keshbek / chegirma (%)",
    )
    platinum_from = models.PositiveIntegerField(
        default=7000, verbose_name="Platina darajasi (balldan)"
    )
    platinum_cashback = models.PositiveSmallIntegerField(
        default=10,
        validators=[MaxValueValidator(100)],
        verbose_name="Platina keshbek / chegirma (%)",
    )

    class Meta:
        verbose_name = "Bonus dasturi sozlamalari"
        verbose_name_plural = "Bonus dasturi sozlamalari"

    def clean(self) -> None:
        """
        Thresholds must climb: bronze(0) < silver < gold < platinum.

        `tier_for` picks a tier by scanning this ladder in a fixed order and
        keeping the last one the balance clears — if the admin ever sets, say,
        Gold's threshold below Silver's, a 700-point customer would jump
        straight past Silver into Gold, and everyone above Silver would sit in
        whichever tier happens to have the lowest number. Free configuration
        is the point; a config that silently breaks the ladder isn't.
        """
        from django.core.exceptions import ValidationError

        if not (0 < self.silver_from < self.gold_from < self.platinum_from):
            raise ValidationError(
                "Darajalar ortib borishi kerak: Kumush < Oltin < Platina "
                f"(hozir: {self.silver_from} / {self.gold_from} / "
                f"{self.platinum_from})."
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "LoyaltySettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def points_for(self, reason: str) -> int:
        return {
            PointsTransaction.Reason.REGISTRATION: self.points_registration,
            PointsTransaction.Reason.PURCHASE: self.points_purchase,
            PointsTransaction.Reason.FEEDBACK: self.points_feedback,
            PointsTransaction.Reason.PROGRESS: self.points_progress,
            PointsTransaction.Reason.REFERRAL: self.points_referral,
            PointsTransaction.Reason.BIRTHDAY: self.points_birthday,
            PointsTransaction.Reason.QUIZ: self.points_quiz,
        }.get(reason, 0)

    def tiers(self) -> list[tuple[str, int, int]]:
        """(code, lifetime threshold, cashback %) ordered low to high."""
        return [
            (LoyaltyAccount.Tier.BRONZE, 0, self.bronze_cashback),
            (LoyaltyAccount.Tier.SILVER, self.silver_from, self.silver_cashback),
            (LoyaltyAccount.Tier.GOLD, self.gold_from, self.gold_cashback),
            (
                LoyaltyAccount.Tier.PLATINUM,
                self.platinum_from,
                self.platinum_cashback,
            ),
        ]

    def __str__(self) -> str:
        return "Bonus dasturi sozlamalari"


class LoyaltyAccount(models.Model):
    """One customer's balance, lifetime total and current tier."""

    class Tier(models.TextChoices):
        BRONZE = "bronze", "Bronza"
        SILVER = "silver", "Kumush"
        GOLD = "gold", "Oltin"
        PLATINUM = "platinum", "Platina"

    user = models.OneToOneField(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="loyalty",
        verbose_name="Mijoz",
    )
    balance = models.IntegerField(default=0, verbose_name="Ball balansi")
    # Never goes down — spending points must not cost somebody their tier.
    lifetime_points = models.PositiveIntegerField(
        default=0, verbose_name="Jami yig'ilgan ball"
    )
    tier = models.CharField(
        max_length=12,
        choices=Tier.choices,
        default=Tier.BRONZE,
        verbose_name="Daraja",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Bonus hisobi"
        verbose_name_plural = "Bonus hisoblari"
        ordering = ["-lifetime_points"]

    def __str__(self) -> str:
        return f"{self.user} — {self.balance} ball ({self.get_tier_display()})"


class PointsTransaction(models.Model):
    """
    Every movement of points, positive or negative.

    `reference` is what makes crediting idempotent: the purchase, feedback or
    photo that caused it. A retried save, a double-tapped button or a re-run
    task hits the unique constraint instead of paying twice.
    """

    class Reason(models.TextChoices):
        REGISTRATION = "registration", "Ro'yxatdan o'tish"
        PURCHASE = "purchase", "Xarid"
        FEEDBACK = "feedback", "Mahsulotga baho"
        PROGRESS = "progress", "Natija rasmi"
        REFERRAL = "referral", "Do'st taklifi"
        BIRTHDAY = "birthday", "Tug'ilgan kun"
        QUIZ = "quiz", "Teri testi"
        REDEEM = "redeem", "Sovg'aga almashtirildi"
        MANUAL = "manual", "Admin tuzatishi"

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="points_transactions",
        verbose_name="Mijoz",
    )
    points = models.IntegerField(
        verbose_name="Ball",
        help_text="Musbat — qo'shiladi, manfiy — ayiriladi.",
    )
    reason = models.CharField(
        max_length=16, choices=Reason.choices, verbose_name="Sabab"
    )
    reference = models.CharField(max_length=64, blank=True, editable=False)
    note = models.CharField(max_length=200, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        verbose_name = "Ball harakati"
        verbose_name_plural = "Ball harakatlari"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "reason", "reference"],
                condition=~models.Q(reference=""),
                name="uniq_points_reference",
            )
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user} {self.points:+d} ({self.get_reason_display()})"


class Reward(models.Model):
    """Something a customer can turn points into."""

    title = models.CharField(max_length=128, verbose_name="Nomi")
    title_ru = models.CharField(max_length=128, blank=True, verbose_name="Nomi (ruscha)")
    title_en = models.CharField(
        max_length=128, blank=True, verbose_name="Nomi (inglizcha)"
    )
    description = models.TextField(blank=True, verbose_name="Tavsif")
    description_ru = models.TextField(blank=True, verbose_name="Tavsif (ruscha)")
    description_en = models.TextField(blank=True, verbose_name="Tavsif (inglizcha)")
    cost_points = models.PositiveIntegerField(
        default=500, verbose_name="Narxi (ball)"
    )
    code_prefix = models.CharField(
        max_length=12,
        default="RB",
        verbose_name="Promokod boshlanishi",
        help_text="Har bir mijozga RB-XXXXXX ko'rinishida noyob kod beriladi.",
    )
    stock = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Nechta qoldi",
        help_text="Bo'sh qoldirsangiz — cheklanmagan.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sovg'a"
        verbose_name_plural = "Sovg'alar (ballga almashtiriladi)"
        ordering = ["cost_points"]

    @property
    def is_available(self) -> bool:
        return self.is_active and (self.stock is None or self.stock > 0)

    def __str__(self) -> str:
        return f"{self.title} — {self.cost_points} ball"


class RewardRedemption(models.Model):
    """A reward actually claimed, with the code the customer shows in store."""

    _CODE_ALPHABET = string.ascii_uppercase + string.digits

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="redemptions",
        verbose_name="Mijoz",
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.SET_NULL,
        null=True,
        related_name="redemptions",
        verbose_name="Sovg'a",
    )
    code = models.CharField(max_length=32, unique=True, verbose_name="Promokod")
    points_spent = models.PositiveIntegerField(verbose_name="Sarflangan ball")
    is_used = models.BooleanField(
        default=False,
        verbose_name="Ishlatilgan",
        help_text="Mijoz do'konda kodni ishlatgach belgilang.",
    )
    used_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Olingan vaqt")

    class Meta:
        verbose_name = "Almashtirilgan sovg'a"
        verbose_name_plural = "Almashtirilgan sovg'alar"
        ordering = ["-created_at"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_used and self.used_at is None:
            self.used_at = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def make_code(cls, prefix: str) -> str:
        body = "".join(secrets.choice(cls._CODE_ALPHABET) for _ in range(6))
        return f"{(prefix or 'RB').upper()}-{body}"

    def __str__(self) -> str:
        return self.code
