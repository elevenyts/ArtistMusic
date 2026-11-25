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
import os
import sys
import shutil
import asyncio

from pyrogram import filters, types

from ArtistMusic import app, db, lang, stop


@app.on_message(filters.command(["logs"]) & app.sudo_filter)
@lang.language()
async def _logs(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])
    
    # Read log file and extract logs from last bot start
    try:
        with open("log.txt", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the last occurrence of bot start marker (first log line of startup sequence)
        start_marker = "📁 Cache directories updated."
        last_start_index = content.rfind(start_marker)
        
        if last_start_index != -1:
            # Get logs from the last bot start
            recent_logs = content[last_start_index:]
            
            # Write to temporary file
            temp_log_path = "temp_recent_logs.txt"
            with open(temp_log_path, "w", encoding="utf-8") as f:
                f.write(recent_logs)
            
            await sent.edit_media(
                media=types.InputMediaDocument(
                    media=temp_log_path,
                    caption=m.lang["log_sent"].format(app.name) + " (Last session)",
                )
            )
            
            # Clean up temp file
            try:
                os.remove(temp_log_path)
            except Exception:
                pass
        else:
            # If no start marker found, send the full log file
            await sent.edit_media(
                media=types.InputMediaDocument(
                    media="log.txt",
                    caption=m.lang["log_sent"].format(app.name),
                )
            )
    except Exception as e:
        await sent.edit_text(f"Error reading logs: {str(e)}")


@app.on_message(filters.command(["logger"]) & app.sudo_filter)
@lang.language()
async def _logger(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


@app.on_message(filters.command(["restart"]) & app.sudo_filter)
@lang.language()
async def _restart(_, m: types.Message):
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text(m.lang["restarting"])

    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    await sent.edit_text(m.lang["restarted"])
    asyncio.create_task(stop())
    await asyncio.sleep(2)

    os.execl(sys.executable, sys.executable, "-m", "ArtistMusic")


@app.on_message(filters.command(["update"]) & app.sudo_filter)
@lang.language()
async def _update(_, m: types.Message):
    """
    Update bot from git repository and restart.
    """
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text(
        "<blockquote><b>🔄 Updating...</b></blockquote>\n\n"
        "<blockquote>Pulling latest changes from repository...</blockquote>"
    )
    
    try:
        # Check if git is available
        import subprocess
        
        # Pull latest changes
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode != 0:
            return await sent.edit_text(
                f"<blockquote><b>❌ Update Failed</b></blockquote>\n\n"
                f"<blockquote>Git error: {result.stderr}</blockquote>"
            )
        
        output = result.stdout
        
        # Check if there are any changes
        if "Already up to date" in output or "Already up-to-date" in output:
            return await sent.edit_text(
                "<blockquote><b>✅ Already Updated</b></blockquote>\n\n"
                "<blockquote>Bot is already running the latest version.</blockquote>"
            )
        
        # Install/update requirements
        await sent.edit_text(
            "<blockquote><b>📦 Installing Dependencies...</b></blockquote>\n\n"
            "<blockquote>Updating Python packages...</blockquote>"
        )
        
        pip_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"],
            capture_output=True,
            text=True
        )
        
        # Clear cache and restart
        await sent.edit_text(
            "<blockquote><b>🔄 Restarting...</b></blockquote>\n\n"
            "<blockquote>Bot will be back online shortly...</blockquote>"
        )
        
        for directory in ["cache", "downloads"]:
            shutil.rmtree(directory, ignore_errors=True)
        
        asyncio.create_task(stop())
        await asyncio.sleep(2)
        
        os.execl(sys.executable, sys.executable, "-m", "ArtistMusic")
        
    except FileNotFoundError:
        await sent.edit_text(
            "<blockquote><b>❌ Git Not Found</b></blockquote>\n\n"
            "<blockquote>Git is not installed on this system. Use /restart instead.</blockquote>"
        )
    except Exception as e:
        await sent.edit_text(
            f"<blockquote><b>❌ Update Error</b></blockquote>\n\n"
            f"<blockquote>{str(e)}</blockquote>"
        )
