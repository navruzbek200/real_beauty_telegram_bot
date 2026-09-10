"""
Form pieces shared by the customer-facing admin pages.

Customers are listed on more than one page ("Xaridorlar" and "App
foydalanuvchilari"), and each page edits a different subset of the same row —
so the rules that must hold everywhere live here instead of in one page's form.
"""

from __future__ import annotations

from django import forms

from .models import TelegramUser


class PhoneNumberUniqueMixin:
    """
    Rejects a phone number that already belongs to another customer card.

    The phone number is what the bot matches on at /start, so two cards holding
    the same number means the customer links to whichever one is found first —
    a silent wrong-card bug that is painful to untangle afterwards.
    """

    def clean_phone_number(self) -> str:
        phone = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone:
            return phone
        tail = TelegramUser.phone_tail_of(phone)
        if not tail:
            raise forms.ValidationError(
                "Raqam to'liq emas — kamida 9 ta raqam bo'lishi kerak."
            )
        # Two cards with the same number would both match the customer on /start.
        clash = TelegramUser.objects.filter(phone_tail=tail)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        existing = clash.first()
        if existing is not None:
            raise forms.ValidationError(
                f"Bu raqam «{existing}» xaridorga biriktirilgan."
            )
        return phone
