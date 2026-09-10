from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.filters.menu import MenuText
from bot.i18n import normalize, t
from bot.keyboards import inline
from bot.services import analytics_service, user_service
from bot.states.registration import FaceAnalysisState, SkinQuizState

logger = logging.getLogger(__name__)
router = Router(name="face_analysis")
router.message.filter(F.chat.type == "private")


@router.message(MenuText("menu.face_analysis"))
async def start_face_analysis(message: Message, state: FSMContext, lang: str) -> None:
    """«Yuz tahlili» drops straight into the same skin-type quiz as retake —
    no separate selfie step."""
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None or not user.full_name:
        await message.answer(t("user.not_registered", lang))
        return
    await state.clear()
    await state.set_state(SkinQuizState.intro)
    await state.update_data(language=user.language)
    await message.answer(
        t("quiz.intro", normalize(user.language)),
        parse_mode="HTML",
        reply_markup=inline.quiz_start_keyboard(normalize(user.language)),
    )


@router.message(FaceAnalysisState.photo, F.photo)
async def receive_face_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    if user is None:
        await state.clear()
        return
    lang = normalize(user.language)

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buffer = await bot.download_file(file.file_path)
    photo_bytes = buffer.read() if buffer is not None else None
    if not photo_bytes:
        await message.answer(t("faceanalysis.error", lang))
        return

    if not await analytics_service.detect_face(photo_bytes):
        # Stay in FaceAnalysisState.photo — let them just send another one.
        await message.answer(t("faceanalysis.no_face", lang))
        return

    try:
        await analytics_service.save_face_analysis_photo(
            telegram_id=user.telegram_id, file_bytes=photo_bytes
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to save face analysis photo for %s", user.telegram_id)
        await message.answer(t("faceanalysis.error", lang))
        return

    await state.clear()
    await message.answer(
        t("faceanalysis.success", lang, full_name=html.escape(user.full_name or "")),
        parse_mode="HTML",
    )


@router.message(FaceAnalysisState.photo)
async def face_photo_not_a_photo(message: Message) -> None:
    if message.from_user is None:
        return
    user = await user_service.get_user(message.from_user.id)
    lang = normalize(user.language) if user else "uz"
    await message.answer(t("faceanalysis.ask_photo", lang))
