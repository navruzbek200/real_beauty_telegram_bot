"""
The customer-facing bonus program: balance, tier, cashback, the personal
invite link, and turning points into rewards.

All the accounting lives in `apps.loyalty`; this router only renders it and
routes taps. The program can be switched off from the admin, in which case
every entry point here answers with a short "it's off" note instead of a
half-working screen.
"""

from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters.menu import MenuText
from bot.i18n import t
from bot.keyboards import inline
from bot.services import loyalty_service, user_service

logger = logging.getLogger(__name__)
router = Router(name="loyalty")
# Bonuses are a 1:1 conversation feature; a tap in the support group must not
# reach here.
router.message.filter(F.chat.type == "private")


def _summary_text(summary: loyalty_service.LoyaltySummary, lang: str) -> str:
    text = t(
        "loyalty.summary",
        lang,
        tier=t(summary.tier_label_key, lang),
        cashback=summary.cashback,
        balance=summary.balance,
        lifetime=summary.lifetime,
    )
    if summary.next_label_key:
        text += t(
            "loyalty.next_tier",
            lang,
            tier=t(summary.next_label_key, lang),
            remaining=summary.remaining,
        )
    else:
        text += t("loyalty.max_tier", lang)
    text += t(
        "loyalty.invite_block",
        lang,
        points=summary.referral_points,
        link=summary.invite_link,
    )
    return text


@router.message(MenuText("menu.bonus"))
async def menu_bonus(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return

    summary = await loyalty_service.get_summary(message.from_user.id)
    if summary is None or not summary.enabled:
        await message.answer(t("loyalty.disabled", lang))
        return

    rewards = await loyalty_service.list_active_rewards()
    share = loyalty_service.share_url(
        summary.invite_link, t("loyalty.share_text", lang)
    )
    await message.answer(
        _summary_text(summary, lang),
        parse_mode="HTML",
        reply_markup=inline.bonus_keyboard(lang, share, has_rewards=bool(rewards)),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == inline.CB_OPEN_REWARDS)
async def open_rewards(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    summary = await loyalty_service.get_summary(callback.from_user.id)
    if summary is None or not summary.enabled:
        await callback.message.answer(t("loyalty.disabled", lang))
        return
    rewards = await loyalty_service.list_active_rewards()
    if not rewards:
        await callback.message.answer(t("loyalty.rewards_empty", lang))
        return

    from core.i18n import pick

    lines = [t("loyalty.rewards_header", lang, balance=summary.balance)]
    buttons: list[tuple[int, str]] = []
    for reward in rewards:
        title = pick(reward, "title", lang)
        lines.append(
            t("loyalty.reward_line", lang, title=html.escape(title), cost=reward.cost_points)
        )
        buttons.append((reward.pk, f"{title} · {reward.cost_points} 💎"))
    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=inline.rewards_keyboard(lang, buttons),
    )


@router.callback_query(F.data.startswith(f"{inline.CB_REDEEM_REWARD}{inline.SEP}"))
async def redeem_reward(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    try:
        reward_id = int((callback.data or "").split(inline.SEP, 1)[1])
    except (ValueError, IndexError):
        return
    outcome = await loyalty_service.redeem_reward(callback.from_user.id, reward_id)
    if outcome.ok:
        await callback.message.answer(
            t("loyalty.redeem_ok", lang, code=outcome.code), parse_mode="HTML"
        )
        return
    key = {
        "not_enough": "loyalty.redeem_not_enough",
    }.get(outcome.error or "", "loyalty.redeem_unavailable")
    await callback.message.answer(t(key, lang))
