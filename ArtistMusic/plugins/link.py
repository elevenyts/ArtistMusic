from pyrogram import filters
from pyrogram.types import Message

from ArtistMusic import app


@app.on_message(filters.command("link") & filters.private & app.sudo_filter)
async def group_link(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage:\n/link <group_id>")

    try:
        chat_id = int(message.command[1])
        invite = await app.create_chat_invite_link(chat_id)

        await message.reply_text(
            f"🔗 Group Link:\n{invite.invite_link}"
        )
    except Exception as e:
        await message.reply_text(f"Error: {e}")
