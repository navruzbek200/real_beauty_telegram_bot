from __future__ import annotations

from asgiref.sync import sync_to_async

from apps.support.models import SupportAdmin, SupportMessage, SupportSettings, SupportThread
from apps.users.models import TelegramUser

_SUBJECT_MAX = 60


@sync_to_async
def add_user_message(
    *,
    telegram_id: int,
    text: str,
    attachment_type: str = "",
    attachment_file_id: str = "",
) -> SupportMessage:
    """
    Append an incoming message to the user's open thread, creating one if the
    user has none or their previous thread was closed.

    Returns the saved message (with `.thread.user` preloaded) so the caller
    can forward it into the support group without a second query.
    """
    user = TelegramUser.objects.get(telegram_id=telegram_id)
    thread = (
        SupportThread.objects.select_related("user")
        .filter(user=user)
        .exclude(status=SupportThread.Status.CLOSED)
        .order_by("-last_message_at")
        .first()
    )
    if thread is None:
        subject = text[:_SUBJECT_MAX] or "📎 Fayl"
        thread = SupportThread.objects.create(user=user, subject=subject)

    message = SupportMessage.objects.create(
        thread=thread,
        direction=SupportMessage.Direction.IN,
        text=text,
        attachment_type=attachment_type,
        attachment_file_id=attachment_file_id,
    )
    thread.touch(from_user=True)
    return message


@sync_to_async
def get_support_settings() -> SupportSettings:
    return SupportSettings.get()


@sync_to_async
def mark_group_sent(message_id: int, *, group_chat_id: int, group_message_id: int) -> None:
    SupportMessage.objects.filter(pk=message_id).update(
        group_chat_id=group_chat_id,
        group_message_id=group_message_id,
        status=SupportMessage.Status.SENT,
    )


@sync_to_async
def mark_failed(message_id: int, error_detail: str) -> None:
    SupportMessage.objects.filter(pk=message_id).update(
        status=SupportMessage.Status.FAILED, error_detail=error_detail[:4000]
    )


@sync_to_async
def get_authorized_admin(telegram_user_id: int) -> SupportAdmin | None:
    return SupportAdmin.objects.filter(
        telegram_user_id=telegram_user_id, enabled=True
    ).first()


@sync_to_async
def set_admin_name_if_blank(admin_id: int, name: str) -> None:
    if not name:
        return
    SupportAdmin.objects.filter(pk=admin_id, name="").update(name=name)


@sync_to_async
def get_unanswered_messages() -> list[SupportMessage]:
    """
    The latest incoming message of every thread still awaiting a reply.

    One row per thread (not every unanswered message in it) — an admin who
    asks to resend wants a card to reply to per open conversation, not a
    replay of everything the customer typed.
    """
    thread_ids = (
        SupportThread.objects.filter(awaiting_reply=True)
        .order_by("last_message_at")
        .values_list("pk", flat=True)
    )
    messages: list[SupportMessage] = []
    for thread_id in thread_ids:
        msg = (
            SupportMessage.objects.filter(
                thread_id=thread_id, direction=SupportMessage.Direction.IN
            )
            .select_related("thread", "thread__user")
            .order_by("-created_at")
            .first()
        )
        if msg is not None:
            messages.append(msg)
    return messages


@sync_to_async
def find_mapped_message(group_chat_id: int, group_message_id: int) -> SupportMessage | None:
    return (
        SupportMessage.objects.select_related("thread", "thread__user")
        .filter(group_chat_id=group_chat_id, group_message_id=group_message_id)
        .first()
    )


@sync_to_async
def save_reply(
    *,
    thread_id: int,
    text: str,
    attachment_type: str,
    attachment_file_id: str,
    telegram_admin_id: int,
    status: str,
    error_detail: str = "",
) -> SupportMessage:
    message = SupportMessage.objects.create(
        thread_id=thread_id,
        direction=SupportMessage.Direction.OUT,
        text=text,
        attachment_type=attachment_type,
        attachment_file_id=attachment_file_id,
        telegram_admin_id=telegram_admin_id,
        status=status,
        error_detail=error_detail,
    )
    if status == SupportMessage.Status.SENT:
        SupportThread.objects.get(pk=thread_id).touch(from_user=False)
    return message
