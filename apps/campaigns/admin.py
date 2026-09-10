from __future__ import annotations

import re

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html
from unfold.decorators import action

from core.admin import RBModelAdmin, yes_no_filter

from .models import (
    AutoMessage,
    AutoMessageLog,
    Broadcast,
    CampaignLog,
    MessageTemplate,
    ReminderRule,
)


@admin.register(MessageTemplate)
class MessageTemplateAdmin(RBModelAdmin):
    """
    The messages the bot sends at fixed moments, one row each.

    They are a fixed set, so this page is for editing wording only — adding a
    row or deleting one would just leave the bot with nothing to send.
    """

    # The week-1 and week-2 texts moved to "Avtomatik xabarlar", where the
    # delay is editable too. Their rows still exist (the seed migration copied
    # the wording across) but nothing reads them any more — leaving them on
    # screen would mean somebody edits one and waits for a change that never
    # comes.
    RETIRED_TYPES = ("week1_checkin", "week2_progress")

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).exclude(
            template_type__in=self.RETIRED_TYPES
        )

    list_display = ["when_sent", "preview", "active_badge", "updated_at"]
    list_display_links = ["when_sent"]
    list_filter = [
        yes_no_filter("is_active", "Yuborilishi", "Yuborilyapti", "O'chirilgan")
    ]
    search_fields = ["name", "body"]
    readonly_fields = ["template_type"]
    ordering = ["template_type"]
    fieldsets = (
        (
            "Xabar",
            {"fields": ["template_type", "name", "body", "parse_mode", "is_active"]},
        ),
        (
            "Boshqa tillar (ixtiyoriy)",
            {
                "fields": ["body_ru", "body_en"],
                "classes": ["collapse"],
                "description": "Bo'sh qoldirsangiz — mijozga o'zbekcha matn "
                "yuboriladi.",
            },
        ),
    )

    @admin.display(description="Qachon yuboriladi", ordering="template_type")
    def when_sent(self, obj: MessageTemplate) -> str:
        return obj.get_template_type_display()

    @admin.display(description="Matn")
    def preview(self, obj: MessageTemplate) -> str:
        text = re.sub(r"<[^>]+>", "", obj.body).replace("\n", " ")
        return text[:90] + ("…" if len(text) > 90 else "")

    @admin.display(description="Holat")
    def active_badge(self, obj: MessageTemplate) -> str:
        if obj.is_active:
            return format_html(
                '<span style="color:#059669;font-weight:600">✅ Yuborilyapti</span>'
            )
        return format_html('<span style="color:#9ca3af">⏸ O\'chirilgan</span>')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: MessageTemplate | None = None
    ) -> bool:
        return False

    # Sellers must not see or edit templates
    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: MessageTemplate | None = None
    ) -> bool:
        return request.user.is_superuser


class AutoMessageForm(forms.ModelForm):
    class Meta:
        model = AutoMessage
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("button_action")
        if action and action != AutoMessage.Action.NONE and not cleaned.get(
            "button_label"
        ):
            self.add_error(
                "button_label",
                "Tugma tanlandi — tugma matnini ham yozing (yoki «Tugmasiz» "
                "ni tanlang).",
            )
        if cleaned.get("is_test_mode") and not cleaned.get("test_user"):
            self.add_error(
                "test_user", "Sinov rejimi uchun mijozni tanlang."
            )
        # 4096 is Telegram's hard limit; the send fails outright above it.
        for field in ("body", "body_ru", "body_en"):
            body = cleaned.get(field) or ""
            if len(body) > 4096:
                self.add_error(
                    field, f"Matn 4096 belgidan oshmasligi kerak (hozir {len(body)})."
                )
        return cleaned


@admin.register(AutoMessage)
class AutoMessageAdmin(RBModelAdmin):
    """
    The bot's timed messages: what it says, and how long after what.

    Built around one question — "will this actually go out, and when?" — so
    every screen answers it in words rather than leaving the reader to work it
    out from a number and a unit. The pair of per-object actions is the whole
    testing story: send it to yourself now, or set the unit to minutes and
    watch it arrive.
    """

    form = AutoMessageForm
    list_display = [
        "name",
        "when_label",
        "trigger_label",
        "button_summary",
        "status_badge",
        "sent_total",
    ]
    list_display_links = ["name"]
    list_filter = [
        yes_no_filter("is_active", "Holati", "Yoqilgan", "O'chirilgan"),
        "trigger",
    ]
    search_fields = ["name", "body"]
    readonly_fields = ["plain_summary", "sent_total"]
    # A plain select would render every customer in the shop into the page.
    autocomplete_fields = ["test_user"]
    actions_detail = ["action_test_to_me"]

    fieldsets = (
        (
            "1. Nomi",
            {
                "fields": ["name"],
                "description": "Faqat siz ko'rasiz. Masalan: «1 hafta — "
                "keshbek taklifi».",
            },
        ),
        (
            "2. Qachon yuborilsin",
            {
                "fields": ["trigger", "delay_value", "delay_unit", "plain_summary"],
                "description": "Sinash uchun: birlikni «daqiqa», raqamni 1 "
                "qilib qo'ying va pastdagi «Sinov rejimi»ni yoqing.",
            },
        ),
        (
            "3. Xabar matni",
            {
                "fields": ["body"],
                "description": "Mijozga boradigan matn. {{ user.full_name }} "
                "va {{ product.name }} ishlaydi.",
            },
        ),
        (
            "3a. Boshqa tillar (ixtiyoriy)",
            {
                "fields": ["body_ru", "body_en"],
                "classes": ["collapse"],
                "description": "Bo'sh qoldirsangiz — o'zbekcha matn yuboriladi.",
            },
        ),
        (
            "4. Xabar ostidagi tugma",
            {
                "fields": [
                    "button_action",
                    "button_label",
                    "button_label_ru",
                    "button_label_en",
                ]
            },
        ),
        (
            "5. Yoqish va sinash",
            {
                "fields": ["is_active", "is_test_mode", "test_user", "sent_total"],
            },
        ),
    )

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).select_related("test_user")

    # --- read-only explanations --------------------------------------------
    @admin.display(description="Qachon")
    def when_label(self, obj: AutoMessage) -> str:
        return obj.schedule_label

    @admin.display(description="Nimadan keyin", ordering="trigger")
    def trigger_label(self, obj: AutoMessage) -> str:
        return obj.get_trigger_display()

    @admin.display(description="Tugma")
    def button_summary(self, obj: AutoMessage) -> str:
        if obj.button_action == AutoMessage.Action.NONE:
            return "—"
        return obj.button_label or obj.get_button_action_display()

    @admin.display(description="Holat")
    def status_badge(self, obj: AutoMessage) -> str:
        if not obj.is_active:
            return format_html('<span style="color:#9ca3af">⏸ O\'chirilgan</span>')
        if obj.is_test_mode:
            who = obj.test_user or "—"
            return format_html(
                '<span style="color:#f59e0b;font-weight:600">🧪 Sinov rejimi</span>'
                '<div style="font-size:11px;color:#6b7280">faqat: {}</div>',
                who,
            )
        return format_html(
            '<span style="color:#059669;font-weight:600">✅ Ishlayapti</span>'
        )

    @admin.display(description="Yuborilgan")
    def sent_total(self, obj: AutoMessage) -> str:
        if obj.pk is None:
            return "—"
        return f"{obj.logs.filter(success=True).count()} ta"

    @admin.display(description="Bu nima qiladi")
    def plain_summary(self, obj: AutoMessage) -> str:
        """One sentence saying exactly what this row will do, in Uzbek."""
        if obj.pk is None:
            return "Saqlagandan so'ng shu yerda tushuntirish chiqadi."

        what = (
            "mahsulot sotib olingandan"
            if obj.trigger == AutoMessage.Trigger.AFTER_PURCHASE
            else "ro'yxatdan o'tgandan"
        )
        # The customer's own name goes through format_html's escaping — a name
        # containing markup must not become markup on this page.
        if obj.is_test_mode:
            who = format_html("faqat <b>{}</b> ga", obj.test_user or "—")
        else:
            who = "barcha mos mijozlarga"

        sentence = format_html(
            "Bot {} keyin <b>{} {}</b> o'tgach {} shu xabarni yuboradi.",
            what,
            obj.delay_value,
            obj.get_delay_unit_display(),
            who,
        )
        if obj.is_active:
            return sentence
        return format_html("{} <b>(hozir o'chirilgan)</b>", sentence)

    # --- per-object actions -------------------------------------------------
    @action(description="✍️ Menga test yuborish")
    def action_test_to_me(self, request, object_id):
        """
        Deliver this exact message to the logged-in staff member right now.

        The one thing that answers "does the wording look right?" without
        waiting for the delay or touching a customer.
        """
        from apps.users.models import SellerProfile, TelegramUser
        from core.telegram import TelegramError, send_message

        back = request.path.replace("action_test_to_me/", "")
        rule = AutoMessage.objects.filter(pk=object_id).first()
        if rule is None:
            return redirect(back)

        profile = SellerProfile.objects.filter(user=request.user).first()
        if profile is None or not profile.telegram_id:
            self.message_user(
                request,
                "Test yuborish uchun Xodimlar → o'zingizga Telegram ID kiriting.",
                level=messages.ERROR,
            )
            return redirect(back)

        # Render against a real customer where possible, so placeholders show
        # real values instead of blanks.
        sample_user = TelegramUser.objects.filter(
            telegram_id=profile.telegram_id
        ).first() or TelegramUser.objects.filter(
            telegram_id__isnull=False
        ).first()
        lang = sample_user.language if sample_user else "uz"
        sample_product = None
        if rule.trigger == AutoMessage.Trigger.AFTER_PURCHASE:
            from apps.products.models import Product

            sample_product = Product.objects.filter(is_active=True).first()

        text = rule.render({"user": sample_user, "product": sample_product}, lang)
        keyboard = rule.keyboard_for(
            lang, sample_product.pk if sample_product else None
        )
        try:
            send_message(
                profile.telegram_id, text, parse_mode="HTML", reply_markup=keyboard
            )
        except TelegramError as exc:
            self.message_user(
                request, f"Test yuborilmadi: {exc}", level=messages.ERROR
            )
            return redirect(back)
        self.message_user(request, "Test xabar sizga yuborildi ✅ — botni tekshiring.")
        return redirect(back)

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: AutoMessage | None = None
    ) -> bool:
        return request.user.is_superuser


class ReminderRuleForm(forms.ModelForm):
    class Meta:
        model = ReminderRule
        fields = ["user", "name", "body", "interval_days", "next_run_at", "is_active"]

    def clean_user(self):
        user = self.cleaned_data["user"]
        if not user.telegram_id:
            raise forms.ValidationError(
                "Bu mijoz hali botga ulanmagan (telegram_id yo'q) — eslatma "
                "yetkazib bo'lmaydi. Mijoz botni ochgach qayta urinib ko'ring."
            )
        return user


@admin.register(ReminderRule)
class ReminderRuleAdmin(RBModelAdmin):
    """
    A recurring "every N days" nudge to one specific, bot-linked customer —
    unlike `AutoMessage`, which fires once per purchase/registration anchor.
    """

    form = ReminderRuleForm
    list_display = [
        "name",
        "user",
        "interval_days",
        "next_run_at",
        "status_badge",
        "send_count",
        "error_count",
    ]
    list_display_links = ["name"]
    list_filter = [yes_no_filter("is_active", "Holati", "Yoqilgan", "O'chirilgan")]
    search_fields = ["name", "user__full_name", "user__username"]
    readonly_fields = ["last_sent_at", "send_count", "error_count", "created_at"]
    autocomplete_fields = ["user"]

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="Holat")
    def status_badge(self, obj: ReminderRule) -> str:
        if not obj.is_active:
            return format_html('<span style="color:#9ca3af">⏸ O\'chirilgan</span>')
        return format_html(
            '<span style="color:#059669;font-weight:600">✅ Ishlayapti</span>'
        )

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser


class BroadcastForm(forms.ModelForm):
    class Meta:
        model = Broadcast
        fields = "__all__"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        from apps.users.models import TelegramUser

        # A free-text skin type would never match the stored choice values;
        # offer the same options the customer picked from.
        self.fields["skin_condition"] = forms.ChoiceField(
            required=False,
            label="Teri turi",
            choices=[("", "—")] + list(TelegramUser.FaceCondition.choices),
            help_text="«Teri turi bo'yicha» tanlansagina ishlaydi.",
        )

    def clean(self):
        cleaned = super().clean()
        # Telegram limits: 4096 chars for a message, 1024 for a photo caption.
        # Catch it here — otherwise every single send fails at blast time.
        body = cleaned.get("body") or ""
        if cleaned.get("photo") and len(body) > 1024:
            self.add_error(
                "body",
                f"Rasmli xabar matni 1024 belgidan oshmasligi kerak "
                f"(hozir {len(body)}). Matnni qisqartiring yoki rasmni olib "
                "tashlang.",
            )
        elif len(body) > 4096:
            self.add_error(
                "body",
                f"Xabar matni 4096 belgidan oshmasligi kerak (hozir {len(body)}).",
            )
        return cleaned


@admin.register(Broadcast)
class BroadcastAdmin(RBModelAdmin):
    form = BroadcastForm
    """
    Compose-and-send announcements: seminars, new arrivals, flash sales.

    Two guard rails, because a send cannot be recalled: "menga test" delivers
    the exact message to the composer first, and "hammaga yuborish" routes
    through a confirmation page showing the real recipient count.
    """

    list_display = ["title", "audience_label", "status_badge", "reach", "created_at"]
    list_display_links = ["title"]
    list_filter = ["status", "audience"]
    search_fields = ["title", "body"]
    readonly_fields = ["status", "delivery_summary", "created_at"]
    actions_detail = ["action_test_to_me", "action_send_now"]

    fieldsets = (
        (
            "Xabar",
            {
                "fields": ["title", "body", "photo"],
                "description": "Avval matnni yozing, «Saqlash»dan so'ng test "
                "qilib, keyin yuboring.",
            },
        ),
        ("Holat", {"fields": ["status", "delivery_summary", "created_at"]}),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        # Once sent, the content is frozen — editing it would misrepresent what
        # customers actually received.
        if obj and obj.status in (
            Broadcast.Status.SENDING,
            Broadcast.Status.SENT,
        ):
            fields += ["title", "body", "photo"]
        return fields

    @admin.display(description="Kimlarga")
    def audience_label(self, obj: Broadcast) -> str:
        base = obj.get_audience_display().split(" (")[0]
        if obj.audience == Broadcast.Audience.BY_SKIN and obj.skin_condition:
            return f"{base}: {obj.skin_condition}"
        if obj.audience == Broadcast.Audience.BY_PRODUCT and obj.product:
            return f"{base}: {obj.product.name}"
        return base

    @admin.display(description="Holat")
    def status_badge(self, obj: Broadcast) -> str:
        colors = {
            Broadcast.Status.DRAFT: ("#6b7280", "📝 Qoralama"),
            Broadcast.Status.SENDING: ("#f59e0b", "⏳ Yuborilmoqda…"),
            Broadcast.Status.SENT: ("#059669", "✅ Yuborildi"),
            Broadcast.Status.FAILED: ("#dc2626", "❌ Xato"),
        }
        color, label = colors.get(obj.status, ("#6b7280", obj.status))
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, label)

    @admin.display(description="Yetib bordi")
    def reach(self, obj: Broadcast) -> str:
        if obj.status == Broadcast.Status.SENT:
            out = f"{obj.sent_count} ta"
            if obj.failed_count:
                out += f" ({obj.failed_count} yetmadi)"
            return out
        return "—"

    @admin.display(description="Yuborish natijasi")
    def delivery_summary(self, obj: Broadcast) -> str:
        if obj.pk is None:
            return "—"
        if obj.status == Broadcast.Status.DRAFT:
            count = obj.recipients().count()
            return format_html(
                'Hozircha yuborilmagan. <b>{}</b> ta xaridorga yetib boradi.', count
            )
        if obj.status == Broadcast.Status.SENDING:
            return "⏳ Yuborilmoqda… Sahifani biroz o'tib yangilang."
        if obj.status == Broadcast.Status.SENT:
            return format_html(
                "✅ {} ta yuborildi, {} ta yetmadi (bloklagan yoki botni "
                "o'chirgan).",
                obj.sent_count,
                obj.failed_count,
            )
        return "❌ Yuborishda xatolik. Qayta urinib ko'ring."

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # --- per-object actions -------------------------------------------------

    @action(description="✍️ Menga test yuborish")
    def action_test_to_me(self, request, object_id):
        from apps.users.models import SellerProfile
        from tasks.broadcast import send_test

        profile = SellerProfile.objects.filter(user=request.user).first()
        if profile is None or not profile.telegram_id:
            self.message_user(
                request,
                "Sizga test yuborish uchun Xodimlar → o'zingizga Telegram ID "
                "kiriting.",
                level=messages.ERROR,
            )
            return redirect(request.path.replace("action_test_to_me/", ""))

        try:
            ok, error = send_test(int(object_id), profile.telegram_id)
        except Exception as exc:  # noqa: BLE001
            ok, error = False, str(exc)
        if ok:
            self.message_user(request, "Test xabar sizga yuborildi ✅ — botni tekshiring.")
        else:
            self.message_user(
                request, f"Test yuborilmadi: {error}", level=messages.ERROR
            )
        return redirect(request.path.replace("action_test_to_me/", ""))

    @action(description="📣 Hammaga yuborish")
    def action_send_now(self, request, object_id):
        from tasks.broadcast import send_broadcast

        broadcast = Broadcast.objects.get(pk=object_id)
        change_url = reverse(
            "admin:campaigns_broadcast_change", args=[object_id]
        )

        if broadcast.status in (Broadcast.Status.SENDING, Broadcast.Status.SENT):
            self.message_user(
                request, "Bu e'lon allaqachon yuborilgan.", level=messages.WARNING
            )
            return redirect(change_url)

        # POST from the confirmation page = go. GET = show the page first.
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            send_broadcast.delay(broadcast.pk)
            self.message_user(
                request,
                "📣 Yuborish boshlandi. Bir necha daqiqada holat «Yuborildi» "
                "bo'ladi — sahifani yangilab turing.",
            )
            return redirect(change_url)

        count = broadcast.recipients().count()
        return render(
            request,
            "admin/campaigns/broadcast_confirm.html",
            {
                "broadcast": broadcast,
                "count": count,
                "title": "E'lonni yuborish",
                "back_url": change_url,
                **self.admin_site.each_context(request),
            },
        )
