#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/TheAloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/TheAloneMusic/blob/master/LICENSE >
#
# All rights reserved.

import os
import shutil
import time
from shutil import disk_usage
from typing import Dict, Tuple

from humanize import naturalsize
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from AloneMusic import app
from AloneMusic.misc import SUDOERS

# Constants
CLEANABLE_FOLDERS = ["downloads", "cache", "temp"]
MAX_FOLDER_DEPTH = 3  # How many subfolder levels to show


def get_folder_stats(folder: str) -> Tuple[int, int]:
    """Get total size and file count for a folder."""
    total_size = 0
    file_count = 0
    for root, _, files in os.walk(folder):
        file_count += len(files)
        for file in files:
            try:
                total_size += os.path.getsize(os.path.join(root, file))
            except (OSError, PermissionError):
                continue
    return total_size, file_count


def get_folder_structure(folder: str, depth: int = 0) -> Dict[str, Tuple[int, int]]:
    """Get folder structure with sizes and counts up to specified depth."""
    if depth > MAX_FOLDER_DEPTH:
        return {}

    structure = {}
    try:
        for item in os.listdir(folder):
            path = os.path.join(folder, item)
            if os.path.isdir(path):
                size, count = get_folder_stats(path)
                structure[item] = (size, count, get_folder_structure(path, depth + 1))
    except (OSError, PermissionError):
        pass
    return structure


def format_folder_structure(
    structure: Dict[str, Tuple[int, int, Dict]], indent: int = 0
) -> str:
    """Format folder structure for display."""
    if not structure:
        return ""

    msg = ""
    prefix = "    " * indent
    for name, (size, count, substructure) in sorted(structure.items()):
        msg += f"{prefix}📁 {name}/\n"
        msg += f"{prefix}├ Files: <code>{count}</code>\n"
        msg += f"{prefix}└ Size: <code>{naturalsize(size)}</code>\n"
        msg += format_folder_structure(substructure, indent + 1)
    return msg


async def create_cleanable_folders():
    """Ensure all cleanable folders exist."""
    for folder in CLEANABLE_FOLDERS:
        if not os.path.exists(folder):
            os.makedirs(folder)


@app.on_message(filters.command("clean") & SUDOERS)
async def show_storage(_, message: Message):
    """Show storage overview with cleaning options."""
    await create_cleanable_folders()

    # Get folder statistics
    folder_info = {}
    for folder in CLEANABLE_FOLDERS:
        total_size, file_count = get_folder_stats(folder)
        structure = get_folder_structure(folder)
        folder_info[folder] = {
            "size": total_size,
            "count": file_count,
            "structure": structure,
        }

    total_files = sum(info["count"] for info in folder_info.values())
    total_size = sum(info["size"] for info in folder_info.values())

    # Get disk statistics
    total_disk, used_disk, free_disk = disk_usage("/")
    used_percent = (used_disk / total_disk) * 100
    free_percent = (free_disk / total_disk) * 100

    # Prepare message
    msg = (
        "<b>🗄 Storage Overview</b>\n\n"
        f"<b>📦 Total Storage Used:</b> <code>{naturalsize(total_size)}</code>\n"
        f"<b>📝 Total Files:</b> <code>{total_files}</code>\n\n"
    )

    # Add folder information
    for folder in CLEANABLE_FOLDERS:
        info = folder_info[folder]
        msg += (
            f"<b>📁 {folder}/</b>\n"
            f"├ Files: <code>{info['count']}</code>\n"
            f"└ Size : <code>{naturalsize(info['size'])}</code>\n"
        )

        # Add folder structure if not empty
        if info["structure"]:
            msg += "\n<u>Subfolders:</u>\n"
            msg += format_folder_structure(info["structure"])

        msg += "\n"

    # Disk information
    msg += (
        "<b>💾 Disk Information</b>\n"
        f"├ Total: <code>{naturalsize(total_disk)}</code>\n"
        f"├ Used : <code>{naturalsize(used_disk)}</code> ({used_percent:.1f}%)\n"
        f"└ Free : <code>{naturalsize(free_disk)}</code> ({free_percent:.1f}%)\n\n"
        "<i>Select folders to clean below</i>"
    )

    # Create buttons
    buttons = []
    row = []
    for folder in CLEANABLE_FOLDERS:
        row.append(
            InlineKeyboardButton(
                f"🧹 {folder.capitalize()}", callback_data=f"clean_{folder}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🚀 Clean All", callback_data="clean_all")])

    await message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True
    )


async def clean_folder(folder: str) -> Tuple[bool, str]:
    """Clean a specific folder and return status."""
    try:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        return True, f"✅ <b>{folder}/</b> cleaned successfully"
    except Exception as e:
        return False, f"❌ Failed to clean {folder}/\n<code>{e}</code>"


@app.on_callback_query(filters.regex(r"^clean_(downloads|cache|temp|all)$") & SUDOERS)
async def handle_clean_callback(_, query):
    """Handle all cleaning callbacks."""
    action = query.data.split("_")[1]

    if action == "all":
        results = []
        for folder in CLEANABLE_FOLDERS:
            success, message = await clean_folder(folder)
            results.append(message)
            time.sleep(0.5)

        await query.answer("Cleaned all folders")
        await query.message.edit_text("\n".join(results))
        return

    success, message = await clean_folder(action)
    await query.answer("✅ Done" if success else "❌ Error")
    await query.message.edit_text(message)
    time.sleep(2)
    await show_storage(_, query.message)
