from __future__ import annotations

import logging

from django.contrib import admin, messages
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from core.admin import RBModelAdmin

from core.telegram import TelegramError, send_message

from .models import FaceAnalysisPhoto, ProgressPhoto, SkinQuizResult, UserFeedback

logger = logging.getLogger(__name__)


@admin.register(SkinQuizResult)
class SkinQuizResultAdmin(RBModelAdmin):
    """
    What the skin quiz concluded, and why.

    The answers matter as much as the verdict: "oily" is a label, but "5 on
    oiliness, 4 on blackheads, 0 on sensitivity" is what tells a seller which
    product to put in front of this customer.
    """

    list_display = ["user", "skin_type_label", "problem_summary", "created_at"]
    list_display_links = ["user"]
    list_filter = ["skin_type", "language"]
    search_fields = ["user__full_name", "user__phone_number"]
    readonly_fields = [
        "user",
        "skin_type_label",
        "answer_table",
        "advice_given",
        "language",
        "created_at",
    ]
    fields = [
        "user",
        "skin_type_label",
        "answer_table",
        "advice_given",
        "language",
        "created_at",
    ]
    date_hierarchy = "created_at"
    list_per_page = 30

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="Teri turi", ordering="skin_type")
    def skin_type_label(self, obj: SkinQuizResult) -> str:
        from bot.i18n import t

        return t(f"skin.type.{obj.skin_type}", "uz")

    @admin.display(description="Muammolar")
    def problem_summary(self, obj: SkinQuizResult) -> str:
        """The questions this customer scored high on, in plain words."""
        from apps.analytics.skin_logic import BY_ID, THRESHOLD

        names = {
            "q2": "poralar",
            "q3": "sezgirlik",
            "q4": "husnbuzar",
            "q5": "qora nuqta",
            "q6": "oq nuqta",
            "q7": "pigmentatsiya",
            "q8": "ko'z ajinlari",
            "q9": "ko'z tagi",
            "q10": "bo'shashish",
        }
        hits = [
            label
            for qid, label in names.items()
            if qid in BY_ID and int(obj.answers.get(qid, 0) or 0) >= THRESHOLD
        ]
        return ", ".join(hits) if hits else "—"

    @admin.display(description="Javoblar")
    def answer_table(self, obj: SkinQuizResult) -> str:
        from apps.analytics.skin_logic import QUESTIONS, THRESHOLD
        from bot.i18n import t

        rows = format_html_join(
            "",
            '<tr><td style="padding:2px 8px">{}</td>'
            '<td style="padding:2px 8px;color:{};font-weight:600">{}</td></tr>',
            (
                (
                    t(question.text_key, "uz"),
                    "#dc2626"
                    if int(obj.answers.get(question.id, 0) or 0) >= THRESHOLD
                    else "#6b7280",
                    int(obj.answers.get(question.id, 0) or 0),
                )
                for question in QUESTIONS
            ),
        )
        return format_html("<table>{}</table>", rows)

    @admin.display(description="Berilgan tavsiyalar")
    def advice_given(self, obj: SkinQuizResult) -> str:
        from bot.i18n import t

        # The recommendation blocks are our own constants and carry deliberate
        # <b>/<i> markup — escaping them would print the tags at the reader.
        blocks = [t(key, "uz") for key in (obj.recommendation_keys or [])]
        return format_html(
            '<div style="white-space:pre-wrap">{}</div>',
            mark_safe("\n\n".join(blocks)),
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(FaceAnalysisPhoto)
class FaceAnalysisPhotoAdmin(RBModelAdmin):
    """
    Read-only log of «Yuz tahlili» selfies — `filename` is the exact value a
    future Google Sheets sync writes into Image_Filename, and `synced_to_sheet`
    marks which rows that sync has already handled.
    """

    list_display = ["user", "skin_type_label", "filename", "synced_to_sheet", "created_at"]
    list_display_links = ["user"]
    list_filter = ["skin_type", "synced_to_sheet"]
    search_fields = ["user__full_name", "user__phone_number", "filename"]
    readonly_fields = [
        "user",
        "skin_type_label",
        "image",
        "filename",
        "synced_to_sheet",
        "created_at",
    ]
    fields = ["user", "skin_type_label", "image", "filename", "synced_to_sheet", "created_at"]
    date_hierarchy = "created_at"
    list_per_page = 30

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="Teri turi", ordering="skin_type")
    def skin_type_label(self, obj: FaceAnalysisPhoto) -> str:
        from bot.i18n import t

        return t(f"skin.type.{obj.skin_type}", "uz") if obj.skin_type != "unknown" else "—"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.method in ("GET", "HEAD")
