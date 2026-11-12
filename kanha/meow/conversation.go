package gotdbot

import (
	"time"
)

// WaitMessageOpts holds optional parameters for Ask.
type WaitMessageOpts struct {
	Filter             func(*Message) bool
	CancellationFilter func(*Message) bool
	Timeout            time.Duration
}

// Ask waits for a new message in the specified chat.
func (c *Client) Ask(chatId int64, opts *WaitMessageOpts) (*Message, error) {
	if opts == nil {
		opts = &WaitMessageOpts{Timeout: 1 * time.Minute}
	}

	filter := opts.Filter
	cancellationFilter := opts.CancellationFilter
	timeout := opts.Timeout

	msgFilter := func(client *Client, update TlObject) bool {
		u, ok := update.(*UpdateNewMessage)
		if !ok {
			return false
		}

		msg := u.Message
		if msg.ChatId != chatId {
			return false
		}

		if cancellationFilter != nil && cancellationFilter(msg) {
			return true
		}

		if filter != nil && !filter(msg) {
			return false
		}
		return true
	}

	u, err := c.WaitForChat(chatId, msgFilter, timeout)
	if err != nil {
		return nil, err
	}

	msg := u.(*UpdateNewMessage).Message
	if cancellationFilter != nil && cancellationFilter(msg) {
		return nil, ConversationCancelled
	}

	return msg, nil
}
