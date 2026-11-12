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
	"context"
	"fmt"
	"html"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"KanhaMusic/kanha/logger"

	td "github.com/Kanha/Meow"

	"KanhaMusic/config"
	"KanhaMusic/kanha/core"
	"KanhaMusic/kanha/database"
	"KanhaMusic/kanha/locales"
	"KanhaMusic/kanha/utils"
)

const defaultBroadcastDelay = 0.7

var bManager broadcastManager

type broadcastManager struct {
	mu       sync.Mutex
	cancelFn context.CancelFunc
	stats    *BroadcastStats
}

func (bm *broadcastManager) start(stats *BroadcastStats) (ctx context.Context, ok bool) {
	bm.mu.Lock()
	defer bm.mu.Unlock()

	if bm.cancelFn != nil {
		return nil, false
	}
	ctx, cancel := context.WithCancel(context.Background())
	bm.cancelFn = cancel
	bm.stats = stats
	return ctx, true
}

func (bm *broadcastManager) stop() {
	bm.mu.Lock()
	defer bm.mu.Unlock()
	if bm.cancelFn == nil {
		return
	}

	if bm.stats != nil {
		bm.stats.mu.Lock()
		bm.stats.Cancelled = true
		bm.stats.mu.Unlock()
	}

	bm.cancelFn()
	bm.cancelFn = nil
	bm.stats = nil
}

func (bm *broadcastManager) isActive() bool {
	bm.mu.Lock()
	defer bm.mu.Unlock()
	return bm.cancelFn != nil
}

type BroadcastFlags struct {
	NoChat  bool
	NoUser  bool
	Copy    bool
	Limit   int
	Delay   float64
	Pin     bool
	PinLoud bool
}

type BroadcastStats struct {
	mu          sync.Mutex
	TotalChats  int
	TotalUsers  int
	DoneChats   int
	DoneUsers   int
	FailedChats []int64
	FailedUsers []int64
	Errors      strings.Builder
	Delay       float64
	StartTime   time.Time
	Finished    bool
	Cancelled   bool
	Reasons     map[string]int
}

type broadcastTarget struct {
	id     int64
	isUser bool
}

func init() {
	helpTexts["broadcast"] = `<i>Broadcast a message to all served chats and users.</i>

<u>Commands:</u> <code>/broadcast</code>, <code>/bcast</code>, <code>/gcast</code> (all work the same)

<u>Usage:</u>
<b>/broadcast [flags] [text]</b> — Broadcast a text message.
<b>/broadcast [flags]</b> (reply to a message) — Broadcast the replied message (photo, video, forward, etc.).
<b>/broadcast -cancel</b> — Cancel the ongoing broadcast.

<blockquote>
<b>🎯 Who gets it:</b>
• <code>-user</code> — Only users (DM)
• <code>-group</code> — Only groups
• <code>-all</code> — Users and groups (default)
• <code>-nochat</code> — Exclude groups
• <code>-nouser</code> — Exclude users
</blockquote>
<blockquote>
<b>📋 Options:</b>
• <code>-copy</code> — Send without the forwarded tag (reply mode; used automatically if the message cannot be forwarded)
• <code>-pin</code> — Pin the message (silent)
• <code>-pinloud</code> — Pin the message (with notification)
• <code>-limit [n]</code> — Stop after n targets, groups first (default: 0 = no limit)
• <code>-delay [seconds]</code> — Delay between messages (default: 0.7s)
• <code>-cancel</code> — Cancel the ongoing broadcast
</blockquote>
<blockquote>
<b>📌 Examples:</b>
/broadcast -user Hello everyone
/bcast -group -pin [reply to message]
/gcast -all -copy -limit 50 [reply to message]
/broadcast -user -delay 2 Important announcement
/broadcast -cancel
</blockquote>
<b>⚠️ Notes:</b>
• Only the <b>owner</b> can use this command
• Flags work with one or two dashes (<code>-copy</code> or <code>--copy</code>)
• Text mode sends plain text. For media or formatting, reply to the message
• After every 30 messages, there's an automatic 7.5s pause
• Blocked or deleted users fail; the final report shows the reasons
• You can cancel using the inline button or <code>/broadcast -cancel</code>
• Only one broadcast can run at a time`

	helpTexts["gcast"] = helpTexts["broadcast"]
	helpTexts["bcast"] = helpTexts["broadcast"]
}

func broadcastHandler(c *td.Client, m *td.Message) error {
	if !checkOwner(c, m) {
		return nil
	}
	chatID := m.ChatID()

	for _, w := range strings.Fields(strings.ToLower(m.Text())) {
		if w == "-cancel" || w == "--cancel" {
			return handleBroadcastCancel(c, m)
		}
	}

	if bManager.isActive() {
		_, err := m.ReplyText(c, F(chatID, "broadcast_already_running"), nil)
		return err
	}

	flags, content, err := parseBroadcastCommand(m)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "broadcast_parse_failed", locales.Arg{
			"error": html.EscapeString(err.Error()),
		}), nil)
		return err
	}

	if content == "" && m.ReplyToMessageID() == 0 {
		_, err := m.ReplyText(c, F(chatID, "broadcast_no_content", locales.Arg{
			"cmd": getCommand(m),
		}), nil)
		return err
	}

	chats, users, err := loadBroadcastTargets(c, chatID, flags, m)
	if err != nil {
		return err
	}
	if len(chats) == 0 && len(users) == 0 {
		_, err := m.ReplyText(c, F(chatID, "broadcast_no_targets"), nil)
		return err
	}

	applyBroadcastLimit(flags, &chats, &users)

	stats := &BroadcastStats{
		TotalChats:  len(chats),
		TotalUsers:  len(users),
		Delay:       flags.Delay,
		StartTime:   time.Now(),
		FailedChats: make([]int64, 0),
		FailedUsers: make([]int64, 0),
	}

	ctx, ok := bManager.start(stats)
	if !ok {
		_, err := m.ReplyText(c, F(chatID, "broadcast_already_running"), nil)
		return err
	}

	progressMsg, err := m.ReplyText(c, F(chatID, "broadcast_initializing"),
		&td.SendTextMessageOpts{ReplyMarkup: core.GetBroadcastCancelKeyboard(chatID)})
	if err != nil {
		bManager.stop()
		logger.Errorf("Failed to send broadcast progress message: %v", err)
		return nil
	}

	go bManager.updateProgress(ctx, c, progressMsg, stats)
	go bManager.run(ctx, c, m, progressMsg, flags, content, chats, users, stats)

	return nil
}

func parseBroadcastCommand(m *td.Message) (*BroadcastFlags, string, error) {
	flags := &BroadcastFlags{Delay: defaultBroadcastDelay}

	text := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(m.Text()), getCommand(m)))
	lines := strings.Split(text, "\n")
	if len(lines) == 0 {
		return flags, "", nil
	}

	words := strings.Fields(lines[0])
	var contentWords []string
	var onlyUser, onlyGroup bool

	for i := 0; i < len(words); i++ {
		switch strings.ToLower(words[i]) {
		case "-user", "--user", "-users", "--users":
			onlyUser = true
		case "-group", "--group", "-groups", "--groups", "-chat", "--chat", "-chats", "--chats":
			onlyGroup = true
		case "-all", "--all":
			onlyUser, onlyGroup = true, true
		case "-nochat", "--nochat":
			flags.NoChat = true
		case "-nouser", "--nouser":
			flags.NoUser = true
		case "-copy", "--copy":
			flags.Copy = true
		case "-pin", "--pin":
			flags.Pin = true
		case "-pinloud", "--pinloud":
			flags.PinLoud = true
		case "-limit", "--limit":
			limit, err := strconv.Atoi(nextValue(words, i))
			if err != nil || limit < 0 {
				return nil, "", fmt.Errorf("invalid limit value: %s", nextValue(words, i))
			}
			flags.Limit = limit
			i++
		case "-delay", "--delay":
			delay, err := strconv.ParseFloat(nextValue(words, i), 64)
			if err != nil || delay < 0 {
				return nil, "", fmt.Errorf("invalid delay value: %s", nextValue(words, i))
			}
			flags.Delay = delay
			i++
		case "-cancel", "--cancel":
		default:
			contentWords = append(contentWords, words[i])
		}
	}

	if onlyUser && !onlyGroup {
		flags.NoChat = true
	}
	if onlyGroup && !onlyUser {
		flags.NoUser = true
	}

	content := strings.Join(contentWords, " ")
	if len(lines) > 1 {
		if content != "" {
			content += "\n"
		}
		content += strings.Join(lines[1:], "\n")
	}

	return flags, strings.TrimSpace(content), nil
}

func nextValue(words []string, i int) string {
	if i+1 < len(words) {
		return words[i+1]
	}
	return ""
}

func loadBroadcastTargets(
	c *td.Client,
	chatID int64,
	flags *BroadcastFlags,
	m *td.Message,
) (chats, users []int64, err error) {
	if !flags.NoChat {
		chats, err = database.ServedChats()
		if err != nil {
			if _, rerr := m.ReplyText(c, F(chatID, "broadcast_fetch_chats_failed", locales.Arg{
				"error": html.EscapeString(err.Error()),
			}), nil); rerr != nil {
				return nil, nil, rerr
			}
			return nil, nil, err
		}
	}

	if !flags.NoUser {
		users, err = database.ServedUsers()
		if err != nil {
			if _, rerr := m.ReplyText(c, F(chatID, "broadcast_fetch_users_failed", locales.Arg{
				"error": html.EscapeString(err.Error()),
			}), nil); rerr != nil {
				return nil, nil, rerr
			}
			return nil, nil, err
		}
	}

	return chats, users, nil
}

func applyBroadcastLimit(flags *BroadcastFlags, chats, users *[]int64) {
	if flags.Limit <= 0 || len(*chats)+len(*users) <= flags.Limit {
		return
	}
	if len(*chats) >= flags.Limit {
		*chats = (*chats)[:flags.Limit]
		*users = nil
		return
	}
	remaining := flags.Limit - len(*chats)
	if len(*users) > remaining {
		*users = (*users)[:remaining]
	}
}

func (bm *broadcastManager) run(
	ctx context.Context,
	c *td.Client,
	m, progressMsg *td.Message,
	flags *BroadcastFlags,
	content string,
	chats, users []int64,
	stats *BroadcastStats,
) {
	defer bm.stop()
	defer func() {
		if r := recover(); r != nil {
			logger.Errorf("Broadcast panic recovered: %v", r)
		}
		bm.finalize(c, progressMsg, stats)
	}()

	if rid := m.ReplyToMessageID(); rid > 0 {
		props, perr := c.GetMessageProperties(m.ChatID(), rid)
		if perr == nil {
			outgoing := false
			if rm, gerr := c.GetMessage(m.ChatID(), rid); gerr == nil && rm != nil {
				outgoing = rm.IsOutgoing
			}
			logger.Infof(
				"[broadcast] replied msg=%d chat=%d can_be_forwarded=%v can_be_copied=%v sent_by_bot=%v copy_flag=%v",
				rid, m.ChatID(), props.CanBeForwarded, props.CanBeCopied, outgoing, flags.Copy,
			)
		}
		switch {
		case perr != nil:
			logger.Warnf("[broadcast] GetMessageProperties failed: %v", perr)
		case !props.CanBeForwarded && !props.CanBeCopied:
			logger.Warnf("[broadcast] replied message cannot be forwarded or copied (protected content)")
		case !props.CanBeForwarded:
			logger.Warnf("[broadcast] replied message cannot be forwarded, switching to copy mode")
			flags.Copy = true
		}
	}

	targets := make([]broadcastTarget, 0, len(chats)+len(users))
	for _, id := range chats {
		targets = append(targets, broadcastTarget{id: id})
	}
	for _, id := range users {
		targets = append(targets, broadcastTarget{id: id, isUser: true})
	}

	sent := 0
	for _, t := range targets {
		select {
		case <-ctx.Done():
			return
		default:
		}

		recordTarget(t, bm.send(ctx, c, m, t.id, content, flags), stats)

		sent++
		if !bm.wait(ctx, sent, flags.Delay) {
			return
		}
	}
}

func (bm *broadcastManager) send(
	ctx context.Context,
	c *td.Client,
	m *td.Message,
	targetID int64,
	content string,
	flags *BroadcastFlags,
) error {
	var (
		sent *td.Message
		err  error
	)

	if cerr := ensureBroadcastChat(c, targetID); cerr != nil {
		logger.Errorf("Broadcast failed for %d: %v", targetID, cerr)
		return cerr
	}

	try := func() (*td.Message, error) {
		if m.ReplyToMessageID() > 0 {
			msgs, ferr := c.ForwardMessages(
				targetID,
				m.ChatID(),
				[]int64{m.ReplyToMessageID()},
				&td.ForwardMessagesOpts{SendCopy: flags.Copy},
			)
			if ferr != nil {
				return nil, ferr
			}
			if msgs == nil || len(msgs.Messages) == 0 || msgs.Messages[0].Id == 0 {
				return nil, fmt.Errorf("forward returned no message")
			}
			return &msgs.Messages[0], nil
		}
		return c.SendTextMessage(targetID, content, nil)
	}

	const maxAttempts = 3
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		sent, err = try()
		if err == nil {
			break
		}
		wait := getFloodWait(err)
		if wait <= 0 || attempt == maxAttempts {
			break
		}
		logger.Warnf("Broadcast flood wait %ds for %d (attempt %d)", wait, targetID, attempt)
		select {
		case <-ctx.Done():
			return context.Canceled
		case <-time.After(time.Duration(wait) * time.Second):
		}
	}

	if err != nil {
		if !isBroadcastSkipError(err) {
			logger.Errorf("Broadcast failed for %d: %v", targetID, err)
		}
		return err
	}

	if sent != nil && (flags.Pin || flags.PinLoud) {
		if perr := c.PinChatMessage(
			targetID,
			sent.Id,
			&td.PinChatMessageOpts{DisableNotification: !flags.PinLoud},
		); perr != nil {
			logger.Errorf("Pin failed for %d: %v", targetID, perr)
		}
	}
	return nil
}

func ensureBroadcastChat(c *td.Client, id int64) error {
	if _, err := c.GetChat(id); err == nil {
		return nil
	} else if id <= 0 {
		return err
	}
	_, err := c.CreatePrivateChat(id, nil)
	return err
}

func isBroadcastSkipError(err error) bool {
	msg := strings.ToLower(err.Error())
	for _, s := range []string{
		"user_is_blocked",
		"chat_write_forbidden",
		"user_is_deactivated",
		"blocked by the user",
		"have no write access",
		"forward returned no message",
		"user is deactivated",
		"chat not found",
		"bot was kicked",
		"bot is not a member",
		"forbidden",
	} {
		if strings.Contains(msg, s) {
			return true
		}
	}
	return false
}

func broadcastReason(err error) string {
	r := strings.TrimSpace(err.Error())
	if len(r) > 70 {
		r = r[:70]
	}
	return r
}

func (bm *broadcastManager) wait(ctx context.Context, sent int, delay float64) bool {
	d := time.Duration(delay * float64(time.Second))
	if sent%30 == 0 {
		d = 7500 * time.Millisecond
	}
	select {
	case <-ctx.Done():
		return false
	case <-time.After(d):
		return true
	}
}

func recordTarget(t broadcastTarget, err error, stats *BroadcastStats) {
	stats.mu.Lock()
	defer stats.mu.Unlock()

	if err != nil {
		if t.isUser {
			stats.FailedUsers = append(stats.FailedUsers, t.id)
		} else {
			stats.FailedChats = append(stats.FailedChats, t.id)
		}
		fmt.Fprintf(&stats.Errors, "[%d] - [%v]\n", t.id, err)
		if stats.Reasons == nil {
			stats.Reasons = make(map[string]int)
		}
		stats.Reasons[broadcastReason(err)]++
		return
	}

	if t.isUser {
		stats.DoneUsers++
	} else {
		stats.DoneChats++
	}
}

func (bm *broadcastManager) updateProgress(
	ctx context.Context,
	c *td.Client,
	progressMsg *td.Message,
	stats *BroadcastStats,
) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			stats.mu.Lock()
			if stats.Finished {
				stats.mu.Unlock()
				return
			}
			text := formatBroadcastProgress(stats, false, progressMsg.ChatID())
			stats.mu.Unlock()

			select {
			case <-ctx.Done():
				return
			default:
			}

			_, _ = progressMsg.EditText(c, text, &td.EditTextMessageOpts{
				ReplyMarkup: core.GetBroadcastCancelKeyboard(progressMsg.ChatID()),
			})
		}
	}
}

func (bm *broadcastManager) finalize(
	c *td.Client,
	progressMsg *td.Message,
	stats *BroadcastStats,
) {
	stats.mu.Lock()
	stats.Finished = true
	text := formatBroadcastProgress(stats, true, progressMsg.ChatID())
	stats.mu.Unlock()

	_, _ = progressMsg.EditText(c, text, nil)
}

func formatBroadcastProgress(
	stats *BroadcastStats,
	final bool,
	chatID int64,
) string {
	var sb strings.Builder

	if !final {
		sb.WriteString(F(chatID, "broadcast_progress_header") + "\n\n")
	} else if stats.Cancelled {
		sb.WriteString(F(chatID, "broadcast_cancel_done") + "\n\n")
	}

	sb.WriteString(broadcastProgressLine(chatID, "broadcast_total_chats",
		stats.DoneChats, stats.TotalChats) + "\n")
	sb.WriteString(broadcastProgressLine(chatID, "broadcast_total_users",
		stats.DoneUsers, stats.TotalUsers) + "\n\n")

	if len(stats.FailedChats) > 0 {
		sb.WriteString(F(chatID, "broadcast_failed_chats", locales.Arg{
			"count": len(stats.FailedChats),
		}) + "\n")
	}
	if len(stats.FailedUsers) > 0 {
		sb.WriteString(F(chatID, "broadcast_failed_users", locales.Arg{
			"count": len(stats.FailedUsers),
		}) + "\n")
	}
	if final && len(stats.Reasons) > 0 {
		reasons := make([]string, 0, len(stats.Reasons))
		for r := range stats.Reasons {
			reasons = append(reasons, r)
		}
		sort.Slice(reasons, func(i, j int) bool {
			return stats.Reasons[reasons[i]] > stats.Reasons[reasons[j]]
		})
		if len(reasons) > 5 {
			reasons = reasons[:5]
		}
		for _, r := range reasons {
			sb.WriteString(fmt.Sprintf("• %s — %d\n", html.EscapeString(r), stats.Reasons[r]))
		}
	}
	if len(stats.FailedChats) > 0 || len(stats.FailedUsers) > 0 {
		sb.WriteString("\n")
	}

	elapsed := time.Since(stats.StartTime)
	totalDone := stats.DoneChats + stats.DoneUsers
	totalTargets := stats.TotalChats + stats.TotalUsers

	avgSpeed := 0.0
	if elapsed.Seconds() > 0 && totalDone > 0 {
		avgSpeed = float64(totalDone) / elapsed.Seconds()
	}

	sb.WriteString(F(chatID, "broadcast_delay", locales.Arg{
		"delay": fmt.Sprintf("%.1f", stats.Delay),
	}) + "\n")
	sb.WriteString(F(chatID, "broadcast_elapsed", locales.Arg{
		"elapsed": utils.FormatDuration(int(elapsed.Seconds())),
	}) + "\n")

	if !final && avgSpeed > 0 && totalDone < totalTargets {
		eta := time.Duration(float64(totalTargets-totalDone) / avgSpeed * float64(time.Second))
		sb.WriteString("\n" + F(chatID, "broadcast_eta", locales.Arg{
			"eta": utils.FormatDuration(int(eta.Seconds())),
		}))
	}

	if final {
		totalSent := totalDone
		totalFailed := len(stats.FailedChats) + len(stats.FailedUsers)

		successRate := 0.0
		if totalTargets > 0 {
			successRate = float64(totalSent-totalFailed) / float64(totalTargets) * 100
		}

		sb.WriteString("\n\n" + F(chatID, "broadcast_success_rate", locales.Arg{
			"rate":  fmt.Sprintf("%.1f", successRate),
			"sent":  totalSent - totalFailed,
			"total": totalTargets,
		}))
	}

	return sb.String()
}

func broadcastProgressLine(chatID int64, key string, done, total int) string {
	progress := 0.0
	if total > 0 {
		progress = float64(done) / float64(total) * 100
	}
	return F(chatID, key, locales.Arg{
		"done":     done,
		"total":    total,
		"progress": fmt.Sprintf("%.1f", progress),
	})
}

func handleBroadcastCancel(c *td.Client, m *td.Message) error {
	if !bManager.isActive() {
		_, err := m.ReplyText(c, F(m.ChatID(), "broadcast_not_running"), nil)
		return err
	}
	bManager.stop()
	_, err := m.ReplyText(c, F(m.ChatID(), "broadcast_cancel_success"), nil)
	return err
}

func broadcastCancelCB(c *td.Client, cb *td.UpdateNewCallbackQuery) error {
	if cb.SenderUserId != config.OwnerID {
		cb.Answer(c, 0, true, F(cb.ChatId, "broadcast_cancel_owner_only"), "")
		return nil
	}
	if !bManager.isActive() {
		cb.Answer(c, 0, true, F(cb.ChatId, "broadcast_cancel_none_running"), "")
		return nil
	}
	bManager.stop()
	cb.Answer(c, 0, true, F(cb.ChatId, "broadcast_cancel_done"), "")
	cb.EditMessageText(c, F(cb.ChatId, "broadcast_cancel_done"), nil)
	return nil
}
