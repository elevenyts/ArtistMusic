# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts/ArtistMusic
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
import pyrogram
from typing import Optional

from ArtistMusic import config, logger


class MutableUserFilter(pyrogram.filters.Filter, set):
    """
    A Pyrogram filter that is ALSO a mutable set of user ids.

    Plain `pyrogram.filters.user()` only supports being called as a
    filter — it has no `.add()`, `.discard()`, `.update()`, `in`, or
    `len()`. This project's plugins (blacklist.py, sudoers.py,
    stats.py, start.py, __main__.py) all treat `app.bl_users` and
    `app.sudo_filter` as if they were sets, so we give them a real
    set underneath a real filter.
    """

    def __init__(self, user_ids=None):
        set.__init__(self, user_ids or [])

    async def __call__(self, _, update):
        user = getattr(update, "from_user", None)
        return bool(user and user.id in self)


class Bot(pyrogram.Client):
    """
    Main bot client class extending Pyrogram's Client.

    This class initializes the Telegram bot with proper configuration
    and provides methods for starting and stopping the bot.

    Attributes:
        owner (int): Owner's user ID
        logger (int): Logger group/channel ID
        bl_users (Filter): Filter for blacklisted users
        sudoers (set): Set of sudo user IDs
        sudo_filter (Filter): Filter for sudo users
        id (int): Bot's user ID (set after boot)
        name (str): Bot's first name (set after boot)
        username (str): Bot's username (set after boot)
        mention (str): Bot's mention tag (set after boot)
    """

    def __init__(self):
        """Initialize the bot client with configuration settings."""
        super().__init__(
            name="ArtistMusic",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=pyrogram.enums.ParseMode.HTML,
            max_concurrent_transmissions=7,
            link_preview_options=pyrogram.types.LinkPreviewOptions(
                is_disabled=True),
        )

        self.owner: int = config.OWNER_ID
        self.logger: int = config.LOGGER_ID
        self.bl_users: MutableUserFilter = MutableUserFilter()
        self.sudoers: set = {self.owner}  # Set of sudo user IDs
        self.sudo_filter: MutableUserFilter = MutableUserFilter({self.owner})

        # These will be set after boot()
        self.id: Optional[int] = None
        self.name: Optional[str] = None
        self.username: Optional[str] = None
        self.mention: Optional[str] = None

    async def boot(self) -> None:
        """
        Start the bot and perform initial setup.

        This method:
        - Starts the Pyrogram client
        - Retrieves bot information
        - Verifies access to logger group
        - Checks bot admin status in logger group

        Raises:
            SystemExit: If bot cannot access logger group or is not an admin.
        """
        await super().start()

        # Set bot information
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention

        # Verify logger group access
        try:
            await self.send_message(self.logger, "🤖 ʙᴏᴛ ꜱᴛᴀʀᴛᴇᴅ")
            member = await self.get_chat_member(self.logger, self.id)
        except Exception as ex:
            raise SystemExit(
                f"❌ ʙᴏᴛ ꜰᴀɪʟᴇᴅ ᴛᴏ ᴀᴄᴄᴇꜱꜱ ʟᴏɢɢᴇʀ ɢʀᴏᴜᴘ: {self.logger}\n"
                f"ʀᴇᴀꜱᴏɴ: {ex}\n"
                f"ᴘʟᴇᴀꜱᴇ ᴇɴꜱᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪꜱ ᴀᴅᴅᴇᴅ ᴛᴏ ᴛʜᴇ ʟᴏɢɢᴇʀ ɢʀᴏᴜᴘ."
            )

        # Verify admin status
        if member.status != pyrogram.enums.ChatMemberStatus.ADMINISTRATOR:
            raise SystemExit(
                f"❌ ʙᴏᴛ ɪꜱ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀ ɪɴ ʟᴏɢɢᴇʀ ɢʀᴏᴜᴘ: {self.logger}\n"
                f"ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴍᴏᴛᴇ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀ ᴡɪᴛʜ ɴᴇᴄᴇꜱꜱᴀʀʏ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ."
            )

        logger.info(f"🤖 Bot started successfully as @{self.username}")

    async def exit(self) -> None:
        """
        Gracefully stop the bot client.

        This method stops the Pyrogram client and logs the shutdown.
        """
        await super().stop()
        logger.info("🤖 Bot client stopped.")
