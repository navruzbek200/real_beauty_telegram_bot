"""
App foydalanuvchilari — customers who registered through the Flutter app.

These rows already appear on "Xaridorlar" with a "Mobil ilova" badge, but that
page mixes every source together; whoever watches app sign-ups should not have
to set a filter each time they look. This page is that filter, made permanent.

It is deliberately read-mostly: the app owns these records, so the only thing
staff do here is fix a name or a phone number that was typed wrong.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin
from django.http import HttpRequest

from core.admin import RBModelAdmin, bot_link_badge, yes_no_filter

from .forms import PhoneNumberUniqueMixin
from .models import AppUser


class AppUserForm(PhoneNumberUniqueMixin, forms.ModelForm):
    """
    Typo repair only.

    Everything else on the card — teri turi, tug'ilgan sana, rasm — the customer
    fills in from the app itself, so offering those boxes here would invite
    staff to overwrite what the customer just entered.
    """

    class Meta:
        model = AppUser
        fields = ["full_name", "phone_number"]
        labels = {
            "full_name": "Ism-familiya",
            "phone_number": "Telefon raqami",
        }
        help_texts = {
            "phone_number": "Masalan: +998 90 123 45 67. "
            "Faqat xato yozilgan raqamni to'g'rilash uchun.",
        }


@admin.register(AppUser)
class AppUserAdmin(RBModelAdmin):
    form = AppUserForm
    list_display = [
        "full_name",
        "phone_number",
        "link_badge",
        "registration_status",
        "created_at",
    ]
    list_display_links = ["full_name"]
    list_filter = [yes_no_filter("is_active", "Xaridor holati", "Faol", "O'chirilgan")]
    search_fields = ["full_name", "phone_number"]
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        ("Foydalanuvchi ma'lumotlari", {"fields": ["full_name", "phone_number"]}),
    )

    @admin.display(description="Bot")
    def link_badge(self, obj: AppUser) -> str:
        return bot_link_badge(obj.is_linked)

    def has_add_permission(self, request: HttpRequest) -> bool:
        # App accounts are born in the app's registration flow, which is what
        # sets source=APP. A card added by hand here would be an admin card
        # sitting on the app page and lying about where it came from — manual
        # entry belongs on "Xaridorlar".
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: AppUser | None = None
    ) -> bool:
        return request.user.is_superuser
