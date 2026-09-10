from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Staff(User):
    """
    Proxy over Django's auth user, so the CRM login accounts show up as
    "Xodimlar" instead of a page called "Users" sitting next to the customers
    and reading like it means them.
    """

    class Meta:
        proxy = True
        verbose_name = "Xodim"
        verbose_name_plural = "Xodimlar"


class SellerProfile(models.Model):
    """
    Links a Django auth user (a seller/admin who works in the CRM) to their
    Telegram account, so the bot can attribute referral registrations to them
    and the CRM can render their personal invite link.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_profile",
    )
    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        help_text="Sotuvchining Telegram ID raqami (referal havola uchun).",
    )
    display_name = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sotuvchi sozlamasi"
        verbose_name_plural = "Sotuvchi sozlamalari"

    @property
    def invite_link(self) -> str:
        username = getattr(settings, "BOT_USERNAME", "RealBeautyBot")
        return f"https://t.me/{username}?start=ref_{self.telegram_id}"

    def __str__(self) -> str:
        return self.display_name or (self.user.get_username())


class TelegramUser(models.Model):
    """Registered bot user."""

    class FaceCondition(models.TextChoices):
        DRY = "dry", "Quruq"
        OILY = "oily", "Yog'li"
        COMBINED = "combined", "Aralash"
        NORMAL = "normal", "Normal"
        SENSITIVE = "sensitive", "Sezgir"

    class RegistrationSource(models.TextChoices):
        SELF = "self", "O'zi ro'yxatdan o'tgan"
        ADMIN = "admin", "Admin yordamida"
        APP = "app", "Mobil ilova"

    class RegistrationStatus(models.TextChoices):
        PENDING = "pending", "To'ldirilishi kerak"
        COMPLETED = "completed", "To'ldirilgan"

    class Language(models.TextChoices):
        UZ = "uz", "O'zbekcha"
        RU = "ru", "Русский"
        EN = "en", "English"

    # Empty until the customer opens the bot. Staff add customers by name and
    # phone; the bot fills this in on /start by matching the phone number.
    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name="Telegram ID",
    )
    username = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="Telegram username"
    )
    full_name = models.CharField(max_length=256, blank=True, verbose_name="To'liq ism")
    birth_date = models.DateField(
        null=True, blank=True, verbose_name="Tug'ilgan sana"
    )
    phone_number = models.CharField(
        max_length=20, blank=True, verbose_name="Telefon raqami"
    )
    # Last 9 digits of phone_number, kept in sync by save(). Staff type
    # "+998 90 123 45 67" while Telegram reports "998901234567", so the raw
    # strings never compare equal — this column is what we actually match on.
    phone_tail = models.CharField(
        max_length=9, blank=True, db_index=True, editable=False
    )
    # Picked on the very first /start, before anything else is asked — every
    # later message, button and campaign is rendered in it.
    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.UZ,
        verbose_name="Til",
        help_text="Mijoz botda tanlagan til. Xabarlar shu tilda yuboriladi.",
    )
    face_condition = models.CharField(
        max_length=20,
        choices=FaceCondition.choices,
        blank=True,
        verbose_name="Teri turi",
    )
    photo = models.ImageField(
        upload_to="user_photos/", blank=True, null=True, verbose_name="Rasm"
    )
    products = models.ManyToManyField(
        "products.Product",
        blank=True,
        through="UserProduct",
        verbose_name="Mahsulotlar",
    )
    registered_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )
    referred_by_seller = models.ForeignKey(
        SellerProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referred_users",
        verbose_name="Referal sotuvchi",
    )
    source = models.CharField(
        max_length=10,
        choices=RegistrationSource.choices,
        default=RegistrationSource.SELF,
    )
    registration_status = models.CharField(
        max_length=12,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
        verbose_name="Ro'yxat holati",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")
    # When the customer finished registration in the bot. `created_at` can be
    # months earlier — staff enter customer cards long before the person opens
    # Telegram — so anything counting "N days after signing up" has to use this.
    registered_at = models.DateTimeField(
        null=True, blank=True, editable=False, verbose_name="Ro'yxatdan o'tgan vaqt"
    )

    class Meta:
        verbose_name = "Xaridor"
        verbose_name_plural = "Xaridorlar"

    def save(self, *args, **kwargs) -> None:
        self.phone_tail = self.phone_tail_of(self.phone_number)
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            fields = set(kwargs["update_fields"])
            if "phone_number" in fields:
                fields.add("phone_tail")
                kwargs["update_fields"] = fields
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.username:
            return f"{self.full_name or 'Ismsiz'} (@{self.username})"
        return self.full_name or self.phone_number or f"#{self.pk}"

    @property
    def is_linked(self) -> bool:
        """True once the customer has opened the bot and we know their chat."""
        return self.telegram_id is not None

    @staticmethod
    def phone_tail_of(phone: str | None) -> str:
        """
        Last 9 digits of a phone number — the part that identifies a subscriber
        regardless of how it was typed (+998 90 123-45-67, 909 1234567, …).
        """
        digits = "".join(ch for ch in (phone or "") if ch.isdigit())
        return digits[-9:] if len(digits) >= 9 else ""

    # The shop is ~90% Uzbekistan, so a bare 9-digit local number defaults to
    # +998. But customers standing in Russia, the US, anywhere — reachable on
    # the same bot — must work too, which a hard-coded 998 prefix broke.
    DEFAULT_REGION = "UZ"

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        """
        Canonical E.164 (+<country><number>), or None if it isn't a real number.

        Country is detected, not assumed: a "+" or an international-length
        number is parsed for its own country code (Russia +7, the US +1 …),
        and only a short local number falls back to Uzbekistan. Telegram hands
        contacts over without a leading "+", so those are tried as
        international first before the local fallback.
        """
        import phonenumbers

        raw = (phone or "").strip()
        if not raw:
            return None

        candidates: list[str] = []
        if raw.startswith("+"):
            candidates.append(raw)
        else:
            digits = "".join(ch for ch in raw if ch.isdigit())
            if not digits:
                return None
            # 11+ digits can only be carrying a country code (UZ local is 9),
            # so read it as international first; then fall back to a local
            # number in the default region.
            if len(digits) >= 11:
                candidates.append("+" + digits)
            candidates.append(digits)

        for candidate in candidates:
            try:
                parsed = phonenumbers.parse(candidate, TelegramUser.DEFAULT_REGION)
            except phonenumbers.NumberParseException:
                continue
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
        return None

    @property
    def is_birthday_today(self) -> bool:
        if not self.birth_date:
            return False
        today = timezone.now().date()
        return (
            self.birth_date.day == today.day
            and self.birth_date.month == today.month
        )


class AppUserManager(models.Manager):
    """Keeps the app-users page showing only rows the mobile app created."""

    def get_queryset(self) -> models.QuerySet:
        return (
            super()
            .get_queryset()
            .filter(source=TelegramUser.RegistrationSource.APP)
        )


class AppUser(TelegramUser):
    """
    Proxy over the customer table, so people who signed up in the Flutter app
    get their own menu item instead of being something you have to remember to
    filter for on the (much busier) "Xaridorlar" page.

    Same rows, same table — "Xaridorlar" still lists everyone, this page is the
    app slice of it.
    """

    objects = AppUserManager()

    class Meta:
        proxy = True
        verbose_name = "App foydalanuvchisi"
        verbose_name_plural = "App foydalanuvchilari"


class UserProduct(models.Model):
    """Through model tracking when a user bought a product."""

    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, verbose_name="Foydalanuvchi"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, verbose_name="Mahsulot"
    )
    purchased_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Sotib olingan sana"
    )

    # Track campaign state for this purchase
    week1_sent = models.BooleanField(default=False, verbose_name="1-hafta yuborilgan")
    week2_sent = models.BooleanField(default=False, verbose_name="2-hafta yuborilgan")

    class Meta:
        unique_together = ("user", "product")
        verbose_name = "Sotib olingan mahsulot"
        verbose_name_plural = "Sotib olingan mahsulotlar"

    def __str__(self) -> str:
        return f"{self.user.full_name} — {self.product.name}"


def _generate_login_token() -> str:
    # url-safe, no "=" padding — this string is embedded verbatim in a
    # Telegram deep link (t.me/<bot>?start=auth_<token>), whose payload only
    # allows [A-Za-z0-9_-] and 64 chars total.
    return secrets.token_urlsafe(24)


def _default_login_session_expiry():
    return timezone.now() + timedelta(minutes=TelegramLoginSession.EXPIRY_MINUTES)


class TelegramLoginSession(models.Model):
    """
    A single "log in to the Flutter app via Telegram" attempt.

    The app calls /api/auth/init-session/ to get a token and builds the deep
    link itself; the customer taps it, Telegram opens the bot, and the bot
    either shows a confirm button (existing account) or runs registration and
    confirms automatically once it finishes. The app polls
    /api/auth/check-session/<token>/ until it sees CONFIRMED, then gets a
    Firebase custom token for the same account — the same identity the
    phone-OTP flow already mints, so a customer who used both ends up on one
    Firebase user either way.

    Single-use: check-session deletes the row once it has handed the result
    back, so a leaked token is only ever worth one sign-in.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        CONFIRMED = "confirmed", "Tasdiqlangan"

    EXPIRY_MINUTES = 5

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        default=_generate_login_token,
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    user = models.ForeignKey(
        TelegramUser,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="login_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_login_session_expiry)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ilova kirish sessiyasi"
        verbose_name_plural = "Ilova kirish sessiyalari"

    def __str__(self) -> str:
        return f"{self.token[:8]}… ({self.status})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
