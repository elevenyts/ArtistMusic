package gotdbot

import (
	"errors"
)

var (
	// EndGroups stops processing all remaining groups.
	EndGroups = errors.New("group iteration ended")
	// ContinueGroups skips remaining handlers in the current group and continues with the next group.
	ContinueGroups = errors.New("group iteration continued")
	// ContinueHandlers continues processing the remaining handlers in the same group.
	ContinueHandlers = errors.New("handler iteration continued")

	ConversationCancelled = errors.New("conversation cancelled")
	ConversationTimeout   = errors.New("conversation wait timeout")

	SendTimeout         = errors.New("TDLib send timeout")
	WaitPremiumPurchase = errors.New("account requires Telegram Premium")

	// ErrNoFormattedText is returned when a message content does not contain text or caption.
	ErrNoFormattedText = errors.New("message does not contain formatted text or caption")
)
