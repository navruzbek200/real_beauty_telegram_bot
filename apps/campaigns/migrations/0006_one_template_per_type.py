from __future__ import annotations

from django.db import migrations


def dedupe(apps, schema_editor):
    """
    Collapse each template type down to a single row.

    The senders look a template up by type and take the first hit, so extra
    rows of the same type meant the message a customer received depended on
    row order — a stray test row could silently replace the real copy. Keep
    the longest body per type, which is the one somebody actually wrote.

    Split from the unique-constraint migration that follows: Postgres refuses
    to ALTER a table in the same transaction as deletes that left pending FK
    trigger events.
    """
    MessageTemplate = apps.get_model("campaigns", "MessageTemplate")
    for template_type in set(
        MessageTemplate.objects.values_list("template_type", flat=True)
    ):
        rows = list(MessageTemplate.objects.filter(template_type=template_type))
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: (len(r.body), r.pk), reverse=True)
        keeper, *extras = rows
        MessageTemplate.objects.filter(pk__in=[r.pk for r in extras]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0005_alter_campaignlog_options"),
    ]

    operations = [migrations.RunPython(dedupe, migrations.RunPython.noop)]
