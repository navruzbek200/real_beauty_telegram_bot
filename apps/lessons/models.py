"""
The gated video course.

Two things live here. `LessonVideo` is the course itself — a flat, ordered
list of videos with nothing but a title and a file, because the shop records
one video per topic and wants to publish it without first inventing a product
to hang it on. `AccessCode` is what opens the course: a customer who bought
something gets a word from the seller, types it into the Mini App, and the
course stays open for them from then on.

The video never leaves Telegram. The Mini App only ever lists titles; tapping
one deep-links into the bot chat, which sends the file with
`protect_content=True` — the single mechanism that actually stops forwarding
and saving, because it is enforced by Telegram's clients rather than by us.
Streaming the file from our own domain would put a downloadable URL in the
customer's hands no matter what the page around it did.
"""

from __future__ import annotations

import secrets
import string

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Ambiguous glyphs left out on purpose: a code gets read off a receipt or
# repeated over the phone, and 0/O and 1/I/L are where that goes wrong.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_code(length: int = 8) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def normalize_code(raw: str) -> str:
    """Fold a typed code onto its canonical form.

    Customers type these from memory, on a phone keyboard, in a hurry. Case,
    spaces and dashes carry no meaning, so none of them should be able to make
    a correct code fail.
    """
    return "".join(ch for ch in (raw or "").upper() if ch in string.ascii_uppercase + string.digits)


class LessonVideo(models.Model):
    """One video in the course."""

    title = models.CharField(
        max_length=120,
        verbose_name="Nomi",
        help_text="Mijoz ko'radigan sarlavha, masalan: «Terini to'g'ri tozalash».",
    )
    title_ru = models.CharField(max_length=120, blank=True, verbose_name="Nomi (ruscha)")
    title_en = models.CharField(max_length=120, blank=True, verbose_name="Nomi (inglizcha)")

    description = models.TextField(
        blank=True,
        verbose_name="Qisqa izoh",
        help_text="Ixtiyoriy. Ro'yxatda sarlavha ostida ko'rinadi.",
    )
    description_ru = models.TextField(blank=True, verbose_name="Qisqa izoh (ruscha)")
    description_en = models.TextField(blank=True, verbose_name="Qisqa izoh (inglizcha)")

    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Tartib",
        help_text="Kichik raqam yuqorida turadi: 1, 2, 3 …",
    )

    video_file = models.FileField(
        upload_to="lessons/",
        blank=True,
        verbose_name="Video fayl",
        help_text="MP4 tavsiya qilinadi. Telegram bitta faylga 50 MB ruxsat beradi.",
    )
    # Telegram hands back an id for every file it stores. Sending by id skips
    # the upload entirely, so the first customer pays the upload cost once and
    # everyone after them gets the video immediately.
    video_file_id = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="Telegram video ID",
        help_text="Birinchi yuborishdan keyin bot o'zi to'ldiradi. "
        "Boshqa botdan ko'chirayotgan bo'lsangiz qo'lda ham kiritishingiz mumkin.",
    )

    duration_seconds = models.PositiveIntegerField(
        default=0, verbose_name="Davomiyligi (soniya)", editable=False
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
        help_text="Belgi olib tashlansa dars ro'yxatdan yo'qoladi.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Video dars"
        verbose_name_plural = "Video darslar"

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"

    @property
    def has_video(self) -> bool:
        return bool(self.video_file_id or (self.video_file and self.video_file.name))

    def clean(self) -> None:
        if not self.has_video:
            raise ValidationError(
                {"video_file": "Video fayl yuklang yoki Telegram video ID kiriting."}
            )


class AccessCode(models.Model):
    """A word that opens the course.

    The default is one code per buyer (`max_uses = 1`): a word that works for
    everyone travels — it gets screenshotted into a group chat and the course
    stops being a reason to buy anything. A campaign-wide code is still
    possible (`max_uses = 0`) when the shop deliberately wants one.

    Spending is counted rather than consumed, so a customer who reinstalls
    Telegram and unlocks again does not burn a second seat — `LessonUnlock` is
    keyed on the customer, not on the code.
    """

    code = models.CharField(
        max_length=32,
        unique=True,
        verbose_name="Kalit so'z",
        help_text="Katta-kichik harf va tirelar ahamiyatsiz — mijoz qanday "
        "yozsa ham topiladi.",
    )
    label = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Izoh",
        help_text="O'zingiz uchun: bu kalit kimga berilgani, masalan «Sentabr aksiyasi».",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    max_uses = models.PositiveIntegerField(
        default=1,
        verbose_name="Nechta mijozga",
        help_text="1 — faqat bitta mijoz ishlatadi (tavsiya etiladi). "
        "0 — cheksiz, butun aksiya uchun.",
    )
    uses_count = models.PositiveIntegerField(default=0, editable=False, verbose_name="Ishlatilgan")
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Amal qilish muddati",
        help_text="Bo'sh qoldirsangiz — muddatsiz.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    issued_to = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_codes",
        verbose_name="Kimga berilgan",
        help_text="Ixtiyoriy: xaridorni tanlab qo'ysangiz, kimga qaysi kod "
        "berilgani keyin ham ma'lum bo'ladi.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kalit so'z"
        verbose_name_plural = "Kalit so'zlar"

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code) or generate_code()
        super().save(*args, **kwargs)

    @property
    def is_spent(self) -> bool:
        return bool(self.max_uses) and self.uses_count >= self.max_uses

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at) and self.expires_at <= timezone.now()

    @property
    def is_usable(self) -> bool:
        return self.is_active and not self.is_spent and not self.is_expired


class LessonUnlock(models.Model):
    """A customer who has opened the course, and what opened it."""

    user = models.OneToOneField(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="lesson_unlock",
        verbose_name="Xaridor",
    )
    code = models.ForeignKey(
        AccessCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unlocks",
        verbose_name="Ishlatilgan kalit",
    )
    unlocked_at = models.DateTimeField(auto_now_add=True, verbose_name="Ochilgan vaqt")

    class Meta:
        ordering = ["-unlocked_at"]
        verbose_name = "Ochilgan dars"
        verbose_name_plural = "Kim darslarni ochgan"

    def __str__(self) -> str:
        return f"{self.user} — {self.code or '—'}"
