package gotdbot

// CallbackData returns the callback data payload as bytes.
func (t *UpdateNewCallbackQuery) CallbackData() []byte {
	if t.Payload == nil {
		return nil
	}
	if p, ok := t.Payload.(*CallbackQueryPayloadData); ok {
		return p.Data
	}
	return nil
}

// DataString returns the callback data payload as a string.
func (t *UpdateNewCallbackQuery) DataString() string {
	if t.CallbackData() != nil {
		return string(t.CallbackData())
	}
	return ""
}

// CallbackDataWithPassword returns the callback data payload as bytes, along with the password if it exists.
func (t *UpdateNewCallbackQuery) CallbackDataWithPassword() ([]byte, string) {
	if t.Payload == nil {
		return nil, ""
	}
	if p, ok := t.Payload.(*CallbackQueryPayloadDataWithPassword); ok {
		return p.Data, p.Password
	}
	return nil, ""
}

// GameShortName returns the short name of the game associated with the callback query.
func (t *UpdateNewCallbackQuery) GameShortName() string {
	if t.Payload == nil {
		return ""
	}
	if p, ok := t.Payload.(*CallbackQueryPayloadGame); ok {
		return p.GameShortName
	}
	return ""
}

// IsPrivate checks if the callback query originated from a private chat.
func (t *UpdateNewCallbackQuery) IsPrivate() bool {
	return t.ChatId > 0
}

// GetMessage returns the message that originated the query.
func (t *UpdateNewCallbackQuery) GetMessage(c *Client) (*Message, error) {
	if t.MessageId == 0 {
		return nil, nil
	}
	return c.GetMessage(t.ChatId, t.MessageId)
}

// Answer sends an answer to the callback query.
func (t *UpdateNewCallbackQuery) Answer(c *Client, cacheTime int32, showAlert bool, text string, url string) error {
	err := c.AnswerCallbackQuery(cacheTime, t.Id, text, url, &AnswerCallbackQueryOpts{ShowAlert: showAlert})
	return err
}

// EditMessageText edits the text of the message associated with the callback query.
func (t *UpdateNewCallbackQuery) EditMessageText(c *Client, text string, opts *EditTextMessageOpts) (*Message, error) {
	return c.EditTextMessage(t.ChatId, t.MessageId, text, opts)
}

// EditMessageCaption edits the caption of the message associated with the callback query.
func (t *UpdateNewCallbackQuery) EditMessageCaption(c *Client, caption string, opts *EditCaptionOpts) (*Message, error) {
	return c.EditCaption(t.ChatId, t.MessageId, caption, opts)
}

// EditMessageReplyMarkup edits the reply markup of the message associated with the callback query.
func (t *UpdateNewCallbackQuery) EditMessageReplyMarkup(c *Client, replyMarkup ReplyMarkup) (*Message, error) {
	return c.EditMessageReplyMarkup(t.ChatId, t.MessageId, &EditMessageReplyMarkupOpts{ReplyMarkup: replyMarkup})
}
