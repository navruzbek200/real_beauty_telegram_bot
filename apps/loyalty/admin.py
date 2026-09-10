"""
Admin for the bonus program.

The shop owner tunes the whole points economy here — how many points each
action is worth, the tier ladder and its cashback, and the rewards points buy —
and can watch every balance and movement. Nothing on these pages is required for
the bot to run; leaving them alone keeps the defaults.
"""

from __future__ import annotations

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from core.admin import RBModelAdmin, yes_no_filter

from .models import (
    LoyaltyAccount,
    LoyaltySettings,
    PointsTransaction,
    Reward,
    RewardRedemption,
)


@admin.register(LoyaltySettings)
class LoyaltySettingsAdmin(RBModelAdmin):
    """One row — the whole economy on a single form (see GlobalSettingsAdmin)."""

    fieldsets = (
        (
            "Dastur",
            {"fields": ["is_enabled"]},
        ),
        (
            "Ball miqdorlari",
            {
                "fields": [
                    "points_registration",
                    "points_referral",
                    "points_purchase",
                    "points_quiz",
                    "points_feedback",
                    "points_progress",
                    "points_birthday",
                ],
                "description": "Har bir amal uchun beriladigan ball. 0 qilib "
                "qo'ysangiz — o'sha amal uchun ball berilmaydi.",
            },
        ),
        (
            "Darajalar va keshbek",
            {
                "fields": [
                    "bronze_cashback",
                    "silver_from",
                    "silver_cashback",
                    "gold_from",
                    "gold_cashback",
                    "platinum_from",
                    "platinum_cashback",
                ],
                "description": "Daraja jami yig'ilgan ballga qarab beriladi. "
                "Chegaralar ortib borishi kerak: Kumush < Oltin < Platina.",
            },
        ),
    )

    def changelist_view(
        self, request: HttpRequest, extra_context=None
    ) -> HttpResponse:
        if not self.has_view_permission(request):
            raise PermissionDenied
        settings = LoyaltySettings.get()
        return HttpResponseRedirect(
            reverse("admin:loyalty_loyaltysettings_change", args=[settings.pk])
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: LoyaltySettings | None = None
    ) -> bool:
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: LoyaltySettings | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: LoyaltySettings | None = None
    ) -> bool:
        return request.user.is_superuser


@admin.register(Reward)
class RewardAdmin(RBModelAdmin):
    list_display = ["title", "cost_points", "stock_badge", "state_badge"]
    list_display_links = ["title"]
    list_filter = [yes_no_filter("is_active", "Holat", "Faol", "O'chirilgan")]
    search_fields = ["title", "title_ru", "title_en", "description"]
    fieldsets = (
        (
            "Sovg'a",
            {
                "fields": [
                    "title",
                    "title_ru",
                    "title_en",
                    "description",
                    "description_ru",
                    "description_en",
                ]
            },
        ),
        (
            "Shartlar",
            {
                "fields": ["cost_points", "code_prefix", "stock", "is_active"],
                "description": "«Nechta qoldi» bo'sh bo'lsa — cheklanmagan.",
            },
        ),
    )

    @admin.display(description="Qoldiq")
    def stock_badge(self, obj: Reward) -> str:
        if obj.stock is None:
            return "∞"
        return str(obj.stock)

    @admin.display(description="Holat")
    def state_badge(self, obj: Reward) -> str:
        if obj.is_available:
            return format_html(
                '<span style="color:#059669;font-weight:600">✅ Botda ko\'rinadi</span>'
            )
        return format_html('<span style="color:#9ca3af">⏸ Yashirilgan</span>')

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: Reward | None = None
    ) -> bool:
        return request.user.is_superuser


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(RBModelAdmin):
    list_display = ["user", "balance", "lifetime_points", "tier", "updated_at"]
    list_display_links = ["user"]
    list_filter = ["tier"]
    search_fields = ["user__full_name", "user__phone_number", "user__username"]
    readonly_fields = ["user", "lifetime_points", "tier", "updated_at"]
    ordering = ["-lifetime_points"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: LoyaltyAccount | None = None
    ) -> bool:
        return request.user.is_superuser


@admin.register(PointsTransaction)
class PointsTransactionAdmin(RBModelAdmin):
    """Read-only audit log — points only ever move through the service layer."""

    list_display = ["created_at", "user", "points", "reason", "note"]
    list_filter = ["reason"]
    search_fields = ["user__full_name", "user__phone_number", "note"]
    readonly_fields = ["user", "points", "reason", "reference", "note", "created_at"]
    ordering = ["-created_at"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: PointsTransaction | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: PointsTransaction | None = None
    ) -> bool:
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: PointsTransaction | None = None
    ) -> bool:
        return request.user.is_superuser


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(RBModelAdmin):
    list_display = ["created_at", "user", "reward", "code", "used_badge"]
    list_filter = [yes_no_filter("is_used", "Holat", "Ishlatilgan", "Kutilmoqda")]
    search_fields = ["code", "user__full_name", "user__phone_number"]
    readonly_fields = [
        "user",
        "reward",
        "code",
        "points_spent",
        "created_at",
        "used_at",
    ]
    fields = [
        "user",
        "reward",
        "code",
        "points_spent",
        "is_used",
        "used_at",
        "created_at",
    ]
    ordering = ["-created_at"]

    @admin.display(description="Holat")
    def used_badge(self, obj: RewardRedemption) -> str:
        if obj.is_used:
            return format_html('<span style="color:#059669">✅ Ishlatilgan</span>')
        return format_html('<span style="color:#f59e0b">⏳ Kutilmoqda</span>')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: RewardRedemption | None = None
    ) -> bool:
        return request.user.is_superuser
