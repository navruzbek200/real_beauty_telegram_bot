from __future__ import annotations

from typing import Any

from asgiref.sync import sync_to_async

from apps.campaigns.models import MessageTemplate


@sync_to_async
def render_template(
    template_type: str, context: dict[str, Any], lang: str = "uz"
) -> tuple[str, str]:
    """
    Render the active template of the given type in `lang`.

    Returns (rendered_text, parse_mode). Falls back to an empty string when no
    active template exists so the caller can substitute its own text rather
    than the bot going silent.
    """
    template = MessageTemplate.objects.filter(
        template_type=template_type, is_active=True
    ).first()
    if template is None:
        return ("", "HTML")
    return (template.render(context, lang), template.parse_mode)


@sync_to_async
def get_template(template_type: str) -> MessageTemplate | None:
    return MessageTemplate.objects.filter(
        template_type=template_type, is_active=True
    ).first()
