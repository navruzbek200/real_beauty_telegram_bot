from __future__ import annotations

from django.db import models


class UserFeedback(models.Model):
    user = models.ForeignKey(
        "users.TelegramUser", on_delete=models.CASCADE, verbose_name="Foydalanuvchi"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Mahsulot",
    )
    week = models.PositiveSmallIntegerField(verbose_name="Hafta")  # 1 or 2
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Baho (1-5)"
    )
    text = models.TextField(blank=True, verbose_name="Fikr matni")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqt")

    # Admin reply → sent back to the customer in the bot.
    admin_reply = models.TextField(
        blank=True,
        verbose_name="Javob (mijozga yuboriladi)",
        help_text="Bu yerga yozib saqlasangiz, matn botda mijozga yuboriladi.",
    )
    reply_sent = models.BooleanField(
        default=False, editable=False, verbose_name="Javob yuborildi"
    )

    class Meta:
        verbose_name = "Fikr"
        verbose_name_plural = "Fikrlar"
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.user} — {self.week}-hafta — {self.rating}"


class SkinQuizResult(models.Model):
    """
    One completed run of the 10-question skin quiz.

    The raw answers are kept, not just the verdict: the shop reads them to see
    *why* somebody came out as, say, oily-with-pigmentation, and the scoring
    rules can be re-run over old submissions when the recommendations change.
    """

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="skin_quiz_results",
        verbose_name="Foydalanuvchi",
    )
    skin_type = models.CharField(max_length=20, verbose_name="Aniqlangan teri turi")
    # {"q1": 4, "q2": 3, ...} — question id to 0–5 answer.
    answers = models.JSONField(default=dict, verbose_name="Javoblar")
    # i18n keys of the recommendation blocks shown, so the CRM can display the
    # exact advice this customer received.
    recommendation_keys = models.JSONField(
        default=list, verbose_name="Berilgan tavsiyalar"
    )
    language = models.CharField(
        max_length=5, default="uz", verbose_name="Til"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Topshirilgan vaqt")

    class Meta:
        verbose_name = "Teri testi natijasi"
        verbose_name_plural = "Teri testi natijalari"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user} — {self.skin_type}"


class ProgressPhoto(models.Model):
    """
    A before/after photo.

    Storage is deliberately split: the full-size original stays on Telegram's
    servers and is addressed by `file_id` (free, permanent, fetched on demand),
    while our disk only ever holds a small thumbnail for the admin gallery.
    At ~40 KB each, 10k photos cost ~400 MB instead of ~20 GB.
    """

    THUMBNAIL_SIZE = (400, 400)

    class Label(models.TextChoices):
        BEFORE = "before", "Oldin"
        AFTER = "after", "Keyin"

    user = models.ForeignKey(
        "users.TelegramUser", on_delete=models.CASCADE, verbose_name="Foydalanuvchi"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Mahsulot",
    )
    # Original on Telegram — the source of truth, never deleted.
    file_id = models.CharField(
        max_length=512, blank=True, editable=False, verbose_name="Telegram file_id"
    )
    thumbnail = models.ImageField(
        upload_to="progress_thumbs/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Kichik nusxa",
    )
    thumbnail_purged = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="Kichik nusxa tozalangan",
        help_text="Thumbnail diskdan o'chirilgan; original Telegramda saqlanib qolgan.",
    )
    label = models.CharField(
        max_length=8, choices=Label.choices, verbose_name="Turi"
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqt")

    class Meta:
        verbose_name = "Natija rasmi"
        verbose_name_plural = "Natija rasmlari"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["user", "-submitted_at"]),
            models.Index(fields=["-submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.get_label_display()}"


class FaceAnalysisPhoto(models.Model):
    """
    A selfie run through the standalone «Yuz tahlili» menu button.

    Unlike ProgressPhoto (thumbnail only, original stays on Telegram) or the
    registration photo on TelegramUser, this keeps the full file on our own
    disk under an exact, predictable name — that name is what a future Google
    Sheets sync writes into the Image_Filename column so the sheet row and
    this file point at each other.
    """

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="face_analysis_photos",
        verbose_name="Foydalanuvchi",
    )
    skin_type = models.CharField(max_length=20, verbose_name="Teri turi")
    image = models.ImageField(upload_to="face_analysis/", verbose_name="Rasm")
    # The exact basename `image` was saved under — kept separately from
    # `image.name` (which carries the "face_analysis/" folder prefix) since
    # this is the literal value a Sheets row needs.
    filename = models.CharField(
        max_length=255, editable=False, verbose_name="Fayl nomi"
    )
    synced_to_sheet = models.BooleanField(
        default=False, editable=False, verbose_name="Sheetga yozildi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuklangan vaqt")

    class Meta:
        verbose_name = "Yuz tahlili rasmi"
        verbose_name_plural = "Yuz tahlili rasmlari"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return self.filename
