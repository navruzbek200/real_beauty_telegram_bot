from __future__ import annotations

from typing import Any

from django.db import models
from django.utils import timezone


class GlobalSettings(models.Model):
    """
    Singleton model — only one row allowed.
    All values are editable from admin panel.
    """

    # The timed check-ins used to live here as four fixed fields. They are now
    # rows in `campaigns.AutoMessage`, where the shop controls the wording, the
    # delay *and* its unit — see the 0009 migration, which carried the old
    # values over.
    birthday_discount_percent = models.PositiveSmallIntegerField(
        default=30,
        verbose_name="Tug'ilgan kun chegirmasi (%)",
        help_text="Tug'ilgan kun xabaridagi foiz. Xabar matnida {{ discount }} "
        "o'rniga shu raqam qo'yiladi.",
    )

    # Social / channel links shown in the Mini App's "Biz bilan" menu. Each is
    # optional — a blank one simply hides its row.
    shop_name = models.CharField(
        max_length=64,
        default="Real Beauty",
        verbose_name="Do'kon nomi",
        help_text="Mini App sarlavhasida ko'rinadi.",
    )
    shop_tagline = models.CharField(
        max_length=120,
        blank=True,
        default="Teringizga professional g'amxo'rlik",
        verbose_name="Do'kon shiori",
    )
    # The Mini App header is the one piece of shop-written copy a Russian or
    # English customer sees before anything else; without these it greeted
    # them in Uzbek. Blank still falls back to Uzbek (`core.i18n.pick`).
    shop_tagline_ru = models.CharField(
        max_length=120,
        blank=True,
        default="Профессиональный уход за вашей кожей",
        verbose_name="Do'kon shiori (ruscha)",
    )
    shop_tagline_en = models.CharField(
        max_length=120,
        blank=True,
        default="Professional care for your skin",
        verbose_name="Do'kon shiori (inglizcha)",
    )
    instagram_url = models.URLField(
        blank=True,
        default="https://instagram.com/realbeauty_uz",
        verbose_name="Instagram havolasi",
    )
    youtube_url = models.URLField(
        blank=True,
        default="https://www.youtube.com/@Realbeauty_uz1/shorts",
        verbose_name="YouTube havolasi",
    )
    telegram_url = models.URLField(
        blank=True, verbose_name="Telegram kanal havolasi"
    )

    # --- delivery ----------------------------------------------------------
    # Charged to the customer as its own basket line. The shop pays the carrier
    # and recovers it here, so these have to be editable without a deploy.
    delivery_fee_yandex = models.PositiveIntegerField(
        default=25_000,
        verbose_name="Yandeks yetkazish haqi (so'm)",
        help_text="Toshkent bo'ylab. Savatchada alohida qator bo'lib qo'shiladi.",
    )
    delivery_fee_bts = models.PositiveIntegerField(
        default=35_000,
        verbose_name="BTS yetkazish haqi (so'm)",
        help_text="Viloyatlarga pochta. Savatchada alohida qator bo'lib qo'shiladi.",
    )

    class Meta:
        verbose_name = "Umumiy sozlamalar"
        verbose_name_plural = "Umumiy sozlamalar"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "GlobalSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return "Umumiy sozlamalar"


class Discount(models.Model):
    """
    Dynamic, admin-editable discount/promotion shown to bot users via the
    "Chegirmalar" menu button.
    """

    title = models.CharField(max_length=128, verbose_name="Sarlavha")
    percent = models.PositiveSmallIntegerField(
        default=0, verbose_name="Chegirma foizi (%)"
    )
    description = models.TextField(blank=True, verbose_name="Tavsif")
    promo_code = models.CharField(max_length=64, blank=True, verbose_name="Promokod")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Amal qilish muddati")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chegirma"
        verbose_name_plural = "Chegirmalar"
        ordering = ["-created_at"]

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.valid_until and self.valid_until < timezone.localdate():
            return False
        return True

    def __str__(self) -> str:
        return f"{self.title} — {self.percent}%"
