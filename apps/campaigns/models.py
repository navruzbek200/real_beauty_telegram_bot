from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db import models

logger = logging.getLogger(__name__)


def render_body(body: str, context: dict[str, Any], *, html: bool) -> str:
    """
    Fill `{{ placeholders }}` in an admin-written message body.

    Falls back to the raw text on any Jinja error: bodies are typed by hand in
    the CRM, and one unclosed brace must degrade to a slightly odd message —
    not crash the campaign task and leave every customer with nothing.

    With `html=True` substituted values are escaped, so a customer named "<3"
    can't produce markup Telegram rejects.
    """
    from jinja2 import Environment

    try:
        env = Environment(autoescape=html)
        return env.from_string(body).render(**context)
    except Exception:  # noqa: BLE001 — syntax or undefined-variable errors
        logger.exception("Template body failed to render; sending raw text")
        return body


class MessageTemplate(models.Model):
    """
    Editable message template with Jinja2-style placeholders.
    Available context: {{ user.full_name }}, {{ product.name }},
                       {{ discount }}, {{ week }}, etc.
    """

    class TemplateType(models.TextChoices):
        WELCOME = "welcome", "Ro'yxatdan o'tgach salomlashish"
        PRODUCT_INTRO = "product_intro", "Mahsulot qo'llanmasi kirish"
        WEEK1_CHECKIN = "week1_checkin", "1-hafta so'rovi"
        WEEK2_PROGRESS = "week2_progress", "2-hafta natija so'rovi"
        BIRTHDAY_SALE = "birthday_sale", "Tug'ilgan kun chegirmasi"
        FEEDBACK_THANKS = "feedback_thanks", "Fikr uchun rahmat"

    name = models.CharField(max_length=128, unique=True, verbose_name="Nomi")
    # Unique: the senders pick a template by type, so a second row of the same
    # type would make which text goes out a coin flip.
    template_type = models.CharField(
        max_length=32,
        choices=TemplateType.choices,
        unique=True,
        verbose_name="Shablon turi",
    )
    body = models.TextField(
        verbose_name="Xabar matni",
        help_text="{{ o'zgaruvchi }} qo'llab-quvvatlanadi. "
        "Masalan: {{ user.full_name }}, {{ product.name }}, {{ discount }}. "
        "Telegram HTML formatidan foydalaning.",
    )
    # Optional — an empty translation falls back to the Uzbek body, so the
    # shop can add languages one at a time instead of all at once.
    body_ru = models.TextField(blank=True, verbose_name="Xabar matni (ruscha)")
    body_en = models.TextField(blank=True, verbose_name="Xabar matni (inglizcha)")
    parse_mode = models.CharField(
        max_length=8,
        default="HTML",
        choices=[("HTML", "HTML"), ("Markdown", "Markdown")],
        verbose_name="Format",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Xabar shabloni"
        verbose_name_plural = "Xabar shablonlari"

    def render(self, context: dict[str, Any], lang: str = "uz") -> str:
        """Render this template's body for `lang`, filling in `context`."""
        from core.i18n import pick

        return render_body(
            pick(self, "body", lang), context, html=self.parse_mode == "HTML"
        )

    def __str__(self) -> str:
        return f"[{self.template_type}] {self.name}"


class CampaignLog(models.Model):
    """Records every message sent to a user."""

    user = models.ForeignKey(
        "users.TelegramUser", on_delete=models.CASCADE, verbose_name="Foydalanuvchi"
    )
    template = models.ForeignKey(
        MessageTemplate, on_delete=models.SET_NULL, null=True, verbose_name="Shablon"
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqt")
    success = models.BooleanField(default=True, verbose_name="Muvaffaqiyatli")
    error_detail = models.TextField(blank=True, verbose_name="Xato tafsiloti")

    class Meta:
        verbose_name = "Yuborilgan xabar"
        verbose_name_plural = "Yuborilgan xabarlar"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["-sent_at"]),
            models.Index(fields=["user", "-sent_at"]),
        ]

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"{self.user} — {self.template} [{status}]"


class AutoMessage(models.Model):
    """
    A message the bot sends by itself, N minutes/hours/days after something
    happened to the customer.

    Replaces the two hard-coded week-1/week-2 campaigns. The shop controls the
    wording, the delay *and its unit*, and the button — which is what makes
    this testable: set the unit to "daqiqa", the value to 1, switch on test
    mode, and the whole pipeline can be verified in a minute instead of a week.
    """

    class Trigger(models.TextChoices):
        AFTER_PURCHASE = "after_purchase", "Mahsulot sotib olingandan keyin"
        AFTER_REGISTRATION = "after_registration", "Ro'yxatdan o'tgandan keyin"

    class Unit(models.TextChoices):
        MINUTE = "minute", "daqiqa"
        HOUR = "hour", "soat"
        DAY = "day", "kun"

    class Action(models.TextChoices):
        NONE = "none", "Tugmasiz (faqat matn)"
        DISCOUNTS = "discounts", "«Chegirmalarni ko'rish» tugmasi"

    _UNIT_SECONDS = {Unit.MINUTE: 60, Unit.HOUR: 3600, Unit.DAY: 86400}

    # An anchor this much older than the delay predates the campaign itself
    # (staff enter purchases long before the customer opens the bot). Greeting
    # somebody months late reads as a broken bot, so those are marked done
    # without sending.
    STALE_GRACE_DAYS = 30

    name = models.CharField(
        max_length=128,
        verbose_name="Nomi",
        help_text="Faqat siz uchun. Masalan: «1 hafta — keshbek taklifi».",
    )
    trigger = models.CharField(
        max_length=24,
        choices=Trigger.choices,
        default=Trigger.AFTER_PURCHASE,
        verbose_name="Qachondan hisoblanadi",
    )
    delay_value = models.PositiveSmallIntegerField(
        default=7,
        verbose_name="Qancha vaqtdan keyin",
        help_text="Raqam. Masalan: 7.",
    )
    delay_unit = models.CharField(
        max_length=8,
        choices=Unit.choices,
        default=Unit.DAY,
        verbose_name="Vaqt birligi",
        help_text="«daqiqa» — sinash uchun qulay, «kun» — haqiqiy ish uchun.",
    )

    body = models.TextField(
        verbose_name="Xabar matni",
        help_text="Mijozga boradigan matn. {{ user.full_name }} va "
        "{{ product.name }} ishlaydi. Telegram HTML: <b>qalin</b>, <i>qiya</i>.",
    )
    body_ru = models.TextField(blank=True, verbose_name="Xabar matni (ruscha)")
    body_en = models.TextField(blank=True, verbose_name="Xabar matni (inglizcha)")

    button_action = models.CharField(
        max_length=16,
        choices=Action.choices,
        default=Action.NONE,
        verbose_name="Xabar ostidagi tugma",
    )
    button_label = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Tugma matni",
        help_text="«Tugmasiz» tanlansa, bu maydon e'tiborga olinmaydi.",
    )
    button_label_ru = models.CharField(
        max_length=64, blank=True, verbose_name="Tugma matni (ruscha)"
    )
    button_label_en = models.CharField(
        max_length=64, blank=True, verbose_name="Tugma matni (inglizcha)"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Yoqilgan",
        help_text="O'chirilsa bot bu xabarni umuman yubormaydi.",
    )
    # Test mode exists because the natural way to try a campaign — drop the
    # delay to one minute — would otherwise fire it at every customer who
    # bought something in the last month.
    is_test_mode = models.BooleanField(
        default=False,
        verbose_name="Sinov rejimi",
        help_text="Yoqilsa xabar FAQAT quyida tanlangan mijozga boradi. "
        "Vaqtni «1 daqiqa» qilib sinab ko'rish uchun.",
    )
    test_user = models.ForeignKey(
        "users.TelegramUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Sinov mijozi",
        help_text="Sinov rejimida xabar shu mijozga yuboriladi.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Avtomatik xabar"
        verbose_name_plural = "Avtomatik xabarlar"
        ordering = ["trigger", "delay_value"]

    def __str__(self) -> str:
        return self.name

    # --- timing -------------------------------------------------------------
    @property
    def delay(self) -> timedelta:
        seconds = self._UNIT_SECONDS[self.delay_unit] * self.delay_value
        return timedelta(seconds=seconds)

    @property
    def stale_grace(self) -> timedelta:
        return timedelta(days=self.STALE_GRACE_DAYS)

    @property
    def schedule_label(self) -> str:
        """"7 kun o'tgach" — how the delay reads in the CRM."""
        return f"{self.delay_value} {self.get_delay_unit_display()} o'tgach"

    # --- rendering ----------------------------------------------------------
    def render(self, context: dict[str, Any], lang: str = "uz") -> str:
        from core.i18n import pick

        return render_body(pick(self, "body", lang), context, html=True)

    def label_for(self, lang: str = "uz") -> str:
        from core.i18n import pick

        return pick(self, "button_label", lang)

    def keyboard_for(self, lang: str, product_id: int | None = None) -> dict | None:
        """
        The inline keyboard this message carries, as a raw Bot API dict.

        Returns None when there is no button to draw. `product_id` is accepted
        and ignored: the only remaining action opens the discount list, which
        is the same screen for everybody.
        """
        from bot.keyboards.inline import CB_OPEN_DISCOUNTS

        label = self.label_for(lang)
        if self.button_action == self.Action.NONE or not label:
            return None
        return {
            "inline_keyboard": [[{"text": label, "callback_data": CB_OPEN_DISCOUNTS}]]
        }


class AutoMessageLog(models.Model):
    """
    Proof that one auto-message already went to one anchor.

    `anchor` is what makes a send happen exactly once: "up:42" for a purchase,
    "user:7" for a registration. A plain (message, user) pair would be wrong —
    a customer who buys two products should get the check-in for both.
    """

    auto_message = models.ForeignKey(
        AutoMessage,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="Avtomatik xabar",
    )
    user = models.ForeignKey(
        "users.TelegramUser", on_delete=models.CASCADE, verbose_name="Mijoz"
    )
    anchor = models.CharField(max_length=32, editable=False)
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqt")
    success = models.BooleanField(default=True, verbose_name="Yetkazildi")
    error_detail = models.TextField(blank=True, verbose_name="Xato")

    class Meta:
        verbose_name = "Avtomatik xabar jurnali"
        verbose_name_plural = "Avtomatik xabarlar jurnali"
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["auto_message", "anchor"], name="uniq_automessage_anchor"
            )
        ]
        indexes = [models.Index(fields=["-sent_at"])]

    def __str__(self) -> str:
        return f"{self.auto_message} → {self.user}"


class ReminderRule(models.Model):
    """
    A recurring "every N days" nudge to one specific customer — e.g. a
    reorder reminder every 2 weeks — as opposed to `AutoMessage`, which fires
    once per purchase/registration anchor.

    Deliberately one row per customer rather than one global rule fanning out
    to everyone: a recurring reminder is usually set up for a specific person
    ("remind Aziza to reorder"), and `next_run_at` needs to live somewhere
    that survives independently per recipient once it starts drifting from
    however the rule was originally scheduled.
    """

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="reminder_rules",
        verbose_name="Mijoz",
        help_text="Faqat botga ulangan (telegram_id bor) mijozlarga yuboriladi.",
    )
    name = models.CharField(
        max_length=128,
        verbose_name="Nomi",
        help_text="Faqat siz uchun. Masalan: «Har 2 haftada — qayta buyurtma».",
    )
    body = models.TextField(
        verbose_name="Xabar matni",
        help_text="{{ user.full_name }} ishlaydi. Telegram HTML.",
    )
    interval_days = models.PositiveSmallIntegerField(
        default=14,
        verbose_name="Necha kunda bir marta",
    )
    next_run_at = models.DateTimeField(verbose_name="Keyingi yuborilish vaqti")
    last_sent_at = models.DateTimeField(
        null=True, blank=True, editable=False, verbose_name="Oxirgi yuborilgan"
    )
    is_active = models.BooleanField(default=True, verbose_name="Yoqilgan")
    send_count = models.PositiveIntegerField(
        default=0, editable=False, verbose_name="Yuborilgan marta"
    )
    error_count = models.PositiveIntegerField(
        default=0, editable=False, verbose_name="Xatolar soni"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Takrorlanuvchi eslatma"
        verbose_name_plural = "Takrorlanuvchi eslatmalar"
        ordering = ["next_run_at"]

    def __str__(self) -> str:
        return f"{self.name} → {self.user}"

    @property
    def interval(self) -> timedelta:
        return timedelta(days=self.interval_days)

    def render(self, lang: str | None = None) -> str:
        return render_body(
            self.body, {"user": self.user}, html=True
        )


class Broadcast(models.Model):
    """
    A one-off announcement the shop pushes to customers on demand: a seminar,
    a new arrival, a flash sale — anything that is not one of the fixed
    lifecycle templates.

    Kept separate from MessageTemplate because the lifecycle templates are a
    closed set the bot fires automatically, while these are composed and sent
    by a person whenever news comes up.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        SENDING = "sending", "Yuborilmoqda"
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Xato"

    class Audience(models.TextChoices):
        ALL = "all", "Hamma (botga ulangan barcha xaridorlar)"
        BY_SKIN = "by_skin", "Teri turi bo'yicha"
        BY_PRODUCT = "by_product", "Mahsulot sotib olganlar"

    title = models.CharField(
        max_length=128,
        verbose_name="Sarlavha (faqat siz uchun)",
        help_text="Ro'yxatda ko'rinadi. Mijozga yuborilmaydi.",
    )
    body = models.TextField(
        verbose_name="Xabar matni",
        help_text="Mijozga boradigan matn. Telegram HTML: <b>qalin</b>, "
        "<i>qiya</i>, <a href='...'>havola</a>.",
    )
    photo = models.ImageField(
        upload_to="broadcasts/",
        blank=True,
        null=True,
        verbose_name="Rasm (ixtiyoriy)",
        help_text="Yuklasangiz, xabar rasm bilan boradi.",
    )
    audience = models.CharField(
        max_length=16,
        choices=Audience.choices,
        default=Audience.ALL,
        verbose_name="Kimlarga",
    )
    skin_condition = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teri turi",
        help_text="«Teri turi bo'yicha» tanlansagina ishlaydi.",
    )
    product = models.ForeignKey(
        "products.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Mahsulot",
        help_text="«Mahsulot sotib olganlar» tanlansagina ishlaydi.",
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        editable=False,
        verbose_name="Holat",
    )
    total = models.PositiveIntegerField(default=0, editable=False, verbose_name="Jami")
    sent_count = models.PositiveIntegerField(
        default=0, editable=False, verbose_name="Yuborildi"
    )
    failed_count = models.PositiveIntegerField(
        default=0, editable=False, verbose_name="Yetmadi"
    )

    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    started_at = models.DateTimeField(null=True, blank=True, editable=False)
    finished_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "E'lon"
        verbose_name_plural = "E'lonlar"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def recipients(self):
        """
        Active, bot-linked customers this broadcast targets.

        Only linked users (telegram_id set) can be reached, and inactive ones
        were switched off on purpose — both are excluded regardless of filter.
        """
        from apps.users.models import TelegramUser

        qs = TelegramUser.objects.filter(is_active=True, telegram_id__isnull=False)
        if self.audience == self.Audience.BY_SKIN and self.skin_condition:
            qs = qs.filter(face_condition=self.skin_condition)
        elif self.audience == self.Audience.BY_PRODUCT and self.product_id:
            qs = qs.filter(userproduct__product_id=self.product_id)
        return qs.distinct()
