from __future__ import annotations

from django import forms
from django.contrib import admin
from django.db.models import Max
from django.http import HttpRequest
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html
from unfold.admin import StackedInline

from core.admin import RBModelAdmin, yes_no_filter

from .models import Product, ProductTutorialStep, TopProduct


class TutorialStepForm(forms.ModelForm):
    class Meta:
        model = ProductTutorialStep
        fields = [
            "order",
            "button_label",
            "intro_text",
            "video_file",
            "protect_content",
            "button_label_ru",
            "button_label_en",
            "intro_text_ru",
            "intro_text_en",
        ]
        labels = {
            "order": "Tartib raqami",
            "button_label": "Tugma matni",
            "intro_text": "Video oldidan yoziladigan matn",
            "video_file": "Video",
            "protect_content": "Videoni ulashish va saqlashni taqiqlash",
        }
        help_texts = {
            "order": "Bo'sh qoldirsangiz oxiriga qo'shiladi.",
            "button_label": "Botda shu matnli tugma chiqadi. "
            "Masalan: «1-qadam: Tozalash».",
            "intro_text": "Video yuborilishidan oldin ko'rsatiladigan qisqa izoh.",
            "video_file": "Ixtiyoriy. Yuklamasangiz bot «tez orada» deb yozadi.",
            "protect_content": "Bot barcha darslik videolarni har doim himoyalangan "
            "holda yuboradi (yuklab olish va forward qilish taqiqlangan) — bu "
            "maydondan qat'i nazar.",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Typing the sequence number by hand is busywork the formset can do.
        self.fields["order"].required = False


class TutorialStepFormSet(BaseInlineFormSet):
    """Fills in the step numbers the admin left blank."""

    def clean(self) -> None:
        super().clean()
        if any(self.errors):
            return

        live = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        # Start after both the numbers typed on this screen and any the product
        # already has — on the add page there is no product to query yet, which
        # is why this cannot be answered one form at a time.
        taken = [f.cleaned_data.get("order") or 0 for f in live]
        if self.instance.pk:
            existing = self.instance.tutorial_steps.exclude(
                pk__in=[f.instance.pk for f in live if f.instance.pk]
            ).aggregate(top=Max("order"))["top"]
            taken.append(existing or 0)
        counter = max(taken, default=0)

        for form in live:
            if not form.cleaned_data.get("order"):
                counter += 1
                form.cleaned_data["order"] = counter
                form.instance.order = counter


class ProductTutorialStepInline(StackedInline):
    """Tutorial steps edited right inside the product — one screen for everything."""

    model = ProductTutorialStep
    form = TutorialStepForm
    formset = TutorialStepFormSet
    extra = 1
    fields = [
        "order",
        "button_label",
        "intro_text",
        "video_file",
        "protect_content",
        "button_label_ru",
        "button_label_en",
        "intro_text_ru",
        "intro_text_en",
    ]
    ordering = ["order"]
    verbose_name = "Qo'llanma qadami"
    verbose_name_plural = "Qo'llanma qadamlari (mijoz botda ko'radigan video darslar)"


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "photo",
            "is_active",
            "current_price",
            "old_price",
            "name_ru",
            "name_en",
            "description_ru",
            "description_en",
            "is_top",
            "top_order",
            "top_note",
            "top_note_ru",
            "top_note_en",
        ]
        labels = {
            "name": "Mahsulot nomi",
            "description": "Tavsif",
            "photo": "Rasm",
            "is_active": "Faol",
        }
        help_texts = {
            "description": "Mijozga ko'rsatiladigan qisqa tavsif.",
            "photo": "Ixtiyoriy — shart emas.",
            "is_active": "O'chirilsa yangi xaridorlarga biriktirib bo'lmaydi.",
        }


_PRODUCT_FIELDSETS = (
    (
        "Mahsulot",
        {
            "fields": [
                "name",
                "description",
                "photo",
                "is_active",
                "current_price",
                "old_price",
            ]
        },
    ),
    (
        "Boshqa tillar (ixtiyoriy)",
        {
            "fields": ["name_ru", "name_en", "description_ru", "description_en"],
            "classes": ["collapse"],
            "description": "Bo'sh qoldirsangiz mijozga o'zbekcha matn ko'rinadi.",
        },
    ),
    (
        "Bu oydagi top ro'yxati",
        {
            "fields": ["is_top", "top_order", "top_note", "top_note_ru", "top_note_en"],
            "description": "Belgilansa, botdagi «🔥 Bu oydagi top mahsulotlar» "
            "tugmasi ostida chiqadi.",
        },
    ),
)


@admin.register(Product)
class ProductAdmin(RBModelAdmin):
    form = ProductForm
    list_display = [
        "name",
        "price_display",
        "steps_summary",
        "buyers_count",
        "top_badge",
        "active_badge",
    ]
    list_display_links = ["name"]
    list_filter = [
        yes_no_filter("is_active", "Mahsulot holati", "Faol", "O'chirilgan"),
        yes_no_filter("is_top", "Top ro'yxati", "Topda", "Topda emas"),
    ]
    search_fields = ["name", "description"]
    inlines = [ProductTutorialStepInline]
    list_per_page = 25
    fieldsets = _PRODUCT_FIELDSETS
    actions = ["add_to_top", "remove_from_top"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tutorial_steps")

    @admin.display(description="Narxi")
    def price_display(self, obj: Product) -> str:
        if obj.old_price and obj.old_price > obj.current_price:
            return format_html(
                '<span style="text-decoration:line-through;color:#9ca3af">{}</span> '
                '<b>{}</b> so\'m',
                f"{obj.old_price:,}".replace(",", " "),
                f"{obj.current_price:,}".replace(",", " "),
            )
        return f"{obj.current_price:,}".replace(",", " ") + " so'm"

    @admin.display(description="Top")
    def top_badge(self, obj: Product) -> str:
        if not obj.is_top:
            return "—"
        return format_html(
            '<span style="color:#d97706;font-weight:600">🔥 #{}</span>', obj.top_order
        )

    @admin.action(description="🔥 Bu oydagi topga qo'shish")
    def add_to_top(self, request, queryset) -> None:
        # New entries land at the end of the list rather than fighting over
        # position 1 with whatever is already there.
        start = (
            Product.objects.filter(is_top=True).aggregate(top=Max("top_order"))["top"]
            or 0
        )
        for offset, product in enumerate(queryset.filter(is_top=False), start=1):
            product.is_top = True
            product.top_order = start + offset
            product.save(update_fields=["is_top", "top_order"])
        self.message_user(request, "Top ro'yxatiga qo'shildi ✅")

    @admin.action(description="Topdan olib tashlash")
    def remove_from_top(self, request, queryset) -> None:
        updated = queryset.update(is_top=False)
        self.message_user(request, f"{updated} ta mahsulot topdan olindi.")

    @admin.display(description="Qo'llanma")
    def steps_summary(self, obj: Product) -> str:
        steps = list(obj.tutorial_steps.all())
        if not steps:
            return format_html(
                '<span style="color:#dc2626">⚠️ Qadam yo\'q — bot qo\'llanma '
                "yubora olmaydi</span>"
            )
        missing = [s for s in steps if not s.has_video]
        if missing:
            # A step with no video still sends "coming soon" — not something you
            # want to find out about from a customer.
            return format_html(
                '{} ta qadam · <span style="color:#f59e0b">{} tasida video '
                "yo'q</span>",
                len(steps),
                len(missing),
            )
        return format_html(
            '{} ta qadam · <span style="color:#059669">videolar to\'liq</span>',
            len(steps),
        )

    @admin.display(description="Xaridorlar")
    def buyers_count(self, obj: Product) -> str:
        return f"{obj.userproduct_set.count()} ta"

    @admin.display(description="Holat")
    def active_badge(self, obj: Product) -> str:
        if obj.is_active:
            return format_html(
                '<span style="color:#059669;font-weight:600">✅ Faol</span>'
            )
        return format_html('<span style="color:#9ca3af">⏸ O\'chirilgan</span>')


@admin.register(TopProduct)
class TopProductAdmin(RBModelAdmin):
    """
    The monthly top list on its own page.

    Same rows as the catalogue, filtered to the ones flagged as top and sorted
    the way the bot shows them — so curating the list is reading one screen
    top to bottom, not scanning a full product table for ticks.
    """

    form = ProductForm
    list_display = [
        "top_position",
        "name",
        "price_display",
        "top_note",
        "buyers_count",
        "active_badge",
    ]
    list_display_links = ["name"]
    search_fields = ["name", "top_note"]
    ordering = ["top_order", "name"]
    fieldsets = _PRODUCT_FIELDSETS

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tutorial_steps")

    @admin.display(description="O'rni", ordering="top_order")
    def top_position(self, obj: TopProduct) -> str:
        return format_html(
            '<span style="font-weight:700;color:#d97706">#{}</span>', obj.top_order
        )

    price_display = ProductAdmin.price_display

    @admin.display(description="Xaridorlar")
    def buyers_count(self, obj: TopProduct) -> str:
        return f"{obj.userproduct_set.count()} ta"

    @admin.display(description="Holat")
    def active_badge(self, obj: TopProduct) -> str:
        if obj.is_active:
            return format_html(
                '<span style="color:#059669;font-weight:600">✅ Botda ko\'rinadi</span>'
            )
        # A deactivated product is hidden by the bot even while flagged top;
        # saying so here beats wondering why the list looks short.
        return format_html(
            '<span style="color:#dc2626">⏸ O\'chirilgan — botda chiqmaydi</span>'
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        # Products are created on the catalogue page; this one curates them.
        return False
