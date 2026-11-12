/*
 * ● KanhaMusic
 * ○ A high-performance engine for streaming music in Telegram voicechats.
 *
 * Copyright (C) 2026 Kanha
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 * Repository: https://github.com/Oyekanhaa/KanhaMusic
 */

package modules

import (
	"KanhaMusic/kanha/logger"

	td "github.com/Kanha/Meow"

	"KanhaMusic/config"
	"KanhaMusic/kanha/database"
)

// BotCommands holds all bot commands separated by user type and chat type.
type BotCommands struct {
	PrivateUserCommands  []td.BotCommand
	PrivateSudoCommands  []td.BotCommand
	PrivateOwnerCommands []td.BotCommand
	GroupUserCommands    []td.BotCommand
	GroupAdminCommands   []td.BotCommand
}

func cmd(command, description string) td.BotCommand {
	return td.BotCommand{Command: command, Description: description}
}

var AllCommands = BotCommands{
	PrivateUserCommands: []td.BotCommand{
		cmd("start", "sᴛᴧʀᴛ ᴛʜє ʙσᴛ"),
		cmd("help", "sʜσᴡ ᴛʜє ʜєʟᴘ ᴍєηᴜ"),
		cmd("ping", "ᴄʜєᴄᴋ ɪғ ᴛʜє ʙσᴛ ɪs ᴧʟɪᴠє"),
		cmd("repo", "sʜσᴡ sσᴜʀᴄє ᴄσᴅє ʀєᴘσsɪᴛσʀʏ"),
		cmd("createplaylist", "ᴄʀєᴧᴛє ᴧ ηєᴡ ᴘʟᴧʏʟɪsᴛ"),
		cmd("deleteplaylist", "ᴅєʟєᴛє ᴧ ᴘʟᴧʏʟɪsᴛ"),
		cmd("addtoplaylist", "ᴧᴅᴅ ᴧ ᴛʀᴧᴄᴋ ᴛσ ᴧ ᴘʟᴧʏʟɪsᴛ"),
		cmd("removefromplaylist", "ʀєᴍσᴠє ᴧ ᴛʀᴧᴄᴋ ғʀσᴍ ᴧ ᴘʟᴧʏʟɪsᴛ"),
		cmd("playlistinfo", "sʜσᴡ ᴧ ᴘʟᴧʏʟɪsᴛ's ᴛʀᴧᴄᴋs"),
		cmd("myplaylists", "ʟɪsᴛ ʏσᴜʀ ᴘʟᴧʏʟɪsᴛs"),
	},

	PrivateSudoCommands: []td.BotCommand{
		cmd("ac", "sʜσᴡ ᴧᴄᴛɪᴠє ᴠσɪᴄє ᴄʜᴧᴛs"),
		cmd("stats", "sʜσᴡ ʙσᴛ sᴛᴧᴛs"),
		cmd("logger", "єηᴧʙʟє/ᴅɪsᴧʙʟє ʟσɢɢєʀ ᴄʜᴧηηєʟ"),
		cmd("autoleave", "єηᴧʙʟє/ᴅɪsᴧʙʟє ᴧᴜᴛσ ʟєᴧᴠє"),
	},

	PrivateOwnerCommands: []td.BotCommand{
		cmd("addsudo", "ᴧᴅᴅ ᴧ sᴜᴅσ ᴜsєʀ"),
		cmd("delsudo", "ʀєᴍσᴠє ᴧ sᴜᴅσ ᴜsєʀ"),
		cmd("blockuser", "ʙʟσᴄᴋ ᴧ ᴜsєʀ"),
		cmd("unblockuser", "ᴜηʙʟσᴄᴋ ᴧ ᴜsєʀ"),
		cmd("blockchat", "ʙʟσᴄᴋ ᴧ ᴄʜᴧᴛ"),
		cmd("unblockchat", "ᴜηʙʟσᴄᴋ ᴧ ᴄʜᴧᴛ"),
		cmd("blacklisted", "ʟɪsᴛ ʙʟᴧᴄᴋʟɪsᴛєᴅ ᴄʜᴧᴛs ᴧηᴅ ᴜsєʀs"),
		cmd("maintenance", "єηᴧʙʟє/ᴅɪsᴧʙʟє ᴍᴧɪηᴛєηᴧηᴄє ᴍσᴅє"),
	},

	GroupUserCommands: []td.BotCommand{
		cmd("play", "ᴘʟᴧʏ ᴧ sσηɢ"),
		cmd("queue", "sʜσᴡ ᴛʜє ǫᴜєᴜє"),
		cmd("position", "sʜσᴡ ᴛʜє ᴄᴜʀʀєηᴛ ᴘσsɪᴛɪση σғ ᴛʜє sσηɢ"),
		cmd("reload", "ʀєʟσᴧᴅ ᴛʜє ᴧᴅᴍɪη ᴄᴧᴄʜє"),
		cmd("authlist", "ʟɪsᴛ ᴧᴜᴛʜσʀɪᴢєᴅ ᴜsєʀs"),
		cmd("repo", "sʜσᴡ sσᴜʀᴄє ᴄσᴅє ʀєᴘσsɪᴛσʀʏ"),
	},

	GroupAdminCommands: []td.BotCommand{
		// Playback
		cmd("play", "ᴘʟᴧʏ ᴧ sσηɢ"),
		cmd("cplay", "ᴘʟᴧʏ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),
		cmd("fplay", "ғσʀᴄє ᴘʟᴧʏ ᴧ sσηɢ"),
		cmd("cfplay", "ғσʀᴄє ᴘʟᴧʏ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),

		// Pause / Resume
		cmd("pause", "ᴘᴧᴜsє ᴛʜє ᴄᴜʀʀєηᴛ sσηɢ"),
		cmd("cpause", "ᴘᴧᴜsє ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),
		cmd("resume", "ʀєsᴜᴍє ᴛʜє ᴄᴜʀʀєηᴛ sσηɢ"),
		cmd("cresume", "ʀєsᴜᴍє ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),

		// Skip
		cmd("skip", "sᴋɪᴘ ᴛʜє ᴄᴜʀʀєηᴛ sσηɢ"),
		cmd("cskip", "sᴋɪᴘ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),
		cmd("askip", "sᴋɪᴘ ᴛσ ηєxᴛ ᴧᴜᴛσᴘʟᴧʏ ᴛʀᴧᴄᴋ"),
		cmd("caskip", "sᴋɪᴘ ᴛσ ηєxᴛ ᴧᴜᴛσᴘʟᴧʏ ɪη ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),

		// Replay
		cmd("replay", "ʀєᴘʟᴧʏ ᴛʜє ᴄᴜʀʀєηᴛ sσηɢ"),
		cmd("creplay", "ʀєᴘʟᴧʏ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),

		// End / Stop
		cmd("end", "sᴛσᴘ ᴛʜє sσηɢ ᴧηᴅ ʟєᴧᴠє ᴠσɪᴄє ᴄʜᴧᴛ"),
		cmd("cstop", "sᴛσᴘ ᴧηᴅ ʟєᴧᴠє ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ᴠσɪᴄє ᴄʜᴧᴛ"),

		// Mute / Unmute
		cmd("mute", "ᴍᴜᴛє ᴛʜє ʙσᴛ ɪη ᴛʜє ᴠσɪᴄє ᴄʜᴧᴛ"),
		cmd("unmute", "ᴜηᴍᴜᴛє ᴛʜє ʙσᴛ ɪη ᴛʜє ᴠσɪᴄє ᴄʜᴧᴛ"),
		cmd("cmute", "ᴍᴜᴛє ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ᴠσɪᴄє ᴄʜᴧᴛ"),
		cmd("cunmute", "ᴜηᴍᴜᴛє ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ᴠσɪᴄє ᴄʜᴧᴛ"),

		// Seek
		cmd("seek", "sєєᴋ ᴛσ ᴧ sᴘєᴄɪғɪᴄ ᴘσsɪᴛɪση"),
		cmd("seekback", "sєєᴋ ʙᴧᴄᴋ ɪη ᴛʜє sσηɢ"),
		cmd("cseek", "sєєᴋ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's sσηɢ"),
		cmd("cseekback", "sєєᴋ ʙᴧᴄᴋ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's sσηɢ"),

		// Speed
		cmd("speed", "sєᴛ ᴛʜє ᴘʟᴧʏʙᴧᴄᴋ sᴘєєᴅ"),
		cmd("cspeed", "sєᴛ ᴛʜє ᴘʟᴧʏʙᴧᴄᴋ sᴘєєᴅ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),

		// Queue management
		cmd("queue", "sʜσᴡ ᴛʜє ǫᴜєᴜє"),
		cmd("cqueue", "sʜσᴡ ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ǫᴜєᴜє"),
		cmd("position", "sʜσᴡ ᴛʜє ᴄᴜʀʀєηᴛ ᴘσsɪᴛɪση σғ ᴛʜє sσηɢ"),
		cmd("cposition", "sʜσᴡ ᴛʜє ᴄᴜʀʀєηᴛ ᴘσsɪᴛɪση ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),
		cmd("jump", "ᴊᴜᴍᴘ ᴛσ ᴧ sᴘєᴄɪғɪᴄ sσηɢ ɪη ᴛʜє ǫᴜєᴜє"),
		cmd("cjump", "ᴊᴜᴍᴘ ᴛσ ᴧ sσηɢ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ǫᴜєᴜє"),
		cmd("remove", "ʀєᴍσᴠє ᴧ sσηɢ ғʀσᴍ ᴛʜє ǫᴜєᴜє"),
		cmd("cremove", "ʀєᴍσᴠє ᴧ sσηɢ ғʀσᴍ ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ǫᴜєᴜє"),
		cmd("move", "ᴍσᴠє ᴧ sσηɢ ɪη ᴛʜє ǫᴜєᴜє"),
		cmd("cmove", "ᴍσᴠє ᴧ sσηɢ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ǫᴜєᴜє"),
		cmd("clear", "ᴄʟєᴧʀ ᴛʜє ǫᴜєᴜє"),
		cmd("cclear", "ᴄʟєᴧʀ ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ǫᴜєᴜє"),
		cmd("shuffle", "sʜᴜғғʟє ᴛʜє ǫᴜєᴜє"),
		cmd("cshuffle", "sʜᴜғғʟє ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ's ǫᴜєᴜє"),
		cmd("loop", "ʟσσᴘ ᴛʜє ᴄᴜʀʀєηᴛ sσηɢ"),
		cmd("cloop", "ʟσσᴘ ᴛʜє ᴄᴜʀʀєηᴛ sσηɢ ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),

		cmd("setcplay", "ᴄσηғɪɢᴜʀє ᴄʜᴧηηєʟᴘʟᴧʏ ғσʀ ʏσᴜʀ ᴄʜᴧᴛ"),

		// Settings & access
		cmd("playmode", "ᴄσηᴛʀσʟ ᴡʜσ ᴄᴧη ᴜsє /ᴘʟᴧʏ"),
		cmd("adminmode", "ᴄσηᴛʀσʟ ᴡʜσ ᴄᴧη ᴜsє ᴧᴅᴍɪη ᴍᴜsɪᴄ ᴄσᴍᴍᴧηᴅs"),
		cmd("cmddelete", "ᴛσɢɢʟє ᴧᴜᴛσᴍᴧᴛɪᴄ ᴅєʟєᴛɪση σғ ʙσᴛ ᴄσᴍᴍᴧηᴅs"),
		cmd("autoplay", "ᴛσɢɢʟє ᴧᴜᴛσᴘʟᴧʏ ʀєᴄσᴍᴍєηᴅᴧᴛɪσηs"),
		cmd("vclogger", "ᴛσɢɢʟє ᴠσɪᴄє ᴄʜᴧᴛ ᴧʟєʀᴛs"),
		cmd("vcstatus", "ᴠɪєᴡ ᴠσɪᴄє ᴄʜᴧᴛ ʟσɢɢєʀ sᴛᴧᴛᴜs"),
		cmd("settings", "ᴄσηғɪɢᴜʀє ᴄʜᴧᴛ sєᴛᴛɪηɢs"),
		cmd("addauth", "ᴧᴅᴅ ᴧ ᴜsєʀ ᴛσ ᴛʜє ᴧᴜᴛʜσʀɪᴢєᴅ ʟɪsᴛ"),
		cmd("delauth", "ʀєᴍσᴠє ᴧ ᴜsєʀ ғʀσᴍ ᴛʜє ᴧᴜᴛʜσʀɪᴢєᴅ ʟɪsᴛ"),
		cmd("reload", "ʀєʟσᴧᴅ ᴛʜє ᴧᴅᴍɪη ᴄᴧᴄʜє"),
		cmd("creload", "ʀєʟσᴧᴅ ᴛʜє ᴧᴅᴍɪη ᴄᴧᴄʜє ɪη ᴛʜє ʟɪηᴋєᴅ ᴄʜᴧηηєʟ"),
	},
}

func setBotCommands(bot *td.Client) {
	type scopedCmds struct {
		scope td.BotCommandScope
		cmds  []td.BotCommand
	}

	entries := []scopedCmds{
		{&td.BotCommandScopeAllPrivateChats{}, AllCommands.PrivateUserCommands},
		{&td.BotCommandScopeAllGroupChats{}, AllCommands.GroupUserCommands},
		{
			&td.BotCommandScopeAllChatAdministrators{},
			append(AllCommands.GroupUserCommands, AllCommands.GroupAdminCommands...),
		},
		{
			&td.BotCommandScopeChat{ChatId: config.OwnerID},
			append(
				append(AllCommands.PrivateUserCommands, AllCommands.PrivateSudoCommands...),
				AllCommands.PrivateOwnerCommands...,
			),
		},
	}

	for _, e := range entries {
		if err := bot.SetCommands(e.cmds, "", &td.SetCommandsOpts{Scope: e.scope}); err != nil {
			logger.Errorf("Failed to set bot commands(Scope: %T): %v", e.scope, err)
		}
	}

	// Sudo users get their own command scope in private.
	sudoers, err := database.Sudoers()
	if err != nil {
		logger.Error("Failed to fetch sudoers: " + err.Error())
		return
	}

	sudoCmds := append(AllCommands.PrivateUserCommands, AllCommands.PrivateSudoCommands...)
	for _, id := range sudoers {
		scope := &td.BotCommandScopeChat{ChatId: id}
		if err := bot.SetCommands(sudoCmds, "", &td.SetCommandsOpts{Scope: scope}); err != nil {
			logger.Error("Failed to set sudo commands: " + err.Error())
		}
	}
}
