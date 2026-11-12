package message

import (
	"regexp"

	"github.com/Kanha/Meow"
	"github.com/Kanha/Meow/filters"
)

// Prefix checks if the message text starts with the given prefix.
func Prefix(prefix string) filters.Message {
	return func(msg *gotdbot.Message) bool {
		return msg.StartsWith(prefix)
	}
}

// Suffix checks if the message text ends with the given suffix.
func Suffix(suffix string) filters.Message {
	return func(msg *gotdbot.Message) bool {
		return msg.EndsWith(suffix)
	}
}

// Equal checks if the message text equals the given match string.
func Equal(match string) filters.Message {
	return func(msg *gotdbot.Message) bool {
		return msg.GetText() == match
	}
}

// Regex checks if the message text matches the given regex pattern.
func Regex(pattern string) filters.Message {
	reg, err := regexp.Compile(pattern)
	if err != nil {
		return func(msg *gotdbot.Message) bool {
			return false
		}
	}
	return func(msg *gotdbot.Message) bool {
		return reg.MatchString(msg.GetText())
	}
}

// Private filters messages sent in private chats.
func Private(msg *gotdbot.Message) bool {
	return msg.IsPrivate()
}

// Group filters messages sent in group or supergroup chats.
func Group(msg *gotdbot.Message) bool {
	return msg.IsGroup() || msg.IsSupergroupOrChannel()
}

// Channel filters messages sent in channel chats.
func Channel(msg *gotdbot.Message) bool {
	return msg.IsChannel()
}

// Incoming filters incoming messages.
func Incoming(msg *gotdbot.Message) bool {
	return !msg.IsOutgoingMessage()
}

// Outgoing filters outgoing messages.
func Outgoing(msg *gotdbot.Message) bool {
	return msg.IsOutgoingMessage()
}

// Edited filters edited messages.
func Edited(msg *gotdbot.Message) bool {
	return msg.IsEditedMessage()
}

// Command filters messages that are commands.
func Command(msg *gotdbot.Message) bool {
	return msg.IsCommand()
}

// FromUserID checks if the message sender's user ID matches the given ID.
func FromUserID(id int64) filters.Message {
	return func(msg *gotdbot.Message) bool {
		return msg.SenderID() == id
	}
}

// ChatID checks if the message chat ID matches the given ID.
func ChatID(id int64) filters.Message {
	return func(msg *gotdbot.Message) bool {
		return msg.ChatID() == id
	}
}

// And combines multiple filters, all must pass.
func And(fs ...filters.Message) filters.Message {
	return func(msg *gotdbot.Message) bool {
		for _, f := range fs {
			if !f(msg) {
				return false
			}
		}
		return true
	}
}

// Or combines multiple filters, at least one must pass.
func Or(fs ...filters.Message) filters.Message {
	return func(msg *gotdbot.Message) bool {
		for _, f := range fs {
			if f(msg) {
				return true
			}
		}
		return false
	}
}

// Not negates a filter.
func Not(f filters.Message) filters.Message {
	return func(msg *gotdbot.Message) bool {
		return !f(msg)
	}
}
