"""
Admin for the gated video course.

Three pages: the videos themselves, the words that open them, and the list of
customers who have opened them. The last one is read-only — it is a record of
something that happened, not a setting.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest
from django.utils.html import format_html

from core.admin import RBModelAdmin, yes_no_filter

from .models import AccessCode, LessonUnlock, LessonVideo, generate_code
from .widgets import TELEGRAM_MAX_MB, VideoDropWidget


class LessonVideoForm(forms.ModelForm):
    class Meta:
        model = LessonVideo
        fields = "__all__"
        widgets = {"video_file": VideoDropWidget}

    def clean_video_file(self):
        f = self.cleaned_data.get("video_file")
        # Only a freshly chosen file has a size to check; an untouched field
        # hands back the stored FieldFile, which is already known to be fine.
        if f and hasattr(f, "size") and f.size > TELEGRAM_MAX_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"Fayl {f.size / 1048576:.1f} MB. Telegram bot orqali "
                f"{TELEGRAM_MAX_MB} MB gacha yuborish mumkin — videoni siqing."
            )
        return f


@admin.register(LessonVideo)
class LessonVideoAdmin(RBModelAdmin):
    form = LessonVideoForm
    list_display = ["order", "title", "video_state", "is_active"]
    list_display_links = ["title"]
    list_editable = ["order"]
    list_filter = [yes_no_filter("is_active", "Holat", "Faol", "Yashirilgan")]
    search_fields = ["title", "title_ru", "title_en"]
    ordering = ["order", "id"]

    fieldsets = (
        (
            "Video",
            {
                "fields": ["video_file", "video_file_id"],
                "description": "Faylni tashlang yoki bosib tanlang. Birinchi marta "
                "mijozga yuborilgach bot Telegram ID'ni o'zi saqlab qo'yadi — "
                "keyingi yuborishlar bir zumda bo'ladi.",
            },
        ),
        (
            "Sarlavha",
            {
                "fields": ["title", "description", "order", "is_active"],
                "description": "Mijoz «Darslar» bo'limida shuni ko'radi.",
            },
        ),
        (
            "Ruscha / inglizcha (ixtiyoriy)",
            {
                "classes": ["collapse"],
                "fields": ["title_ru", "description_ru", "title_en", "description_en"],
                "description": "Bo'sh qoldirsangiz o'zbekcha matn ko'rsatiladi.",
            },
        ),
    )

    @admin.display(description="Video")
    def video_state(self, obj: LessonVideo) -> str:
        if obj.video_file_id:
            return format_html(
                '<span style="color:#059669">✅ Telegramda keshlangan</span>'
            )
        if obj.video_file and obj.video_file.name:
            return format_html('<span style="color:#2c7d9b">⬆️ Yuklangan</span>')
        return format_html('<span style="color:#c2410c">⚠️ Video yo‘q</span>')


class AccessCodeForm(forms.ModelForm):
    class Meta:
        model = AccessCode
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A blank field on a new code is a dead end — the shop has to invent a
        # word before it can save. Offering one it can overwrite is faster and
        # produces codes that are actually hard to guess.
        if not self.instance.pk and not self.initial.get("code"):
            self.fields["code"].initial = generate_code()


@admin.register(AccessCode)
class AccessCodeAdmin(RBModelAdmin):
    form = AccessCodeForm
    list_display = ["code_badge", "label", "usage", "state", "created_at"]
    list_display_links = ["code_badge"]
    list_filter = [yes_no_filter("is_active", "Holat", "Faol", "O'chirilgan")]
    search_fields = ["code", "label"]
    readonly_fields = ["uses_count", "created_at"]
    actions = ["activate", "deactivate"]

    fieldsets = (
        (
            "Kalit so'z",
            {
                "fields": ["code", "label", "is_active"],
                "description": "Mijoz shu so'zni «Darslar» bo'limiga kiritadi. "
                "Katta-kichik harf va tirelar ahamiyatsiz.",
            },
        ),
        (
            "Cheklovlar",
            {
                "fields": ["max_uses", "expires_at", "uses_count", "created_at"],
                "description": "Bitta mijozga bermoqchi bo'lsangiz «Nechta mijozga» = 1 "
                "qiling. Butun aksiya uchun 0 qoldiring.",
            },
        ),
    )

    @admin.display(description="Kalit so'z", ordering="code")
    def code_badge(self, obj: AccessCode) -> str:
        return format_html(
            '<code style="font-size:14px;letter-spacing:.09em;font-weight:700;'
            'background:rgba(110,198,217,.18);color:#2c7d9b;padding:3px 9px;'
            'border-radius:6px">{}</code>',
            obj.code,
        )

    @admin.display(description="Ishlatilgan")
    def usage(self, obj: AccessCode) -> str:
        limit = obj.max_uses or "∞"
        return f"{obj.uses_count} / {limit}"

    @admin.display(description="Holat")
    def state(self, obj: AccessCode) -> str:
        if not obj.is_active:
            return format_html('<span style="color:#6b7280">O‘chirilgan</span>')
        if obj.is_expired:
            return format_html('<span style="color:#c2410c">Muddati tugagan</span>')
        if obj.is_spent:
            return format_html('<span style="color:#c2410c">Tugagan</span>')
        return format_html('<span style="color:#059669">✅ Ishlaydi</span>')

    @admin.action(description="🟢 Yoqish")
    def activate(self, request: HttpRequest, queryset) -> None:
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} ta kalit yoqildi.", messages.SUCCESS)

    @admin.action(description="🔴 O‘chirish")
    def deactivate(self, request: HttpRequest, queryset) -> None:
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} ta kalit o‘chirildi.", messages.SUCCESS)


@admin.register(LessonUnlock)
class LessonUnlockAdmin(RBModelAdmin):
    list_display = ["user", "code", "unlocked_at"]
    search_fields = ["user__full_name", "user__phone_number", "code__code"]
    readonly_fields = ["user", "code", "unlocked_at"]
    ordering = ["-unlocked_at"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
