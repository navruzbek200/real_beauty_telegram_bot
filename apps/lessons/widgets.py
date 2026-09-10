"""
The video field's admin widget.

Its template lives in this app's own templates/ directory rather than the
project's, because Django renders widgets through a separate form engine that
searches installed apps but not the project TEMPLATES dirs.
"""

from __future__ import annotations

from django import forms

# Telegram refuses a bot upload over 50 MB. Saying so at the point of choosing
# the file is the difference between a caught mistake and a lesson that looks
# published but never plays.
TELEGRAM_MAX_MB = 50


class VideoDropWidget(forms.ClearableFileInput):
    template_name = "rb/widgets/video_drop.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["max_mb"] = TELEGRAM_MAX_MB
        context["checkbox_name"] = self.clear_checkbox_name(name)
        context["checkbox_id"] = self.clear_checkbox_id(self.clear_checkbox_name(name))
        current_url = ""
        current_name = ""
        if value and getattr(value, "url", None):
            current_url = value.url
            current_name = value.name.rsplit("/", 1)[-1]
        context["current_url"] = current_url
        context["current_name"] = current_name
        return context
