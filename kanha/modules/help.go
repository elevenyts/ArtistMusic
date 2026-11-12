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
	"fmt"
	"html"
	"strings"
	"unicode/utf16"

	td "github.com/Kanha/Meow"

	"KanhaMusic/config"
	"KanhaMusic/kanha/core"
)

var helpTexts = map[string]string{}

func init() {
	helpTexts["/help"] = fmt.Sprintf(`ℹ️ <b>Help Command</b>
<i>Displays general bot help or detailed information about a specific command.</i>

<u>Usage:</u>
<code>/help</code> — Show the main help menu.  
<code>/help &lt;command&gt;</code> — Show help for a specific command.

For more info, visit our <a href="%s">Support Chat</a>.`, config.SupportChat)
}

func helpHandler(c *td.Client, m *td.Message) error {
	if isChannel(c, m) {
		return nil
	}

	args := strings.Fields(m.Text())
	if len(args) > 1 {
		cmd := args[1]
		if cmd != "pm_help" {
			if !strings.HasPrefix(cmd, "/") {
				cmd = "/" + cmd
			}
			return showHelpFor(c, m, cmd)
		}
	}

	if !m.IsPrivate() {
		_, err := m.ReplyText(c, F(m.ChatID(), "help_private_only"), &td.SendTextMessageOpts{
			ReplyMarkup: core.GetGroupHelpKeyboard(m.ChatID()),
		})
		return err
	}

	_, err := m.ReplyText(c, F(m.ChatID(), "help_main"), &td.SendTextMessageOpts{
		ReplyMarkup: core.GetHelpKeyboard(m.ChatID()),
	})
	return err
}

func helpCB(c *td.Client, cb *td.UpdateNewCallbackQuery) error {
	cb.Answer(c, 0, false, "", "")

	msg, err := cb.GetMessage(c)
	if err != nil {
		return err
	}

	markup := core.GetHelpKeyboard(cb.ChatId)

	if isPhotoMessage(msg) {
		_, err = cb.EditMessageCaption(c, F(cb.ChatId, "help_main"), &td.EditCaptionOpts{
			ReplyMarkup: markup,
		})
	} else {
		_, err = cb.EditMessageText(c, F(cb.ChatId, "help_main"), &td.EditTextMessageOpts{
			ReplyMarkup: markup,
		})
	}
	return err
}

func helpCallbackHandler(c *td.Client, cb *td.UpdateNewCallbackQuery) error {
	data := cb.DataString()
	cb.Answer(c, 0, false, "", "")
	if data == "" {
		return nil
	}
	chatID := cb.ChatId
	parts := strings.SplitN(data, ":", 2)
	if len(parts) < 2 {
		return nil
	}

	var text string
	btn := core.GetBackKeyboard(chatID)

	switch parts[1] {
	case "admin":
		text = F(chatID, "help_admin")
	case "auth":
		text = F(chatID, "help_auth")
	case "bcast":
		text = F(chatID, "help_bcast")
	case "play":
		text = F(chatID, "help_play")
	case "sudo":
		text = F(chatID, "help_sudo")
	case "restrict":
		text = F(chatID, "help_restrict")
	case "thumb":
		text = F(chatID, "help_thumb")
	case "start":
		text = F(chatID, "help_start")
	case "autoplay":
		text = F(chatID, "help_autoplay")
	case "playlist":
		text = F(chatID, "help_playlist")
	case "vclogs":
		text = F(chatID, "help_vclogs")
	case "inline":
		text = F(chatID, "help_inline")
	case "main":
		text = F(chatID, "help_main")
		btn = core.GetHelpKeyboard(chatID)
	}

	msg, err := cb.GetMessage(c)
	if err != nil {
		return err
	}

	if isPhotoMessage(msg) {
		// Telegram captions are capped at 1024 UTF-16 units; longer help pages
		// are sent as a plain text message instead of being edited into the photo.
		if len(utf16.Encode([]rune(text))) <= 1024 {
			_, err = cb.EditMessageCaption(c, text, &td.EditCaptionOpts{
				ReplyMarkup: btn,
			})
		} else {
			_ = msg.Delete(c, true)
			_, err = c.SendTextMessage(chatID, text, &td.SendTextMessageOpts{
				ParseMode:   "HTML",
				ReplyMarkup: btn,
			})
		}
	} else {
		_, err = cb.EditMessageText(c, text, &td.EditTextMessageOpts{
			ReplyMarkup: btn,
		})
	}
	return err
}

func showHelpFor(c *td.Client, m *td.Message, cmd string) error {
	helpText, ok := helpTexts[cmd]
	if !ok {
		trimmed := strings.TrimPrefix(cmd, "/")
		if value, exists := helpTexts[trimmed]; exists {
			helpText = value
		}
	}

	if helpText == "" {
		_, err := m.ReplyText(
			c,
			"⚠️ <i>No help found for command <code>"+
				html.EscapeString(cmd)+
				"</code></i>",
			nil,
		)
		return err
	}

	_, err := m.ReplyText(
		c,
		"📘 <b>Help for</b> <code>"+cmd+"</code>:\n\n"+helpText,
		nil,
	)
	return err
}
