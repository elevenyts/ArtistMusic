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

import asyncio

from pyrogram import enums, errors, types

from ArtistMusic import app, config, db, queue, yt
from ArtistMusic.core.mongo import NoAssistantAvailable


def checkUB(play):
    async def wrapper(_, m: types.Message):
        async def safe_reply(text):
            """Safely send reply, return None if chat doesn't allow messages"""
            try:
                return await m.reply_text(text)
            except (errors.ChatWriteForbidden, errors.ChatSendPlainForbidden):
                # Chat doesn't allow text messages - silently return
                return None
            except Exception:
                return None
        
        if not m.from_user:
            await safe_reply(m.lang["play_user_invalid"])
            return

        if m.chat.type != enums.ChatType.SUPERGROUP:
            await safe_reply(m.lang["play_chat_invalid"])
            return await app.leave_chat(m.chat.id)

        if not m.reply_to_message and (
            len(m.command) < 2 or (len(m.command)
                                   == 2 and m.command[1] == "-f")
        ):
            await safe_reply(m.lang["play_usage"])
            return

        if len(queue.get_queue(m.chat.id)) >= config.QUEUE_LIMIT:
            await safe_reply(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))
            return

        command = m.command[0].lower()
        force = command.endswith("force") or (
            len(m.command) > 1 and "-f" in m.command[1]
        )
        cplay = command.startswith("c")

        video_requested = command.startswith("v") or command.startswith("cv")
        if video_requested and not await db.get_vplay_enabled():
            await safe_reply(m.lang["play_video_disabled"])
            return
        video = video_requested
        
        url = yt.url(m)
        # Only validate URL if not replying to media (Telegram files have t.me URLs)
        if url and not m.reply_to_message and not yt.valid(url):
            return await m.reply_text(m.lang["play_unsupported"])

        play_mode = await db.get_play_mode(m.chat.id)
        force_admin = await db.get_force_mode(m.chat.id)
        if play_mode or (force and force_admin):
            adminlist = await db.get_admins(m.chat.id)
            if (
                m.from_user.id not in adminlist
                and not await db.is_auth(m.chat.id, m.from_user.id)
                and not m.from_user.id in app.sudoers
            ):
                await safe_reply(m.lang["play_admin"])
                return

        if m.chat.id not in db.active_calls:
            try:
                client = await db.get_client(m.chat.id)
            except NoAssistantAvailable:
                await safe_reply(m.lang["no_assistant"])
                return
            try:
                member = await app.get_chat_member(m.chat.id, client.id)
                if member.status in [
                    enums.ChatMemberStatus.BANNED,
                    enums.ChatMemberStatus.RESTRICTED,
                ]:
                    try:
                        await app.unban_chat_member(
                            chat_id=m.chat.id, user_id=client.id
                        )
                    except:
                        await safe_reply(
                            m.lang["play_banned"].format(
                                app.name,
                                client.id,
                                client.mention,
                                f"@{client.username}" if client.username else None,
                            )
                        )
                        return
            except errors.ChatAdminRequired:
                await safe_reply(
                    f"<blockquote><b>🔐 Bot Admin Required</b></blockquote>\n\n"
                    f"<blockquote>To play music in this chat, I need to be an <b>administrator</b>.\n\n"
                    f"<b>Required permissions:</b>\n"
                    f"• Manage Voice Chats\n"
                    f"• Invite Users via Link\n"
                    f"• Delete Messages\n\n"
                    f"Please promote me as admin with the required permissions.</blockquote>"
                )
                return
            except errors.UserNotParticipant:
                if m.chat.username:
                    invite_link = m.chat.username
                    try:
                        await client.resolve_peer(invite_link)
                    except:
                        pass
                else:
                    try:
                        invite_link = (await app.get_chat(m.chat.id)).invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(m.chat.id)
                    except errors.ChatAdminRequired:
                        await safe_reply(
                            f"<blockquote><b>🔐 Bot Admin Required</b></blockquote>\n\n"
                            f"<blockquote>To play music in this chat, I need to be an <b>administrator</b>.\n\n"
                            f"<b>Required permissions:</b>\n"
                            f"• Manage Voice Chats\n"
                            f"• Invite Users via Link\n"
                            f"• Delete Messages\n\n"
                            f"Please promote me as admin with the required permissions.</blockquote>"
                        )
                        return
                    except errors.ChatAdminRequired:
                        await safe_reply(
                            f"<blockquote><b>🔐 Bot Admin Required</b></blockquote>\n\n"
                            f"<blockquote>To play music in this chat, I need to be an <b>administrator</b>.\n\n"
                            f"<b>Required permissions:</b>\n"
                            f"• Manage Voice Chats\n"
                            f"• Invite Users via Link\n"
                            f"• Delete Messages\n\n"
                            f"Please promote me as admin with the required permissions.</blockquote>"
                        )
                        return
                    except Exception as ex:
                        await safe_reply(
                            m.lang["play_invite_error"].format(
                                type(ex).__name__)
                        )
                        return

                umm = await safe_reply(m.lang["play_invite"].format(app.name))
                if umm:
                    await asyncio.sleep(2)
                try:
                    await client.join_chat(invite_link)
                except errors.UserAlreadyParticipant:
                    pass
                except errors.InviteRequestSent:
                    try:
                        await client.approve_chat_join_request(m.chat.id, client.id)
                    except errors.ChatAdminRequired:
                        if umm:
                            try:
                                await umm.edit_text(
                                    f"<blockquote><b>🔐 Bot Admin Required</b></blockquote>\n\n"
                                    f"<blockquote>To play music in this chat, I need to be an <b>administrator</b>.\n\n"
                                    f"<b>Required permissions:</b>\n"
                                    f"• Manage Voice Chats\n"
                                    f"• Invite Users via Link\n"
                                    f"• Delete Messages\n\n"
                                    f"Please promote me as admin with the required permissions.</blockquote>"
                                )
                            except:
                                pass
                        return
                    except Exception as ex:
                        if umm:
                            try:
                                await umm.edit_text(
                                    m.lang["play_invite_error"].format(
                                        type(ex).__name__)
                                )
                            except:
                                pass
                        return
                except errors.ChatAdminRequired:
                    if umm:
                        try:
                            await umm.edit_text(
                                f"<blockquote><b>🔐 Bot Admin Required</b></blockquote>\n\n"
                                f"<blockquote>To play music in this chat, I need to be an <b>administrator</b>.\n\n"
                                f"<b>Required permissions:</b>\n"
                                f"• Manage Voice Chats\n"
                                f"• Invite Users via Link\n"
                                f"• Delete Messages\n\n"
                                f"Please promote me as admin with the required permissions.</blockquote>"
                            )
                        except:
                            pass
                    return
                except Exception as ex:
                    if umm:
                        try:
                            await umm.edit_text(
                                m.lang["play_invite_error"].format(type(ex).__name__)
                            )
                        except:
                            pass
                    return

                if umm:
                    try:
                        await umm.delete()
                    except:
                        pass
                await client.resolve_peer(m.chat.id)

        try:
            await m.delete()
        except:
            pass

        return await play(_, m, force, url, cplay, video)

    return wrapper
