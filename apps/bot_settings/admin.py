from __future__ import annotations

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from core.admin import RBModelAdmin, yes_no_filter

from .models import Discount, GlobalSettings


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(RBModelAdmin):
    """
    A single row of settings, edited as a plain form.

    There is nothing to list — a changelist holding exactly one link makes the
    sidebar entry look broken, so the changelist forwards straight to the form.
    """

    fieldsets = (
        (
            "Tug'ilgan kun",
            {
                "fields": ["birthday_discount_percent"],
                "description": "Avtomatik xabarlar (1-hafta, 2-hafta va "
                "boshqalar) endi «Marketing → Avtomatik xabarlar» bo'limida "
                "sozlanadi.",
            },
        ),
        (
            "Do'kon (Mini App)",
            {
                "fields": [
                    "shop_name",
                    "shop_tagline",
                    "shop_tagline_ru",
                    "shop_tagline_en",
                    "instagram_url",
                    "youtube_url",
                    "telegram_url",
                ],
                "description": "Mini App'da ko'rinadigan nom, shior va ijtimoiy "
                "tarmoq havolalari. Bo'sh havola — o'sha tugma yashiriladi.",
            },
        ),
    )

    def changelist_view(self, request: HttpRequest, extra_context=None) -> HttpResponse:
        # The redirect skips the stock changelist (and its permission check),
        # so the check has to happen here — otherwise a seller's visit both
        # 403s confusingly *after* a redirect and creates the settings row.
        if not self.has_view_permission(request):
            raise PermissionDenied
        settings = GlobalSettings.get()
        return HttpResponseRedirect(
            reverse("admin:bot_settings_globalsettings_change", args=[settings.pk])
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: GlobalSettings | None = None
    ) -> bool:
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: GlobalSettings | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: GlobalSettings | None = None
    ) -> bool:
        return request.user.is_superuser


@admin.register(Discount)
class DiscountAdmin(RBModelAdmin):
    list_display = ["title", "percent", "promo_code", "state_badge", "valid_until"]
    list_display_links = ["title"]
    list_filter = [
        yes_no_filter("is_active", "Chegirma holati", "Faol", "O'chirilgan")
    ]
    search_fields = ["title", "promo_code", "description"]
    fields = [
        "title",
        "percent",
        "description",
        "promo_code",
        "valid_until",
        "is_active",
    ]

    @admin.display(description="Holat")
    def state_badge(self, obj: Discount) -> str:
        if obj.is_valid:
            return format_html(
                '<span style="color:#059669;font-weight:600">✅ Botda ko\'rinadi</span>'
            )
        if not obj.is_active:
            return format_html('<span style="color:#9ca3af">⏸ O\'chirilgan</span>')
        # Active but past its date — the bot hides it silently, so say so here.
        return format_html('<span style="color:#dc2626">⌛ Muddati tugagan</span>')

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: Discount | None = None
    ) -> bool:
        return request.user.is_superuser
