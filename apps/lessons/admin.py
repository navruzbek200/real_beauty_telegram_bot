"""
Admin for the gated video course.

Three pages: the videos themselves, the words that open them, and the list of
customers who have opened them. The last one is read-only — it is a record of
something that happened, not a setting.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from django.utils import timezone

from core.admin import RBModelAdmin, yes_no_filter

from .models import AccessCode, LessonUnlock, LessonVideo, generate_code


class CodeStateFilter(admin.SimpleListFilter):
    """The question a seller actually asks: which codes can I still hand out?

    A plain is_active filter cannot answer it — a code can be active and
    already spent, which is the state most of them end up in.
    """

    title = "Holati"
    parameter_name = "state"

    def lookups(self, request, model_admin):
        return [
            ("free", "Ishlatilmagan — berish mumkin"),
            ("used", "Ishlatilgan"),
            ("expired", "Muddati tugagan"),
            ("off", "O'chirilgan"),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        value = self.value()
        if value == "free":
            return queryset.filter(is_active=True, uses_count=0).exclude(
                expires_at__lte=now
            )
        if value == "used":
            return queryset.filter(uses_count__gt=0)
        if value == "expired":
            return queryset.filter(expires_at__lte=now)
        if value == "off":
            return queryset.filter(is_active=False)
        return queryset
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
                "fields": ["video_file", "poster", "video_file_id"],
                "description": "Faylni tashlang yoki bosib tanlang. Muqova rasmi "
                "videodan avtomatik olinadi — yoqmasa o'zingiznikini yuklang. "
                "Birinchi marta mijozga yuborilgach bot Telegram ID'ni o'zi "
                "saqlab qo'yadi, keyingi yuborishlar bir zumda bo'ladi.",
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
    change_list_template = "rb/lessons/accesscode_change_list.html"
    list_display = ["code_badge", "state", "redeemed_by", "issued_to", "usage", "created_at"]
    list_display_links = ["code_badge"]
    list_filter = [CodeStateFilter]
    search_fields = ["code", "label", "issued_to__full_name", "issued_to__phone_number"]
    autocomplete_fields = ["issued_to"]
    readonly_fields = ["uses_count", "created_at"]
    actions = ["activate", "deactivate", "delete_used"]

    # How many codes one "Chiqarish" press may mint. A seller issuing them at
    # the counter never needs more, and a typed-in number never reaches the
    # database unchecked.
    ISSUE_CHOICES = (1, 5, 10, 25)

    def get_urls(self):
        return [
            path(
                "issue/",
                self.admin_site.admin_view(self.issue_view),
                name="lessons_accesscode_issue",
            ),
            *super().get_urls(),
        ]

    def issue_view(self, request: HttpRequest):
        """Mint single-use codes and show them once, on the way back."""
        changelist = reverse("admin:lessons_accesscode_changelist")
        if request.method != "POST" or not self.has_add_permission(request):
            return HttpResponseRedirect(changelist)

        try:
            count = int(request.POST.get("count", 1))
        except (TypeError, ValueError):
            count = 1
        if count not in self.ISSUE_CHOICES:
            count = 1

        made: list[str] = []
        for _ in range(count):
            # A collision is vanishingly unlikely over 31^8, but "unlikely"
            # is not "handled" — retry rather than hand the seller a 500.
            for _attempt in range(5):
                candidate = generate_code()
                try:
                    AccessCode.objects.create(
                        code=candidate, max_uses=1, label="Xarid uchun"
                    )
                except IntegrityError:
                    continue
                made.append(candidate)
                break

        if made:
            # The codes ride back in the session because this is a redirect,
            # and they are dropped as soon as the page has shown them.
            request.session["fresh_codes"] = made
        else:
            self.message_user(
                request, "Kod chiqarib bo'lmadi. Qayta urinib ko'ring.", messages.ERROR
            )
        return HttpResponseRedirect(changelist)

    def changelist_view(self, request: HttpRequest, extra_context=None):
        extra_context = extra_context or {}
        extra_context["fresh_codes"] = request.session.pop("fresh_codes", None)
        return super().changelist_view(request, extra_context)

    fieldsets = (
        (
            "Kalit so'z",
            {
                "fields": ["code", "label", "issued_to", "is_active"],
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

    @admin.display(description="Kim ishlatgan")
    def redeemed_by(self, obj: AccessCode) -> str:
        names = [u.user.full_name or str(u.user.telegram_id) for u in obj.unlocks.all()]
        if not names:
            return format_html('<span style="color:#9ca3af">—</span>')
        return ", ".join(names[:3]) + ("…" if len(names) > 3 else "")

    @admin.display(description="Ishlatilgan")
    def usage(self, obj: AccessCode) -> str:
        limit = obj.max_uses or "∞"
        return f"{obj.uses_count} / {limit}"

    def get_queryset(self, request: HttpRequest):
        return (
            super()
            .get_queryset(request)
            .select_related("issued_to")
            .prefetch_related("unlocks__user")
        )

    @admin.display(description="Holat")
    def state(self, obj: AccessCode) -> str:
        if not obj.is_active:
            return format_html('<span style="color:#6b7280">O‘chirilgan</span>')
        if obj.is_expired:
            return format_html('<span style="color:#c2410c">Muddati tugagan</span>')
        if obj.is_spent:
            return format_html('<span style="color:#6b7280">✔️ Ishlatilgan</span>')
        return format_html(
            '<span style="color:#059669;font-weight:600">🟢 Berish mumkin</span>'
        )

    @admin.action(description="🟢 Yoqish")
    def activate(self, request: HttpRequest, queryset) -> None:
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} ta kalit yoqildi.", messages.SUCCESS)

    @admin.action(description="🔴 O‘chirish")
    def deactivate(self, request: HttpRequest, queryset) -> None:
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} ta kalit o‘chirildi.", messages.SUCCESS)

    @admin.action(description="🧹 Ishlatilganlarini ro‘yxatdan o‘chirish")
    def delete_used(self, request: HttpRequest, queryset) -> None:
        """Clear spent codes out of the way.

        Deleting one does not take the customer's access with it: the unlock
        row keeps its own record and only loses the pointer, so the course
        stays open for whoever already redeemed it.
        """
        spent = queryset.filter(uses_count__gt=0)
        count = spent.count()
        if not count:
            self.message_user(
                request, "Tanlanganlar orasida ishlatilgani yo‘q.", messages.WARNING
            )
            return
        spent.delete()
        self.message_user(
            request,
            f"{count} ta ishlatilgan kalit o‘chirildi. "
            "Ularni ishlatgan mijozlarda darslar ochiq qoladi.",
            messages.SUCCESS,
        )


@admin.register(LessonUnlock)
class LessonUnlockAdmin(RBModelAdmin):
    """Who has the course open — and the way to open it by hand.

    Access is keyed on the Telegram account. A customer who deletes Telegram
    and signs up again arrives as a different person as far as the bot is
    concerned, and their old code is already spent, so without a way to grant
    access directly the shop would have to mint a replacement code and walk
    them through redeeming it again. Adding a row here does the same thing in
    one step. Removing one takes the course away again.
    """

    list_display = ["user", "code", "unlocked_at"]
    search_fields = ["user__full_name", "user__phone_number", "code__code"]
    autocomplete_fields = ["user"]
    readonly_fields = ["unlocked_at"]
    ordering = ["-unlocked_at"]

    fieldsets = (
        (
            "Darslarni ochish",
            {
                "fields": ["user"],
                "description": "Xaridorni tanlang — unga darslar kalit so'zsiz "
                "ochiladi. Mijoz Telegramini o'chirib qayta ro'yxatdan o'tgan "
                "bo'lsa yoki kalitini yo'qotgan bo'lsa shu yerdan bering.",
            },
        ),
    )

    def get_fieldsets(self, request: HttpRequest, obj=None):
        if obj is None:
            return self.fieldsets
        return (
            (
                "Ochilgan",
                {"fields": ["user", "code", "unlocked_at"]},
            ),
        )

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        # An existing row is a record of something that happened; only a new
        # one is a decision the shop is making now.
        if obj is None:
            return ["unlocked_at"]
        return ["user", "code", "unlocked_at"]
