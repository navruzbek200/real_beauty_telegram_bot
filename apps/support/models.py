from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class SupportThread(models.Model):
    """
    One ongoing conversation between a bot user and the shop.

    A user has at most one open thread at a time: new messages land in the open
    thread, and a closed thread is reopened if the user writes again.
    """

    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        ANSWERED = "answered", "Javob berildi"
        CLOSED = "closed", "Yopilgan"

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="support_threads",
        verbose_name="Foydalanuvchi",
    )
    subject = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Mavzu",
        help_text="Foydalanuvchining birinchi xabaridan avtomatik olinadi.",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
        verbose_name="Holat",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ochilgan vaqt")
    last_message_at = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name="Oxirgi xabar"
    )
    # True while the newest message is from the user and nobody replied yet.
    awaiting_reply = models.BooleanField(
        default=True, db_index=True, verbose_name="Javob kutilmoqda"
    )

    class Meta:
        verbose_name = "Murojaat"
        verbose_name_plural = "Murojaatlar"
        ordering = ["-awaiting_reply", "-last_message_at"]
        indexes = [
            models.Index(fields=["-last_message_at"]),
            models.Index(fields=["status", "-last_message_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.subject or 'murojaat'}"

    def touch(self, *, from_user: bool) -> None:
        """Update thread state after a new message is appended."""
        self.last_message_at = timezone.now()
        self.awaiting_reply = from_user
        # A user message (re)opens the thread; an admin message answers it.
        self.status = self.Status.NEW if from_user else self.Status.ANSWERED
        self.save(update_fields=["last_message_at", "awaiting_reply", "status"])


class SupportMessage(models.Model):
    """A single message inside a thread, in either direction."""

    class Direction(models.TextChoices):
        IN = "in", "Foydalanuvchidan"
        OUT = "out", "Admindan"

    class AttachmentType(models.TextChoices):
        PHOTO = "photo", "Rasm"
        DOCUMENT = "document", "Hujjat"
        VOICE = "voice", "Ovozli xabar"
        VIDEO = "video", "Video"
        STICKER = "sticker", "Stiker"

    class Status(models.TextChoices):
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Yuborilmadi"

    thread = models.ForeignKey(
        SupportThread,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Murojaat",
    )
    direction = models.CharField(
        max_length=4, choices=Direction.choices, verbose_name="Yo'nalish"
    )
    text = models.TextField(blank=True, verbose_name="Matn")
    # Telegram file_id of an attachment (no disk copy kept).
    attachment_file_id = models.CharField(max_length=512, blank=True, editable=False)
    attachment_type = models.CharField(
        max_length=16, choices=AttachmentType.choices, blank=True, editable=False
    )
    # Set for outgoing messages written by a logged-in CRM user (legacy path);
    # group-routed replies are attributed via telegram_admin instead.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Muallif",
    )
    # Set for messages forwarded into / replied from the support group.
    telegram_admin = models.ForeignKey(
        "SupportAdmin",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
        verbose_name="Telegram admin",
    )
    # Where this message's copy landed in the support group, so an admin's
    # native Telegram reply can be matched back to this row.
    group_chat_id = models.BigIntegerField(null=True, blank=True, editable=False)
    group_message_id = models.BigIntegerField(null=True, blank=True, editable=False)
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.SENT,
        editable=False,
        verbose_name="Holat",
    )
    retry_count = models.SmallIntegerField(default=0, editable=False)
    error_detail = models.TextField(blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        verbose_name = "Murojaat xabari"
        verbose_name_plural = "Murojaat xabarlari"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["group_chat_id", "group_message_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_direction_display()}: {self.text[:40]}"


class SupportSettings(models.Model):
    """
    Singleton — only one row allowed.

    Holds the Telegram group used for support routing. The bot token itself
    stays in the BOT_TOKEN env var (the running bot process can't hot-swap
    it anyway); this model only tracks where replies should land and whether
    that connection is currently healthy.
    """

    class ConnectionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Tekshirilmagan"
        OK = "ok", "Ulangan"
        ERROR = "error", "Xatolik"

    group_chat_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Guruh Chat ID",
        help_text="Support xabarlari shu guruhga yuboriladi. Botni guruhga "
        "qo'shib, guruh ID sini shu yerga kiriting.",
    )
    connection_status = models.CharField(
        max_length=8,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.UNKNOWN,
        editable=False,
        verbose_name="Ulanish holati",
    )
    last_checked_at = models.DateTimeField(
        null=True, blank=True, editable=False, verbose_name="Oxirgi tekshiruv"
    )
    last_error = models.TextField(blank=True, editable=False, verbose_name="Xato")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram guruh sozlamasi"
        verbose_name_plural = "Telegram guruh sozlamasi"

    def save(self, *args, **kwargs) -> None:
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "SupportSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return "Telegram guruh sozlamasi"


class SupportAdmin(models.Model):
    """A Telegram account allowed to reply to support requests in the group."""

    telegram_user_id = models.BigIntegerField(
        unique=True,
        validators=[MinValueValidator(1)],
        verbose_name="Telegram ID",
    )
    name = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Ism",
        help_text="Ixtiyoriy — bo'sh qoldirsangiz, birinchi javobdan avtomatik olinadi.",
    )
    enabled = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")

    class Meta:
        verbose_name = "Guruh admini"
        verbose_name_plural = "Guruh adminlari"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name or str(self.telegram_user_id)
