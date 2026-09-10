from __future__ import annotations

from django.db import models


class TopProductManager(models.Manager):
    """Keeps the "top of the month" page showing only the picked products."""

    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(is_top=True)


class Product(models.Model):
    name = models.CharField(max_length=256, verbose_name="Nomi")
    name_ru = models.CharField(
        max_length=256, blank=True, verbose_name="Nomi (ruscha)"
    )
    name_en = models.CharField(
        max_length=256, blank=True, verbose_name="Nomi (inglizcha)"
    )
    description = models.TextField(blank=True, verbose_name="Tavsif")
    description_ru = models.TextField(blank=True, verbose_name="Tavsif (ruscha)")
    description_en = models.TextField(blank=True, verbose_name="Tavsif (inglizcha)")
    photo = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        verbose_name="Rasm (ixtiyoriy)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    current_price = models.PositiveIntegerField(
        default=0,
        verbose_name="Hozirgi narxi (so'm)",
    )
    old_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Eski narxi (so'm)",
        help_text="Chegirmani ko'rsatish uchun. Bo'sh qoldirsangiz chegirma "
        "ko'rsatilmaydi.",
    )

    # --- "Bu oydagi top mahsulotlar" ---------------------------------------
    # A flag on the product rather than a separate table: the shop picks from
    # the products it already sells, and a parallel list would let the two
    # drift apart (a renamed or deactivated product still showing in the top).
    is_top = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Bu oyning top mahsuloti",
        help_text="Belgilansa, botdagi «Bu oydagi top mahsulotlar» ro'yxatida "
        "chiqadi.",
    )
    top_order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Top ro'yxatdagi o'rni",
        help_text="1 — birinchi bo'lib chiqadi, keyin 2, 3 ...",
    )
    top_note = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Top izohi",
        help_text="Ixtiyoriy: «Eng ko'p sotilgan», «Yangi kelgan» kabi qisqa "
        "yozuv. Mahsulot ostida ko'rinadi.",
    )
    top_note_ru = models.CharField(
        max_length=200, blank=True, verbose_name="Top izohi (ruscha)"
    )
    top_note_en = models.CharField(
        max_length=200, blank=True, verbose_name="Top izohi (inglizcha)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def __str__(self) -> str:
        return self.name

    @property
    def discount_percent(self) -> int | None:
        """Whole-percent discount, or None when there is nothing to show."""
        if not self.old_price or self.old_price <= self.current_price:
            return None
        return round((1 - self.current_price / self.old_price) * 100)


class TopProduct(Product):
    """
    Proxy over Product giving the monthly top list its own CRM page.

    Same rows, same table — this page is just the slice with `is_top` set, so
    the shop can curate the list without hunting through the full catalogue.
    """

    objects = TopProductManager()

    class Meta:
        proxy = True
        ordering = ["top_order", "name"]
        verbose_name = "Top mahsulot"
        verbose_name_plural = "Bu oydagi top mahsulotlar"


class ProductTutorialStep(models.Model):
    """
    One tutorial step of a product: an inline button in the bot that plays a
    short "how to use" video. Everything (button text, message, video) is
    managed right inside the product — no separate video library.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="tutorial_steps",
        verbose_name="Mahsulot",
    )
    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Ketma-ketlik",
        help_text="Tugmalar tartibi: 1, 2, 3 ... (kichik raqam yuqorida turadi).",
    )
    button_label = models.CharField(
        max_length=64,
        verbose_name="Tugma matni",
        help_text="Botda ko'rinadigan tugma, masalan: «1-qadam: Tozalash».",
    )
    button_label_ru = models.CharField(
        max_length=64, blank=True, verbose_name="Tugma matni (ruscha)"
    )
    button_label_en = models.CharField(
        max_length=64, blank=True, verbose_name="Tugma matni (inglizcha)"
    )
    intro_text = models.TextField(
        blank=True,
        verbose_name="Video oldidan matn",
        help_text="Ixtiyoriy: video yuborilishidan oldin ko'rsatiladigan qisqa "
        "izoh. Bo'sh qoldirsangiz — faqat video yuboriladi.",
    )
    intro_text_ru = models.TextField(
        blank=True, verbose_name="Video oldidan matn (ruscha)"
    )
    intro_text_en = models.TextField(
        blank=True, verbose_name="Video oldidan matn (inglizcha)"
    )
    video_file = models.FileField(
        upload_to="videos/",
        blank=True,
        null=True,
        verbose_name="Video (ixtiyoriy)",
        help_text="Video yuklang. Yuklamasangiz bot «tez orada» deb yozadi.",
    )
    # Filled automatically by the bot after the first send (reuse, no re-upload).
    video_file_id = models.CharField(max_length=512, blank=True, editable=False)
    protect_content = models.BooleanField(
        default=True,
        verbose_name="Himoya (ulashish/saqlashni taqiqlash)",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Qo'llanma qadami"
        verbose_name_plural = "Qo'llanma qadamlari"

    @property
    def has_video(self) -> bool:
        return bool(self.video_file_id or (self.video_file and self.video_file.name))

    def __str__(self) -> str:
        return f"{self.product.name} — {self.order}: {self.button_label}"
