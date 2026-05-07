#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
# All rights reserved.
import asyncio
import os
import shutil
import socket
from datetime import datetime

import urllib3
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError
from pyrogram import filters

import config
from AloneMusic import app
from AloneMusic.misc import HAPP, SUDOERS, XCB
from AloneMusic.utils.database import (get_active_chats, remove_active_chat,
                                       remove_active_video_chat)
from AloneMusic.utils.decorators.language import language

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


async def is_heroku():
    return "heroku" in socket.getfqdn().lower()


# ---------------- LOGS ----------------
@app.on_message(filters.command(["getlog", "logs", "getlogs"]) & SUDOERS)
@language
async def log_(client, message, _):
    try:
        await message.reply_document("log.txt")
    except:
        await message.reply_text(_["server_1"])


# ---------------- UPDATE ----------------
@app.on_message(filters.command(["update", "gitpull"]) & SUDOERS)
@language
async def update_(client, message, _):
    if await is_heroku():
        if HAPP is None:
            return await message.reply_text(_["server_2"])

    response = await message.reply_text(_["server_3"])

    try:
        repo = Repo(search_parent_directories=True)
    except GitCommandError:
        return await response.edit(_["server_4"])
    except InvalidGitRepositoryError:
        return await response.edit(_["server_5"])

    os.system(f"git fetch origin {config.UPSTREAM_BRANCH} &> /dev/null")
    await asyncio.sleep(5)

    verification = ""
    for check in repo.iter_commits(f"HEAD..origin/{config.UPSTREAM_BRANCH}"):
        verification = str(check.count())

    if verification == "":
        return await response.edit(_["server_6"])

    updates = ""
    REPO_ = repo.remotes.origin.url.split(".git")[0]

    def ordinal(n):
        return "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )

    for info in repo.iter_commits(f"HEAD..origin/{config.UPSTREAM_BRANCH}"):
        date = datetime.fromtimestamp(info.committed_date)
        updates += (
            f"<b>➣ #{info.count()}: "
            f"<a href={REPO_}/commit/{info}>{info.summary}</a> "
            f"ʙʏ -> {info.author}</b>\n"
            f"\t\t<b>➥ ᴄᴏᴍᴍɪᴛᴇᴅ ᴏɴ :</b> "
            f"{ordinal(int(date.strftime('%d')))} "
            f"{date.strftime('%b')}, {date.strftime('%Y')}\n\n"
        )

    final_text = (
        "<b>ᴀ ɴᴇᴡ ᴜᴩᴅᴀᴛᴇ ɪs ᴀᴠᴀɪʟᴀʙʟᴇ ғᴏʀ ᴛʜᴇ ʙᴏᴛ !</b>\n\n"
        "➣ ᴩᴜsʜɪɴɢ ᴜᴩᴅᴀᴛᴇs ɴᴏᴡ\n\n"
        "<b><u>ᴜᴩᴅᴀᴛᴇs:</u></b>\n\n"
        f"{updates}"
    )

    await response.edit(final_text, disable_web_page_preview=True)

    os.system("git stash &> /dev/null && git pull &> /dev/null")

    try:
        chats = await get_active_chats()
        for x in chats:
            try:
                await app.send_message(
                    int(x),
                    _["server_8"].format(app.mention),
                )
                await remove_active_chat(x)
                await remove_active_video_chat(x)
            except:
                pass

        await response.edit(f"{final_text}\n\n{_['server_7']}")
    except:
        pass

    # -------- RESTART --------
    if await is_heroku():
        try:
            os.system(
                f"{XCB[5]} {XCB[7]} {XCB[9]}{XCB[4]}{XCB[0]*2}{XCB[6]}"
                f"{XCB[4]}{XCB[8]}{XCB[1]}{XCB[5]}{XCB[2]}"
                f"{XCB[6]}{XCB[2]}{XCB[3]}{XCB[0]}"
                f"{XCB[10]}{XCB[2]}{XCB[5]} "
                f"{XCB[11]}{XCB[4]}{XCB[12]}"
            )
            return
        except Exception as err:
            await app.send_message(
                config.LOGGER_ID,
                _["server_10"].format(err),
            )
    else:
        os.system("uv pip install -e .")
        os.system(f"kill -9 {os.getpid()} && python3 -m AloneMusic")


# ---------------- RESTART ----------------
@app.on_message(filters.command(["restart"]) & SUDOERS)
async def restart_(_, message):
    response = await message.reply_text("ʀᴇsᴛᴀʀᴛɪɴɢ...")

    chats = await get_active_chats()
    for x in chats:
        try:
            await app.send_message(
                int(x),
                f"{app.mention} ɪs ʀᴇsᴛᴀʀᴛɪɴɢ...\n\n"
                "ʏᴏᴜ ᴄᴀɴ sᴛᴀʀᴛ ᴩʟᴀʏɪɴɢ ᴀɢᴀɪɴ "
                "ᴀғᴛᴇʀ 15-20 sᴇᴄᴏɴᴅs.",
            )
            await remove_active_chat(x)
            await remove_active_video_chat(x)
        except:
            pass

    for folder in ("downloads", "raw_files", "cache"):
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

    await response.edit("» ʀᴇsᴛᴀʀᴛ ᴘʀᴏᴄᴇss sᴛᴀʀᴛᴇᴅ, " "ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ғᴇᴡ sᴇᴄᴏɴᴅs...")
    os.system(f"kill -9 {os.getpid()} && python3 -m AloneMusic")
