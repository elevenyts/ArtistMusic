#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import filters
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from AloneMusic import app
from AloneMusic.utils.database import get_lang, set_lang
from AloneMusic.utils.decorators import ActualAdminCB, language, languageCB
from config import BANNED_USERS
from strings import get_string, languages_present


def languages_keyboard(_):
    buttons = [
        InlineKeyboardButton(
            text=languages_present[i],
            callback_data=f"languages:{i}",
        )
        for i in languages_present
    ]

    keyboard = InlineKeyboardMarkup(
        [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        + [
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data="settingsback_helper",
                ),
                InlineKeyboardButton(
                    text=_["CLOSE_BUTTON"],
                    callback_data="close",
                ),
            ]
        ]
    )
    return keyboard


@app.on_message(filters.command(["lang", "setlang", "language"]) & ~BANNED_USERS)
@language
async def langs_command(client, message: Message, _):
    await message.reply_text(
        _["lang_1"],
        reply_markup=languages_keyboard(_),
    )


@app.on_callback_query(filters.regex("^LG") & ~BANNED_USERS)
@languageCB
async def language_cb(client, callback_query: CallbackQuery, _):
    try:
        await callback_query.answer()
    except Exception:
        return

    await callback_query.edit_message_reply_markup(reply_markup=languages_keyboard(_))


@app.on_callback_query(filters.regex(r"^languages:(.*?)") & ~BANNED_USERS)
@ActualAdminCB
async def language_markup(client, callback_query: CallbackQuery, _):
    language_code = callback_query.data.split(":")[1]
    old = await get_lang(callback_query.message.chat.id)

    if str(old) == str(language_code):
        return await callback_query.answer(_["lang_4"], show_alert=True)

    try:
        _ = get_string(language_code)
    except KeyError:
        _ = get_string(old)
        return await callback_query.answer(_["lang_3"], show_alert=True)

    await set_lang(callback_query.message.chat.id, language_code)
    await callback_query.answer(_["lang_2"], show_alert=True)

    await callback_query.edit_message_reply_markup(reply_markup=languages_keyboard(_))
