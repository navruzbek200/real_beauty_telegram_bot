from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.prod")

app = Celery(
    "realbeauty", include=["tasks.scheduled", "tasks.broadcast", "tasks.orders"]
)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Every minute, because the delay on an automatic message is admin-editable
    # down to one minute. A daily beat would quietly turn "1 daqiqa" into
    # "tomorrow at 10:00" — the exact thing that makes a campaign untestable.
    # The task itself is cheap when nothing is due: one indexed query per rule.
    "auto-messages": {
        "task": "tasks.scheduled.dispatch_auto_messages",
        "schedule": crontab(minute="*"),
    },
    "recurring-reminders": {
        "task": "tasks.scheduled.dispatch_reminders",
        "schedule": crontab(minute="*/15"),
    },
    "birthday-messages": {
        "task": "tasks.scheduled.send_birthday_messages",
        "schedule": crontab(hour=9, minute=0),
    },
    # Unpaid orders are not sales — nobody collects cash on delivery — so
    # they get one nudge and then expire. Quarter-hourly is plenty for
    # windows measured in hours.
    "chase-unpaid-orders": {
        "task": "tasks.orders.chase_unpaid_orders",
        "schedule": crontab(minute="*/15"),
    },
    # Housekeeping — keeps the log table and media dir from growing forever.
    "purge-campaign-logs": {
        "task": "tasks.scheduled.purge_old_campaign_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
    "purge-progress-thumbnails": {
        "task": "tasks.scheduled.purge_old_progress_thumbnails",
        "schedule": crontab(hour=3, minute=30, day_of_week=0),
    },
    "purge-admin-log": {
        "task": "tasks.scheduled.purge_old_admin_log",
        "schedule": crontab(hour=3, minute=45, day_of_week=0),
    },
}
