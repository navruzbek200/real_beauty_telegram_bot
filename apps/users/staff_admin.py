"""
Staff accounts — the people who log into this CRM.

Django's stock user admin is a permissions console: raw permission pickers,
English column names, and a "Users" label that reads as if it meant customers.
For this shop there are only two kinds of account, so the page is reduced to
that choice plus the seller's Telegram link.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.utils.html import format_html
from unfold.admin import StackedInline

from core.admin import RBModelAdmin, yes_no_filter
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import SellerProfile, Staff
from .roles import sync_seller_group


class SellerProfileInline(StackedInline):
    model = SellerProfile
    extra = 0
    can_delete = True
    verbose_name = "Sotuvchi sozlamasi"
    verbose_name_plural = "Sotuvchi sozlamasi"
    fields = ["telegram_id", "display_name", "is_active", "invite_link_display"]
    readonly_fields = ["invite_link_display"]

    @admin.display(description="Referal havola")
    def invite_link_display(self, obj: SellerProfile) -> str:
        if not obj.pk or not obj.telegram_id:
            return "Telegram ID kiritib saqlang — havola shu yerda chiqadi."
        return format_html(
            '<code style="font-size:13px">{}</code><br>'
            '<span style="color:#6b7280;font-size:12px">Shu havolani '
            "xaridorga yuboring — u orqali kelgan mijozlar shu sotuvchiga "
            "biriktiriladi.</span>",
            obj.invite_link,
        )


class StaffForm(UserChangeForm):
    """Replaces the permission matrix with one plain question."""

    ROLE_ADMIN = "admin"
    ROLE_SELLER = "seller"

    role = forms.ChoiceField(
        label="Roli",
        choices=[
            (ROLE_SELLER, "Sotuvchi — faqat xaridorlar va murojaatlar"),
            (ROLE_ADMIN, "Administrator — hamma narsaga ruxsat"),
        ],
        widget=forms.RadioSelect,
        help_text="Sotuvchi sozlamalar, shablonlar va chegirmalarni ko'ra olmaydi.",
    )

    class Meta(UserChangeForm.Meta):
        model = Staff
        fields = ["username", "first_name", "last_name", "role", "is_active"]
        labels = {
            "username": "Login",
            "first_name": "Ism",
            "last_name": "Familiya",
            "is_active": "Faol (o'chirilsa CRM'ga kira olmaydi)",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["role"].initial = (
                self.ROLE_ADMIN if self.instance.is_superuser else self.ROLE_SELLER
            )

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        # Everyone on this page logs into the admin; the role only decides how
        # far they get once inside.
        user.is_staff = True
        user.is_superuser = self.cleaned_data["role"] == self.ROLE_ADMIN
        if commit:
            user.save()
            self.save_m2m()
        return user


class StaffCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Staff
        fields = ["username"]
        labels = {"username": "Login"}

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        # Without this a brand-new account cannot log in at all — the admin
        # would hand you a staff member who is locked out of the CRM.
        user.is_staff = True
        if commit:
            user.save()
        return user


# Django's own user page is replaced by the Staff proxy below.
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(Staff)
class StaffAdmin(UserAdmin, RBModelAdmin):
    form = StaffForm
    add_form = StaffCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ["login_name", "person_name", "role_badge", "active_badge"]
    list_display_links = ["login_name"]
    list_filter = [
        yes_no_filter("is_superuser", "Roli", "Administrator", "Sotuvchi"),
        yes_no_filter("is_active", "Kirish", "Faol", "Kira olmaydi"),
    ]
    search_fields = ["username", "first_name", "last_name"]
    ordering = ["username"]
    inlines = [SellerProfileInline]
    filter_horizontal = ()

    fieldsets = (
        ("Kirish", {"fields": ["username", "password"]}),
        ("Xodim", {"fields": ["first_name", "last_name"]}),
        ("Ruxsat", {"fields": ["role", "is_active"]}),
    )
    add_fieldsets = (
        (
            "Yangi xodim",
            {
                "fields": ["username", "password1", "password2"],
                "description": "Saqlagach roli va ismini kiritasiz.",
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Group membership carries the seller's actual permissions. It has to
        # happen here: the admin calls form.save(commit=False), so any m2m work
        # inside the form itself would never run.
        group = sync_seller_group()
        if obj.is_superuser:
            obj.groups.remove(group)
        else:
            obj.groups.add(group)

    def get_inline_instances(self, request: HttpRequest, obj=None):
        # The Telegram link belongs to an account that exists; on the add page
        # it would only be an extra empty box to scroll past.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    @admin.display(description="Login", ordering="username")
    def login_name(self, obj: Staff) -> str:
        return obj.username

    @admin.display(description="Ism")
    def person_name(self, obj: Staff) -> str:
        return obj.get_full_name() or "—"

    @admin.display(description="Roli")
    def role_badge(self, obj: Staff) -> str:
        if obj.is_superuser:
            return format_html(
                '<span style="color:#2b42aa;font-weight:600">Administrator</span>'
            )
        return format_html('<span style="color:#6b7280">Sotuvchi</span>')

    @admin.display(description="Holat")
    def active_badge(self, obj: Staff) -> str:
        if obj.is_active:
            return format_html('<span style="color:#059669">✅ Faol</span>')
        return format_html('<span style="color:#dc2626">⛔️ Kira olmaydi</span>')

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(self, request: HttpRequest, obj: Staff | None = None) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: Staff | None = None
    ) -> bool:
        # Deleting yourself locks you out; deactivate instead.
        if obj is not None and obj.pk == request.user.pk:
            return False
        return request.user.is_superuser
