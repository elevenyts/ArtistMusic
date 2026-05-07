import asyncio
import importlib
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from Artist import LOGGER, app, userbot
from Artist.core.call import Artist
from Artist.misc import sudo
from Artist.plugins import ALL_MODULES
from Artist.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

PORT = int(os.environ.get("PORT", 8080))

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""
    
    def do_GET(self):
        if self.path in ['/', '/health', '/ping']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass

def start_web_server():
    """Start a simple web server in a separate thread"""
    try:
        server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        LOGGER(__name__).info(f"Web server started on port {PORT}")
        return server
    except Exception as e:
        LOGGER(__name__).warning(f"Failed to start web server: {e}")
        return None


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()
    
    # Start web server for free platforms
    http_server = start_web_server()
    
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    
    await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module("Artist.plugins" + all_module)
    LOGGER("Artist.plugins").info("Successfully Imported Modules...")
    
    await userbot.start()
    await Artist.start()
    
    try:
        await Artist.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("Artist").error(
            "Please turn on the videochat of your log group/channel.\n\nStopping Bot..."
        )
        exit()
    except:
        pass
    
    await Artist.decorators()
    LOGGER("Artist").info("Bot started successfully!")
    
    # Keep the bot running
    try:
        await idle()
    finally:
        if http_server:
            http_server.shutdown()
        await app.stop()
        await userbot.stop()
        LOGGER("Artist").info("Stopping Bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
