import asyncio
import importlib
import os
import sys
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from Artist import LOGGER, app, userbot
from Artist.core.call import Artist
from Artist.misc import sudo
from Artist.plugins import ALL_MODULES
from Artist.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

# Web server for free deployment platforms (Render, Koyeb, etc.)
WEB_SERVER = False
PORT = int(os.environ.get("PORT", 8080))

async def start_web_server():
    """Start a simple web server to keep the bot alive on free platforms"""
    try:
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text="Bot is running!", status=200)
        
        async def home(request):
            return web.Response(text="Artist Music Bot is Active!", status=200)
        
        app_web = web.Application()
        app_web.router.add_get('/', home)
        app_web.router.add_get('/health', health_check)
        app_web.router.add_get('/ping', health_check)
        
        runner = web.AppRunner(app_web)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        LOGGER(__name__).info(f"Web server started on port {PORT}")
        return True
    except ImportError:
        LOGGER(__name__).warning("aiohttp not installed. Web server disabled.")
        return False
    except Exception as e:
        LOGGER(__name__).warning(f"Failed to start web server: {e}")
        return False


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
    global WEB_SERVER
    WEB_SERVER = await start_web_server()
    
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
    
    # Keep the bot running with web server
    try:
        await idle()
    finally:
        await app.stop()
        await userbot.stop()
        LOGGER("Artist").info("Stopping Bot...")


if __name__ == "__main__":
    # Handle replit specific requirements
    if "REPLIT" in os.environ or "REPL_ID" in os.environ:
        try:
            from replit import web
            web.run()
        except:
            pass
    
    # Handle render, koyeb, railway deployments
    if "RENDER" in os.environ or "KOYEB" in os.environ or "RAILWAY" in os.environ:
        LOGGER(__name__).info("Detected free platform deployment")
    
    # Run the bot
    asyncio.get_event_loop().run_until_complete(init())
