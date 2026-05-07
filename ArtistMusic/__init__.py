from Artist.core.bot import Artist
from Artist.core.dir import dirr
from Artist.core.userbot import Userbot
from Artist.misc import dbb, heroku

from .logging import LOGGER

dirr()
dbb()
heroku()

app = Artist()
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
