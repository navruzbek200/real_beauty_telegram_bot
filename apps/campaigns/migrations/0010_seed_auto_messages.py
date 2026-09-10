"""
Carry the two hard-coded lifecycle campaigns into `AutoMessage`.

Before this, "one week after the purchase, ask for feedback" was spread across
three places: a delay in GlobalSettings, a body in MessageTemplate and a button
label back in GlobalSettings again. This migration collapses each of them into
a single row the shop can actually edit — same delay, same words, same button.

Purchases that already received the old message are logged as sent, so nobody
gets the week-1 check-in twice on the day of the deploy.
"""

from __future__ import annotations

from django.db import migrations

# (auto-message name, trigger source field, template type, button action,
#  GlobalSettings label field, fallback delay in days, fallback label)
_RULES = [
    (
        "1-hafta — fikr so'rovi",
        "week1_delay_days",
        "week1_checkin",
        "feedback",
        "feedback_button_label",
        7,
        "Fikr bildirish",
        "week1_sent",
    ),
    (
        "2-hafta — natija rasmi",
        "week2_delay_days",
        "week2_progress",
        "progress",
        "before_after_button_label",
        14,
        "Rasmlarni yuborish",
        "week2_sent",
    ),
]


def seed(apps, schema_editor):
    AutoMessage = apps.get_model("campaigns", "AutoMessage")
    AutoMessageLog = apps.get_model("campaigns", "AutoMessageLog")
    MessageTemplate = apps.get_model("campaigns", "MessageTemplate")
    GlobalSettings = apps.get_model("bot_settings", "GlobalSettings")
    UserProduct = apps.get_model("users", "UserProduct")

    settings = GlobalSettings.objects.first()

    for (
        name,
        delay_field,
        template_type,
        action,
        label_field,
        default_days,
        default_label,
        sent_flag,
    ) in _RULES:
        if AutoMessage.objects.filter(name=name).exists():
            continue

        template = MessageTemplate.objects.filter(
            template_type=template_type
        ).first()
        body = (template.body if template else "") or (
            "Assalomu alaykum, {{ user.full_name }}! "
            "Mahsulotdan foydalanyapsizmi? Fikringizni bildiring."
        )

        rule = AutoMessage.objects.create(
            name=name,
            trigger="after_purchase",
            delay_value=getattr(settings, delay_field, default_days) or default_days,
            delay_unit="day",
            body=body,
            body_ru=getattr(template, "body_ru", "") if template else "",
            body_en=getattr(template, "body_en", "") if template else "",
            button_action=action,
            button_label=getattr(settings, label_field, default_label)
            or default_label,
            is_active=template.is_active if template else True,
        )

        # Backfill: anything the old scheduler already handled is done.
        already = UserProduct.objects.filter(**{sent_flag: True}).values_list(
            "pk", "user_id"
        )
        AutoMessageLog.objects.bulk_create(
            [
                AutoMessageLog(auto_message=rule, user_id=user_id, anchor=f"up:{pk}")
                for pk, user_id in already
            ],
            ignore_conflicts=True,
        )


def unseed(apps, schema_editor):
    AutoMessage = apps.get_model("campaigns", "AutoMessage")
    AutoMessage.objects.filter(
        name__in=[name for name, *_ in _RULES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0009_messagetemplate_body_en_messagetemplate_body_ru_and_more"),
        ("bot_settings", "0003_alter_globalsettings_before_after_button_label_and_more"),
        ("users", "0013_telegramuser_language_telegramuser_registered_at"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
