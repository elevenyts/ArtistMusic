#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

from AloneMusic.core.bot import Alone
from AloneMusic.core.dir import dirr
from AloneMusic.core.userbot import Userbot
from AloneMusic.misc import dbb, heroku

from .logging import LOGGER

dirr()
dbb()
heroku()

app = Alone()
userbot = Userbot()


from .platforms import (Apple, Carbon, Resso, Soundcloud, Spotify, Telegram,
                        Youtube)

Apple = Apple.AppleAPI()
Carbon = Carbon.CarbonAPI()
SoundCloud = Soundcloud.SoundAPI()
Spotify = Spotify.SpotifyAPI()
Resso = Resso.RessoAPI()
Telegram = Telegram.TeleAPI()
YouTube = Youtube.YouTubeAPI()
