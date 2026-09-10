from __future__ import annotations
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

async def cleanup_user_msg(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass

async def replace_prompt(message: Message, state: FSMContext, text: str, reply_markup=None) -> None:
    data = await state.get_data()
    last_id = data.get("prompt_msg_id")
    chat_id = message.chat.id
    bot = message.bot
    if last_id:
        try:
            await bot.delete_message(chat_id, last_id)
        except Exception:
            pass
    msg = await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)
    await state.update_data(prompt_msg_id=msg.message_id)

async def replace_prompt_callback(callback, state: FSMContext, text: str, reply_markup=None) -> None:
    data = await state.get_data()
    chat_id = callback.message.chat.id
    bot = callback.bot
    last_id = data.get("prompt_msg_id") or callback.message.message_id
    if last_id:
        try:
            await bot.delete_message(chat_id, last_id)
        except Exception:
            pass
    msg = await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)
    await state.update_data(prompt_msg_id=msg.message_id)

