from __future__ import annotations

import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.utils.html import escape, format_html
from unfold.admin import TabularInline

from core.admin import RBModelAdmin, bot_link_badge, yes_no_filter
from core.telegram import TelegramError, send_message

from .forms import PhoneNumberUniqueMixin
from .models import TelegramUser, UserProduct

logger = logging.getLogger(__name__)

# Registers the staff-account admin that replaces Django's stock user page.
from . import staff_admin  # noqa: F401,E402  (import for side effects)

# Registers the app-only slice of the customer table as its own menu item.
from . import app_user_admin  # noqa: F401,E402  (import for side effects)

# The "Groups" (permission sets) page is not needed for this simple shop —
# the staff page asks for a role instead. Login accounts live under "Xodimlar".
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


class UserProductInline(TabularInline):
    model = UserProduct
    extra = 1
    fields = ["product", "week1_sent", "week2_sent"]
    readonly_fields = ["week1_sent", "week2_sent"]
    verbose_name = "Sotib olingan mahsulot"
    verbose_name_plural = "Sotib olingan mahsulotlar"


class TelegramUserForm(PhoneNumberUniqueMixin, forms.ModelForm):
    """
    Staff-facing customer card.

    Deliberately free of Telegram plumbing: whoever adds a customer at the
    counter knows their name and phone, never their numeric Telegram ID, so the
    bot resolves that itself when the customer opens it.
    """

    class Meta:
        model = TelegramUser
        fields = [
            "full_name",
            "phone_number",
            "username",
            "birth_date",
            "face_condition",
            "photo",
            "is_active",
        ]
        labels = {
            "full_name": "Ism-familiya",
            "phone_number": "Telefon raqami",
            "username": "Telegram username",
            "photo": "Rasm",
        }
        help_texts = {
            "phone_number": "Masalan: +998 90 123 45 67. "
            "Mijoz botga kirganda shu raqam orqali ulanadi.",
            "username": "Ixtiyoriy. Bilsangiz yozing (@ belgisiz) — ulanish tezlashadi.",
            "birth_date": "Ixtiyoriy. To'ldirsangiz, tug'ilgan kunida chegirma "
            "xabari avtomatik boradi.",
            "face_condition": "Ixtiyoriy.",
            "photo": "Ixtiyoriy — shart emas.",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # A card with no name is useless to look up later; the model keeps the
        # field blankable because the bot creates rows before asking the name.
        self.fields["full_name"].required = True
        self.fields["phone_number"].required = True

    def clean_username(self) -> str:
        # Staff type "@name" out of habit; store it the way Telegram reports it.
        return (self.cleaned_data.get("username") or "").lstrip("@").strip()

    def clean_full_name(self) -> str:
        name = (self.cleaned_data.get("full_name") or "").strip()
        # "<" or ">" would break every HTML-mode bot message embedding the name.
        if "<" in name or ">" in name:
            raise forms.ValidationError("Ismda < yoki > belgisi bo'lmasin.")
        return name


@admin.register(TelegramUser)
class TelegramUserAdmin(RBModelAdmin):
    form = TelegramUserForm
    list_display = [
        "photo_thumb",
        "full_name",
        "phone_number",
        "source_badge",
        "products_list",
        "link_badge",
        "created_at",
    ]
    list_filter = [
        yes_no_filter("is_active", "Xaridor holati", "Faol", "O'chirilgan"),
        "source",
        "face_condition",
    ]
    search_fields = ["full_name", "username", "phone_number"]
    readonly_fields = ["created_at", "link_help", "photo_preview"]
    inlines = [UserProductInline]
    date_hierarchy = "created_at"
    list_per_page = 25
    list_display_links = ["full_name"]

    def get_queryset(self, request: HttpRequest):
        return (
            super().get_queryset(request).prefetch_related("userproduct_set__product")
        )

    def get_fieldsets(self, request: HttpRequest, obj: TelegramUser | None = None):
        if obj is None:
            # Adding: only what the person at the counter actually knows.
            return (
                (
                    "Xaridor ma'lumotlari",
                    {
                        "fields": [
                            "full_name",
                            "phone_number",
                            "username",
                            "birth_date",
                            "face_condition",
                        ]
                    },
                ),
            )
        return (
            (
                "Xaridor ma'lumotlari",
                {
                    "fields": [
                        "full_name",
                        "phone_number",
                        "username",
                        "birth_date",
                        "face_condition",
                        "photo",
                        "photo_preview",
                    ]
                },
            ),
            ("Bot", {"fields": ["link_help", "is_active", "created_at"]}),
        )

    def save_model(self, request, obj, form, change):
        if not change:
            # Cards born in the CRM, not from the bot's own /start flow.
            obj.source = TelegramUser.RegistrationSource.ADMIN
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user: TelegramUser = form.instance
        new_products = [
            up.product
            for fs in formsets
            if fs.model is UserProduct
            for up in getattr(fs, "new_objects", [])
        ]
        if not new_products:
            return
        if not user.telegram_id:
            messages.info(
                request,
                "Mahsulot saqlandi. Mijoz botga ulanganida qo'llanma va "
                "eslatmalar avtomatik boradi.",
            )
            return
        for product in new_products:
            if self._send_purchase_message(user, product, greet=change):
                messages.success(
                    request,
                    f"«{product.name}» uchun tabrik va qo'llanma mijozga "
                    "botda yuborildi ✅",
                )
            else:
                messages.warning(
                    request,
                    f"«{product.name}» qo'llanmasini yuborib bo'lmadi — mijoz "
                    "botni bloklagan bo'lishi mumkin. 1-hafta eslatmasi "
                    "baribir rejalashtirilgan.",
                )

    @staticmethod
    def _send_purchase_message(user: TelegramUser, product, greet: bool = True) -> bool:
        """
        Thank the customer for the purchase and hand them the tutorial, the
        moment the seller records it — the same content the bot sends after
        self-registration, so both entry paths feel identical.

        `greet=False` when the product is assigned in the very same save that
        creates the customer: that is registration, not a purchase, so the
        "thanks for buying" line does not apply — only the tutorial does.
        """
        from apps.campaigns.models import MessageTemplate
        from bot.i18n import t
        from bot.keyboards.inline import CB_TUTORIAL_STEP, SEP
        from core.i18n import pick

        lang = user.language
        intro = ""
        parse_mode = "HTML"
        template = MessageTemplate.objects.filter(
            template_type="product_intro", is_active=True
        ).first()
        if template is not None:
            intro = template.render({"product": product, "user": user}, lang)
            parse_mode = template.parse_mode
        if not intro.strip():
            intro = t(
                "tutorial.intro_fallback",
                lang,
                product=escape(pick(product, "name", lang)),
            )

        steps = list(product.tutorial_steps.order_by("order"))
        keyboard = None
        if steps:
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": pick(step, "button_label", lang),
                            "callback_data": (
                                f"{CB_TUTORIAL_STEP}{SEP}{product.pk}{SEP}{step.pk}"
                            ),
                        }
                    ]
                    for step in steps
                ]
            }
        try:
            if greet:
                send_message(user.telegram_id, t("purchase.thanks", lang))
            send_message(
                user.telegram_id, intro, parse_mode=parse_mode, reply_markup=keyboard
            )
        except TelegramError as exc:
            logger.warning(
                "Purchase message to %s failed: %s", user.telegram_id, exc
            )
            return False
        return True

    @admin.display(description="")
    def photo_thumb(self, obj: TelegramUser) -> str:
        """A small round avatar in the list, so a face is recognisable at a glance."""
        if not (obj.photo and obj.photo.name):
            return format_html(
                '<span style="color:#d1d5db;font-size:20px">👤</span>'
            )
        return format_html(
            '<img src="{}" style="width:32px;height:32px;border-radius:50%;'
            'object-fit:cover" />',
            obj.photo.url,
        )

    @admin.display(description="Mijoz yuklagan rasm")
    def photo_preview(self, obj: TelegramUser) -> str:
        """
        The registration selfie, shown right on the card.

        Django's stock ImageField widget only offers a bare "Currently:
        <filename>" link — nothing a seller would click to actually look at
        the customer's face before handing over a product.
        """
        if not (obj.photo and obj.photo.name):
            return "Mijoz hali rasm yubormagan."
        return format_html(
            '<a href="{0}" target="_blank">'
            '<img src="{0}" style="max-width:220px;max-height:220px;'
            'border-radius:8px;object-fit:cover" /></a>',
            obj.photo.url,
        )

    @admin.display(description="Mahsulotlar")
    def products_list(self, obj: TelegramUser) -> str:
        names = [up.product.name for up in obj.userproduct_set.all()]
        return ", ".join(names) if names else "—"

    @admin.display(description="Manba", ordering="source")
    def source_badge(self, obj: TelegramUser) -> str:
        colors = {
            TelegramUser.RegistrationSource.SELF: "#6b7280",
            TelegramUser.RegistrationSource.ADMIN: "#2b42aa",
            TelegramUser.RegistrationSource.APP: "#059669",
        }
        color = colors.get(obj.source, "#6b7280")
        return format_html(
            '<span style="color:{}">{}</span>',
            color,
            obj.get_source_display(),
        )

    @admin.display(description="Bot")
    def link_badge(self, obj: TelegramUser) -> str:
        return bot_link_badge(obj.is_linked)

    @admin.display(description="Bot bilan aloqa")
    def link_help(self, obj: TelegramUser) -> str:
        if obj.is_linked:
            return format_html(
                '<span style="color:#059669;font-weight:600">✅ Mijoz botga '
                "ulangan.</span> Xabarlar unga avtomatik boradi."
            )
        return format_html(
            '<span style="color:#f59e0b;font-weight:600">⏳ Mijoz hali botga '
            "kirmagan.</span><br>Unga bot havolasini yuboring. Mijoz botda "
            "telefon raqamini yuborgach, kartasi shu yerga o'zi ulanadi — "
            "qo'lda hech nima qilish shart emas."
        )

    def has_delete_permission(
        self, request: HttpRequest, obj: TelegramUser | None = None
    ) -> bool:
        return request.user.is_superuser
