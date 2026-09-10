"""
Shared admin building blocks.

Django's admin defaults are built for developers: deleting means picking an
action out of a dropdown and pressing Run, a yes/no filter is literally labelled
"Ha / Yo'q" with no hint of what it filters, and the only way back is a line of
grey breadcrumb text. Everything here exists to make those three things behave
the way any ordinary app behaves.
"""

from __future__ import annotations

from typing import Any, Sequence

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin


def yes_no_filter(
    field: str, title: str, yes_label: str, no_label: str
) -> type[admin.SimpleListFilter]:
    """
    A boolean filter that says what it actually means.

    Filtering a BooleanField the stock way renders "Barchasi / Ha / Yo'q" —
    which leaves the reader to guess "yes… what?". Naming both sides removes
    the guess.
    """

    class Filter(admin.SimpleListFilter):
        parameter_name = field

        def __init__(self, request, params, model, model_admin):
            self.title = title
            super().__init__(request, params, model, model_admin)

        def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple]:
            return [("1", yes_label), ("0", no_label)]

        def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
            if self.value() == "1":
                return queryset.filter(**{field: True})
            if self.value() == "0":
                return queryset.filter(**{field: False})
            return queryset

    Filter.__name__ = f"{field.title().replace('_', '')}Filter"
    return Filter


def bot_link_badge(is_linked: bool) -> str:
    """
    The "is this customer reachable by the bot?" column.

    Shared because more than one page lists customers, and two hand-written
    copies of the same badge drift apart the first time a wording changes.
    """
    if is_linked:
        return format_html('<span style="color:#059669">✅ Ulangan</span>')
    return format_html('<span style="color:#f59e0b">⏳ Botga kirmagan</span>')


class RBModelAdmin(ModelAdmin):
    """Base for every admin page in this project."""

    # Templates add a real back button; see core/templates/rb/.
    change_form_template = "rb/change_form.html"
    change_list_template = "rb/change_list.html"
    delete_confirmation_template = "rb/delete_confirmation.html"

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        display = list(super().get_list_display(request))
        # A bin on the row is how people expect to delete one thing. The stock
        # route — tick, open a dropdown, choose an action, press Run, confirm —
        # is four steps to say "delete this".
        if self.has_delete_permission(request) and "delete_button" not in display:
            display.append("delete_button")
        return display

    @admin.display(description="")
    def delete_button(self, obj: Any) -> str:
        url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_delete",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}" class="rb-row-delete" title="O\'chirish">'
            '<span class="material-symbols-outlined">delete</span></a>',
            url,
        )
