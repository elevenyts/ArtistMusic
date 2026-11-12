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
	"strings"
	"time"

	td "github.com/Kanha/Meow"

	"KanhaMusic/config"
	"KanhaMusic/kanha/locales"
	"KanhaMusic/kanha/logger"
	"KanhaMusic/kanha/utils"
)

const bugCooldown = 5 * time.Minute

func init() {
	helpTexts["/bug"] = `<i>Report a bug, issue, or unexpected behavior directly to the bot developers.</i>

<u>Usage:</u>
<b>/bug &lt;description&gt;</b> — Send a bug report with a short explanation.
<b>Reply + /bug</b> — Report a specific message or media as a bug.

<b>🧠 Details:</b>
When used, the bot forwards your report (and the replied message, if any) to the <b>owner</b> and <b>logger</b> chats.
Flood protection is applied — you can send one report every <b>5 minutes</b> per chat.

<b>⚠️ Note:</b>
Reports are used for debugging only. Spamming this command may restrict your access.`
}

func bugHandler(c *td.Client, m *td.Message) error {
	if isChannel(c, m) {
		return nil
	}

	chatID := m.ChatID()
	reason := strings.TrimSpace(m.Args())
	replyID := m.ReplyToMessageID()

	if reason == "" && replyID == 0 {
		_, err := m.ReplyText(c, F(chatID, "bug_usage", locales.Arg{
			"cmd": getCommand(m),
		}), nil)
		return err
	}

	floodKey := fmt.Sprintf("bug:%d:%d", chatID, m.SenderID())
	if remaining := utils.GetFlood(floodKey); remaining > 0 {
		_, err := m.ReplyText(c, F(chatID, "flood_minutes", locales.Arg{
			"duration": utils.FormatDuration(int(remaining.Seconds())),
		}), nil)
		return err
	}
	utils.SetFlood(floodKey, bugCooldown)

	targets := bugTargets()

	// Forward the replied message (if any) so devs see the actual content.
	if replyID != 0 {
		if replied, err := m.GetRepliedMessage(c); err == nil && replied != nil {
			for _, target := range targets {
				if _, err := replied.Forward(c, target, nil); err != nil {
					logger.Errorf("bug: failed to forward to %d: %v", target, err)
				}
			}
		}
	}

	sender, _ := m.GetUser(c)

	chatName := F(chatID, "bug_private_chat")
	if !m.IsPrivate() {
		if chat, err := m.GetChat(c); err == nil && chat != nil {
			chatName = utils.EscapeHTML(chat.Title)
			if l, err := m.GetLink(c); err == nil && l != nil && l.IsPublic {
				chatName = fmt.Sprintf("<a href=\"%s\">%s</a>", l.Link, chatName)
			}
		}
	}

	report := utils.EscapeHTML(reason)
	if report == "" {
		report = F(chatID, "bug_reply_only")
	}

	reportMsg := F(chatID, "bug_report_format", locales.Arg{
		"user":    mentionOf(sender, m.SenderID()),
		"user_id": m.SenderID(),
		"chat":    chatName,
		"chat_id": chatID,
		"report":  report,
	})

	for _, target := range targets {
		if _, err := c.SendTextMessage(
			target,
			reportMsg,
			&td.SendTextMessageOpts{ParseMode: "HTML", DisableWebPagePreview: true},
		); err != nil {
			logger.Errorf("bug: failed to send report to %d: %v", target, err)
		}
	}

	_, err := m.ReplyText(c, F(chatID, "bug_thanks"), nil)
	return err
}

// bugTargets returns the unique chats that should receive bug reports.
func bugTargets() []int64 {
	var targets []int64
	if config.LoggerID != 0 {
		targets = append(targets, config.LoggerID)
	}
	if config.OwnerID != 0 && config.OwnerID != config.LoggerID {
		targets = append(targets, config.OwnerID)
	}
	return targets
}
