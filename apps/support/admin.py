from __future__ import annotations

import logging

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.timezone import localtime
from unfold.decorators import action

from core.admin import RBModelAdmin, yes_no_filter
from core.telegram import TelegramError, call as telegram_call

from .models import SupportAdmin, SupportMessage, SupportSettings, SupportThread

logger = logging.getLogger(__name__)

_ATTACHMENT_CHIP_LABELS = {
    SupportMessage.AttachmentType.DOCUMENT: "📄 Hujjat — ochish",
    SupportMessage.AttachmentType.STICKER: "🖼 Stiker — ochish",
}


def _attachment_html(msg: SupportMessage) -> str:
    """
    Photo/video/voice render inline (an admin should see at a glance what a
    customer sent, not guess from a bare "ochish" link); document/sticker
    stay a clearly labelled chip — Telegram documents have no safe generic
    preview, and stickers are frequently animated (.tgs), which an <img>
    can't render at all.
    """
    if not msg.attachment_file_id:
        return ""
    url = reverse("telegram_file", args=[msg.attachment_file_id])
    if msg.attachment_type == SupportMessage.AttachmentType.PHOTO:
        return format_html(
            '<a href="{0}" target="_blank" class="rb-chat__media-link">'
            '<img src="{0}" loading="lazy" class="rb-chat__img" alt="Rasm"></a>',
            url,
        )
    if msg.attachment_type == SupportMessage.AttachmentType.VIDEO:
        return format_html(
            '<video src="{}" controls preload="metadata" '
            'class="rb-chat__video"></video>',
            url,
        )
    if msg.attachment_type == SupportMessage.AttachmentType.VOICE:
        return format_html(
            '<audio src="{}" controls class="rb-chat__audio"></audio>', url
        )
    label = _ATTACHMENT_CHIP_LABELS.get(msg.attachment_type, "📎 Fayl — ochish")
    return format_html(
        '<a href="{}" target="_blank" class="rb-chat__file-chip">{}</a>', url, label
    )


@admin.register(SupportThread)
class SupportThreadAdmin(RBModelAdmin):
    """
    Read-only conversation history.

    Replies no longer happen here — admins reply inside the Telegram support
    group and the bot routes them back automatically. This page stays so
    staff can search/skim past conversations and manually close stale ones.
    """

    list_display = ["user", "subject", "preview", "state_badge", "last_message_at"]
    list_filter = [
        yes_no_filter(
            "awaiting_reply", "Javob kerakmi", "Javob kutmoqda", "Javob berilgan"
        ),
        "status",
    ]
    search_fields = ["user__full_name", "user__username", "subject", "messages__text"]
    date_hierarchy = "last_message_at"
    list_per_page = 30
    list_display_links = ["user", "subject"]
    fields = ["conversation", "status"]
    readonly_fields = ["conversation"]

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="Oxirgi xabar")
    def preview(self, obj: SupportThread) -> str:
        last = obj.messages.last()
        if last is None:
            return "—"
        arrow = "←" if last.direction == SupportMessage.Direction.IN else "→"
        text = last.text or "📎 fayl"
        return f"{arrow} {text[:60]}"

    @admin.display(description="Holat")
    def state_badge(self, obj: SupportThread) -> str:
        if obj.awaiting_reply:
            return format_html(
                '<span style="color:#dc2626;font-weight:600">🔴 Javob kutmoqda</span>'
            )
        if obj.status == SupportThread.Status.CLOSED:
            return format_html('<span style="color:#9ca3af">✔ Yopilgan</span>')
        return format_html('<span style="color:#059669">✅ Javob berildi</span>')

    @admin.display(description="Yozishmalar")
    def conversation(self, obj: SupportThread) -> str:
        """
        Rendered with rb-chat CSS classes (core/static/css/admin.css), not
        inline colors — a hardcoded light background with no matching text
        color used to turn invisible-on-invisible the moment someone switched
        the admin to dark mode.
        """
        if obj.pk is None:
            return "—"
        rows = []
        for msg in obj.messages.select_related("author", "telegram_admin"):
            incoming = msg.direction == SupportMessage.Direction.IN
            who = (
                (obj.user.full_name or str(obj.user.telegram_id))
                if incoming
                else str(msg.telegram_admin or msg.author or "Admin")
            )
            text_html = (
                format_html('<div class="rb-chat__text">{}</div>', msg.text)
                if msg.text
                else ""
            )
            error_html = (
                format_html(
                    '<div class="rb-chat__error">⚠️ Yuborilmadi: {}</div>',
                    msg.error_detail,
                )
                if msg.status == SupportMessage.Status.FAILED
                else ""
            )
            body = format_html(
                "{}{}{}", text_html, _attachment_html(msg), error_html
            )
            rows.append(
                (
                    "rb-chat__row--in" if incoming else "rb-chat__row--out",
                    who,
                    localtime(msg.created_at).strftime("%d.%m.%Y %H:%M"),
                    body,
                )
            )
        if not rows:
            return "—"
        return format_html(
            '<div class="rb-chat">{}</div>',
            format_html_join(
                "",
                '<div class="rb-chat__row {}"><div class="rb-chat__bubble">'
                '<div class="rb-chat__meta">{} · {}</div>{}</div></div>',
                rows,
            ),
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: SupportThread | None = None
    ) -> bool:
        return request.user.is_superuser


def _mask_token(token: str) -> str:
    if not token:
        return "— sozlanmagan (BOT_TOKEN) —"
    if ":" not in token or len(token) < 10:
        return "••••••••"
    bot_id, _, secret = token.partition(":")
    return f"{bot_id}:{secret[:4]}••••••{secret[-4:]}"


@admin.register(SupportSettings)
class SupportSettingsAdmin(RBModelAdmin):
    """
    Single row of settings, edited as a plain form — same pattern as
    GlobalSettingsAdmin (a changelist with one link looks broken, so it
    forwards straight to the form).
    """

    fields = ["bot_token_display", "group_chat_id", "connection_status_display"]
    readonly_fields = ["bot_token_display", "connection_status_display"]
    actions_detail = ["action_test_connection"]

    @admin.display(description="Bot token")
    def bot_token_display(self, obj: SupportSettings) -> str:
        from django.conf import settings as dj_settings

        return _mask_token(dj_settings.BOT_TOKEN)

    @admin.display(description="Ulanish holati")
    def connection_status_display(self, obj: SupportSettings) -> str:
        checked = (
            localtime(obj.last_checked_at).strftime("%d.%m.%Y %H:%M")
            if obj.last_checked_at
            else "hali tekshirilmagan"
        )
        if obj.connection_status == SupportSettings.ConnectionStatus.OK:
            badge = format_html(
                '<span style="color:#059669;font-weight:600">✅ Ulangan</span>'
            )
        elif obj.connection_status == SupportSettings.ConnectionStatus.ERROR:
            badge = format_html(
                '<span style="color:#dc2626;font-weight:600">❌ Xatolik: {}</span>',
                obj.last_error,
            )
        else:
            badge = format_html('<span style="color:#9ca3af">⏺ Tekshirilmagan</span>')
        return format_html("{}<div style='font-size:12px;color:#6b7280'>{}</div>", badge, checked)

    @action(description="🔌 Ulanishni tekshirish")
    def action_test_connection(self, request: HttpRequest, object_id):
        obj = SupportSettings.objects.get(pk=object_id)
        if not obj.group_chat_id:
            self.message_user(
                request, "Avval Guruh Chat ID ni kiriting.", level=messages.ERROR
            )
            return HttpResponseRedirect(
                request.path.replace("action_test_connection/", "")
            )
        obj.last_checked_at = timezone.now()
        try:
            telegram_call("getChat", {"chat_id": obj.group_chat_id})
        except TelegramError as exc:
            obj.connection_status = SupportSettings.ConnectionStatus.ERROR
            obj.last_error = str(exc)
            obj.save(update_fields=["connection_status", "last_error", "last_checked_at"])
            self.message_user(request, f"Ulanmadi: {exc}", level=messages.ERROR)
        else:
            obj.connection_status = SupportSettings.ConnectionStatus.OK
            obj.last_error = ""
            obj.save(update_fields=["connection_status", "last_error", "last_checked_at"])
            self.message_user(request, "Guruhga ulanish muvaffaqiyatli ✅")
        return HttpResponseRedirect(
            request.path.replace("action_test_connection/", "")
        )

    def changelist_view(self, request: HttpRequest, extra_context=None):
        from django.core.exceptions import PermissionDenied

        if not self.has_view_permission(request):
            raise PermissionDenied
        settings_obj = SupportSettings.get()
        return HttpResponseRedirect(
            reverse("admin:support_supportsettings_change", args=[settings_obj.pk])
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: SupportSettings | None = None
    ) -> bool:
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: SupportSettings | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: SupportSettings | None = None
    ) -> bool:
        return request.user.is_superuser


@admin.register(SupportAdmin)
class SupportAdminAdmin(RBModelAdmin):
    list_display = ["name_or_id", "telegram_user_id", "enabled_badge", "created_at"]
    list_display_links = ["name_or_id"]
    list_filter = [yes_no_filter("enabled", "Holati", "Faol", "O'chirilgan")]
    search_fields = ["telegram_user_id", "name"]
    fields = ["telegram_user_id", "name", "enabled"]

    @admin.display(description="Ism")
    def name_or_id(self, obj: SupportAdmin) -> str:
        return obj.name or str(obj.telegram_user_id)

    @admin.display(description="Holati")
    def enabled_badge(self, obj: SupportAdmin) -> str:
        if obj.enabled:
            return format_html('<span style="color:#059669">✅ Faol</span>')
        return format_html('<span style="color:#9ca3af">⏸ O\'chirilgan</span>')

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: SupportAdmin | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: SupportAdmin | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: SupportAdmin | None = None
    ) -> bool:
        return request.user.is_superuser
