package gotdbot

import (
	"fmt"
	"html"
	"strings"
)

// GetFormattedText returns a FormattedText object from the given text, entities and parse mode.
func (c *Client) GetFormattedText(text string, entities []TextEntity, parseMode string) (*FormattedText, error) {
	if len(entities) > 0 {
		return &FormattedText{
			Text:     text,
			Entities: entities,
		}, nil
	}

	if parseMode == "" {
		parseMode = c.config.ParseMode
	}

	return c.ParseText(text, parseMode)
}

// EscapeHTML escapes HTML characters in the given text.
func EscapeHTML(text string) string {
	return html.EscapeString(text)
}

// EscapeMarkdown escapes Markdown characters in the given text.
func EscapeMarkdown(text string, version int) string {
	var chars string
	if version == 1 {
		chars = "_*`[\\"
	} else {
		chars = "_*[]()~`>#+-=|{}.!\\"
	}
	var b strings.Builder
	for _, c := range text {
		if strings.ContainsRune(chars, c) {
			b.WriteRune('\\')
		}
		b.WriteRune(c)
	}
	return b.String()
}

// Mention returns a text mention for the given user ID.
func Mention(text string, userId int64, isHtml bool, escape bool) string {
	if escape {
		if isHtml {
			text = EscapeHTML(text)
		} else {
			text = EscapeMarkdown(text, 2)
		}
	}
	if isHtml {
		return fmt.Sprintf("<a href=\"tg://user?id=%d\">%s</a>", userId, text)
	}
	return fmt.Sprintf("[%s](tg://user?id=%d)", text, userId)
}

// sendMessageWithContent is a helper function to send a message with content
func (c *Client) sendMessageWithContent(
	chatId int64,
	content InputMessageContent,
	options *MessageSendOptions,
	topicId MessageTopic,
	quote *InputTextQuote,
	replyTo InputMessageReplyTo,
	replyToMessageId int64,
	replyMarkup ReplyMarkup,
	callbackQueryId int64,
	receiverUserId int64,
	replaceCallbackQueryMessage bool,
) (*Message, error) {
	if replyToMessageId > 0 {
		replyTo = &InputMessageReplyToMessage{
			MessageId: replyToMessageId,
			Quote:     quote,
		}
	}

	if c.config.LoadMessagesBeforeReply && replyToMessageId > 0 {
		_, _ = c.GetMessage(chatId, replyToMessageId)
	}

	if receiverUserId != 0 || callbackQueryId > 0 {
		var sendingId int32
		var onlyPreview bool

		var protectContent bool

		if options != nil {
			sendingId = options.SendingId
			onlyPreview = options.OnlyPreview
			protectContent = options.ProtectContent
		}

		return c.SendEphemeralMessage(callbackQueryId, chatId, content, receiverUserId, sendingId, &SendEphemeralMessageOpts{
			OnlyPreview:                 onlyPreview,
			ProtectContent:              protectContent,
			ReplaceCallbackQueryMessage: replaceCallbackQueryMessage,
			ReplyMarkup:                 replyMarkup,
			ReplyTo:                     replyTo,
			TopicId:                     topicId,
		})
	}

	return c.SendMessage(chatId, content, &SendMessageOpts{
		TopicId:     topicId,
		ReplyTo:     replyTo,
		Options:     options,
		ReplyMarkup: replyMarkup,
	})
}

// SendTextMessageOpts contains optional parameters for SendTextMessage
type SendTextMessageOpts struct {
	ParseMode                         string
	Entities                          []TextEntity
	DisableWebPagePreview             bool
	Url                               string
	ForceSmallMedia                   bool
	ForceLargeMedia                   bool
	ShowAboveText                     bool
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	ClearDraft                        bool
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendTextMessage sends a text message to chat
func (c *Client) SendTextMessage(chatId int64, text string, opts *SendTextMessageOpts) (*Message, error) {
	if opts == nil {
		opts = &SendTextMessageOpts{}
	}

	formattedText, err := c.GetFormattedText(text, opts.Entities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	linkPreviewOptions := &LinkPreviewOptions{
		IsDisabled:      opts.DisableWebPagePreview,
		Url:             opts.Url,
		ForceSmallMedia: opts.ForceSmallMedia,
		ForceLargeMedia: opts.ForceLargeMedia,
		ShowAboveText:   opts.ShowAboveText,
	}

	content := &InputMessageText{
		Text:               formattedText,
		LinkPreviewOptions: linkPreviewOptions,
		ClearDraft:         opts.ClearDraft,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendPhotoOpts contains optional parameters for SendPhoto
type SendPhotoOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	AddedStickerFileIds               []int32
	Width                             int32
	Height                            int32
	SelfDestructType                  MessageSelfDestructType
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	HasSpoiler                        bool
	ShowCaptionAboveMedia             bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	Thumbnail                         *InputThumbnail
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendPhoto sends a photo to chat
func (c *Client) SendPhoto(chatId int64, photo InputFile, opts *SendPhotoOpts) (*Message, error) {
	if opts == nil {
		opts = &SendPhotoOpts{}
	}

	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	content := &InputMessagePhoto{
		Photo: &InputPhoto{
			Photo:               photo,
			Thumbnail:           opts.Thumbnail,
			AddedStickerFileIds: opts.AddedStickerFileIds,
			Width:               opts.Width,
			Height:              opts.Height,
		},
		Caption:               caption,
		SelfDestructType:      opts.SelfDestructType,
		HasSpoiler:            opts.HasSpoiler,
		ShowCaptionAboveMedia: opts.ShowCaptionAboveMedia,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendVideoOpts contains optional parameters for SendVideo
type SendVideoOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	AddedStickerFileIds               []int32
	SupportsStreaming                 bool
	Duration                          int32
	Width                             int32
	Height                            int32
	SelfDestructType                  MessageSelfDestructType
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	HasSpoiler                        bool
	ShowCaptionAboveMedia             bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	Thumbnail                         *InputThumbnail
	EffectId                          int64
	StartTimestamp                    int32
	Cover                             InputFile
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendVideo sends a video to chat
func (c *Client) SendVideo(chatId int64, video InputFile, opts *SendVideoOpts) (*Message, error) {
	if opts == nil {
		opts = &SendVideoOpts{}
	}

	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	content := &InputMessageVideo{
		Video: &InputVideo{
			Video:               video,
			Thumbnail:           opts.Thumbnail,
			AddedStickerFileIds: opts.AddedStickerFileIds,
			Duration:            opts.Duration,
			Width:               opts.Width,
			Height:              opts.Height,
			SupportsStreaming:   opts.SupportsStreaming,
			StartTimestamp:      opts.StartTimestamp,
			Cover:               opts.Cover,
		},
		Caption:               caption,
		SelfDestructType:      opts.SelfDestructType,
		HasSpoiler:            opts.HasSpoiler,
		ShowCaptionAboveMedia: opts.ShowCaptionAboveMedia,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendAnimationOpts contains optional parameters for SendAnimation
type SendAnimationOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	AddedStickerFileIds               []int32
	Duration                          int32
	Width                             int32
	Height                            int32
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	HasSpoiler                        bool
	ShowCaptionAboveMedia             bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	Thumbnail                         *InputThumbnail
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendAnimation sends an animation to chat
func (c *Client) SendAnimation(chatId int64, animation InputFile, opts *SendAnimationOpts) (*Message, error) {
	if opts == nil {
		opts = &SendAnimationOpts{}
	}

	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	content := &InputMessageAnimation{
		Animation: &InputAnimation{
			Animation:           animation,
			Thumbnail:           opts.Thumbnail,
			AddedStickerFileIds: opts.AddedStickerFileIds,
			Duration:            opts.Duration,
			Width:               opts.Width,
			Height:              opts.Height,
		},
		Caption:               caption,
		HasSpoiler:            opts.HasSpoiler,
		ShowCaptionAboveMedia: opts.ShowCaptionAboveMedia,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendAudioOpts contains optional parameters for SendAudio
type SendAudioOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	Title                             string
	Performer                         string
	Duration                          int32
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	AlbumCoverThumbnail               *InputThumbnail
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendAudio sends an audio to chat
func (c *Client) SendAudio(chatId int64, audio InputFile, opts *SendAudioOpts) (*Message, error) {
	if opts == nil {
		opts = &SendAudioOpts{}
	}

	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	content := &InputMessageAudio{
		Audio: &InputAudio{
			Audio:               audio,
			AlbumCoverThumbnail: opts.AlbumCoverThumbnail,
			Title:               opts.Title,
			Performer:           opts.Performer,
			Duration:            opts.Duration,
		},
		Caption: caption,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendDocumentOpts contains optional parameters for SendDocument
type SendDocumentOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	DisableContentTypeDetection       bool
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	Thumbnail                         *InputThumbnail
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendDocument sends a document to chat
func (c *Client) SendDocument(chatId int64, document InputFile, opts *SendDocumentOpts) (*Message, error) {
	if opts == nil {
		opts = &SendDocumentOpts{}
	}

	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	content := &InputMessageDocument{
		Document: &InputDocument{
			Document:                    document,
			Thumbnail:                   opts.Thumbnail,
			DisableContentTypeDetection: opts.DisableContentTypeDetection,
		},
		Caption: caption,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendVoiceOpts contains optional parameters for SendVoice
type SendVoiceOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	Duration                          int32
	Waveform                          []byte
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	SelfDestructType                  MessageSelfDestructType
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendVoice sends a voice note to chat
func (c *Client) SendVoice(chatId int64, voice InputFile, opts *SendVoiceOpts) (*Message, error) {
	if opts == nil {
		opts = &SendVoiceOpts{}
	}

	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	content := &InputMessageVoiceNote{
		VoiceNote: &InputVoiceNote{
			VoiceNote: voice,
			Waveform:  opts.Waveform,
			Duration:  opts.Duration,
		},
		Caption:          caption,
		SelfDestructType: opts.SelfDestructType,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendVideoNoteOpts contains optional parameters for SendVideoNote
type SendVideoNoteOpts struct {
	Duration                          int32
	Length                            int32
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	Thumbnail                         *InputThumbnail
	EffectId                          int64
	SelfDestructType                  MessageSelfDestructType
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendVideoNote sends a video note to chat
func (c *Client) SendVideoNote(chatId int64, videoNote InputFile, opts *SendVideoNoteOpts) (*Message, error) {
	if opts == nil {
		opts = &SendVideoNoteOpts{}
	}

	content := &InputMessageVideoNote{
		VideoNote: &InputVideoNote{
			VideoNote: videoNote,
			Thumbnail: opts.Thumbnail,
			Duration:  opts.Duration,
			Length:    opts.Length,
		},
		SelfDestructType: opts.SelfDestructType,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendStickerOpts contains optional parameters for SendSticker
type SendStickerOpts struct {
	Emoji                             string
	Width                             int32
	Height                            int32
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	Thumbnail                         *InputThumbnail
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendSticker sends a sticker to chat
func (c *Client) SendSticker(chatId int64, sticker InputFile, opts *SendStickerOpts) (*Message, error) {
	if opts == nil {
		opts = &SendStickerOpts{}
	}

	content := &InputMessageSticker{
		Sticker: &InputSticker{
			Sticker:   sticker,
			Thumbnail: opts.Thumbnail,
			Width:     opts.Width,
			Height:    opts.Height,
		},
		Emoji: opts.Emoji,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendCopyOpts contains optional parameters for SendCopy
type SendCopyOpts struct {
	InGameShare                       bool
	ReplaceCaption                    bool
	NewCaption                        string
	NewCaptionEntities                []TextEntity
	ParseMode                         string
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyMarkup                       ReplyMarkup
	ReplyToMessageID                  int64
	EffectId                          int64
	NewShowCaptionAboveMedia          bool
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendCopy copies a message to chat
func (c *Client) SendCopy(chatId int64, fromChatId int64, messageId int64, opts *SendCopyOpts) (*Message, error) {
	if opts == nil {
		opts = &SendCopyOpts{}
	}

	caption, err := c.GetFormattedText(opts.NewCaption, opts.NewCaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}
	content := &InputMessageForwarded{
		FromChatId:  fromChatId,
		MessageId:   messageId,
		InGameShare: opts.InGameShare,
		CopyOptions: &MessageCopyOptions{
			SendCopy:                 true,
			ReplaceCaption:           opts.ReplaceCaption,
			NewCaption:               caption,
			NewShowCaptionAboveMedia: opts.NewShowCaptionAboveMedia,
		},
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// EditEphemeralMessageTextOpts contains optional parameters for EditEphemeralMessageText
type EditEphemeralMessageTextOpts struct {
	ParseMode             string
	Entities              []TextEntity
	DisableWebPagePreview bool
	Url                   string
	ForceSmallMedia       bool
	ForceLargeMedia       bool
	ShowAboveText         bool
	ReplyMarkup           ReplyMarkup
}

// EditEphemeralMessageText edits the text of an ephemeral message
func (c *Client) EditEphemeralMessageText(chatId int64, ephemeralMessageId int32, receiverUserId int64, text string, opts *EditEphemeralMessageTextOpts) error {
	if opts == nil {
		opts = &EditEphemeralMessageTextOpts{}
	}

	formattedText, err := c.GetFormattedText(text, opts.Entities, opts.ParseMode)
	if err != nil {
		return err
	}

	linkPreviewOptions := &LinkPreviewOptions{
		IsDisabled:      opts.DisableWebPagePreview,
		Url:             opts.Url,
		ForceSmallMedia: opts.ForceSmallMedia,
		ForceLargeMedia: opts.ForceLargeMedia,
		ShowAboveText:   opts.ShowAboveText,
	}

	content := &InputMessageText{
		Text:               formattedText,
		LinkPreviewOptions: linkPreviewOptions,
	}

	return c.EditEphemeralMessage(chatId, ephemeralMessageId, receiverUserId, &EditEphemeralMessageOpts{
		InputMessageContent: content,
		ReplyMarkup:         opts.ReplyMarkup,
	})
}

// EditEphemeralMessageMediaOpts contains optional parameters for EditEphemeralMessageMedia
type EditEphemeralMessageMediaOpts struct {
	ReplyMarkup ReplyMarkup
}

// EditEphemeralMessageMedia edits the media content of an ephemeral message
func (c *Client) EditEphemeralMessageMedia(chatId int64, ephemeralMessageId int32, receiverUserId int64, content InputMessageContent, opts *EditEphemeralMessageMediaOpts) error {
	if opts == nil {
		opts = &EditEphemeralMessageMediaOpts{}
	}

	return c.EditEphemeralMessage(chatId, ephemeralMessageId, receiverUserId, &EditEphemeralMessageOpts{
		InputMessageContent: content,
		ReplyMarkup:         opts.ReplyMarkup,
	})
}

// EditEphemeralMessageReplyMarkup edits the reply markup of an ephemeral message
func (c *Client) EditEphemeralMessageReplyMarkup(chatId int64, ephemeralMessageId int32, receiverUserId int64, replyMarkup ReplyMarkup) error {
	return c.EditEphemeralMessage(chatId, ephemeralMessageId, receiverUserId, &EditEphemeralMessageOpts{
		ReplyMarkup: replyMarkup,
	})
}

// ForwardMessageOpts contains optional parameters for ForwardMessage
type ForwardMessageOpts struct {
	InGameShare                       bool
	DisableNotification               bool
	EffectId                          int64
	ReplaceVideoStartTimestamp        bool
	NewVideoStartTimestamp            int32
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	ProtectContent                    bool
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	UpdateOrderOfInstalledStickerSets bool
}

// ForwardMessage forwards a message to chat
func (c *Client) ForwardMessage(chatId int64, fromChatId int64, messageId int64, opts *ForwardMessageOpts) (*Message, error) {
	if opts == nil {
		opts = &ForwardMessageOpts{}
	}

	content := &InputMessageForwarded{
		FromChatId:                 fromChatId,
		MessageId:                  messageId,
		InGameShare:                opts.InGameShare,
		ReplaceVideoStartTimestamp: opts.ReplaceVideoStartTimestamp,
		NewVideoStartTimestamp:     opts.NewVideoStartTimestamp,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		ProtectContent:                    opts.ProtectContent,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, nil, nil, nil, 0, nil, 0, 0, false)
}

// EditTextMessageOpts contains optional parameters for EditTextMessage
type EditTextMessageOpts struct {
	ParseMode             string
	Entities              []TextEntity
	DisableWebPagePreview bool
	Url                   string
	ForceSmallMedia       bool
	ForceLargeMedia       bool
	ShowAboveText         bool
	ReplyMarkup           ReplyMarkup
}

// EditTextMessage edits a text message
func (c *Client) EditTextMessage(chatId int64, messageId int64, text string, opts *EditTextMessageOpts) (*Message, error) {
	if opts == nil {
		opts = &EditTextMessageOpts{}
	}

	if !*c.config.UseMessageDatabase {
		if _, err := c.GetMessage(chatId, messageId); err != nil {
			return nil, err
		}
	}

	formattedText, err := c.GetFormattedText(text, opts.Entities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	linkPreviewOptions := &LinkPreviewOptions{
		IsDisabled:      opts.DisableWebPagePreview,
		Url:             opts.Url,
		ForceSmallMedia: opts.ForceSmallMedia,
		ForceLargeMedia: opts.ForceLargeMedia,
		ShowAboveText:   opts.ShowAboveText,
	}

	content := &InputMessageText{
		Text:               formattedText,
		LinkPreviewOptions: linkPreviewOptions,
	}

	return c.EditMessageText(chatId, content, messageId, &EditMessageTextOpts{
		ReplyMarkup: opts.ReplyMarkup,
	})
}

// EditCaptionOpts contains optional parameters for EditCaption
type EditCaptionOpts struct {
	ParseMode             string
	Entities              []TextEntity
	ShowCaptionAboveMedia bool
	ReplyMarkup           ReplyMarkup
}

// EditCaption edits the caption of a message
func (c *Client) EditCaption(chatId int64, messageId int64, caption string, opts *EditCaptionOpts) (*Message, error) {
	if opts == nil {
		opts = &EditCaptionOpts{}
	}

	if !*c.config.UseMessageDatabase {
		if _, err := c.GetMessage(chatId, messageId); err != nil {
			return nil, err
		}
	}

	formattedText, err := c.GetFormattedText(caption, opts.Entities, opts.ParseMode)
	if err != nil {
		return nil, err
	}

	return c.EditMessageCaption(chatId, messageId, &EditMessageCaptionOpts{
		Caption:               formattedText,
		ReplyMarkup:           opts.ReplyMarkup,
		ShowCaptionAboveMedia: opts.ShowCaptionAboveMedia,
	})
}

// GetSupergroupId returns the supergroup ID from a chat ID
func (c *Client) GetSupergroupId(chatId int64) (int64, error) {
	chat, err := c.GetChat(chatId)
	if err != nil {
		return 0, err
	}

	if chat.Type == nil {
		return 0, nil
	}

	if ct, ok := chat.Type.(*ChatTypeSupergroup); ok {
		return ct.SupergroupId, nil
	}

	return 0, nil
}

// ParseText parses the text using the specified parse mode.
func (c *Client) ParseText(text string, parseMode string) (*FormattedText, error) {
	var mode TextParseMode

	switch strings.ToLower(parseMode) {
	case "markdown":
		mode = &TextParseModeMarkdown{Version: 1}
	case "markdownv2":
		mode = &TextParseModeMarkdown{Version: 2}
	case "html":
		mode = &TextParseModeHTML{}
	default:
		return &FormattedText{Text: text}, nil
	}

	return c.ParseTextEntities(mode, text)
}

// SendChecklistOpts contains optional parameters for SendChecklist
type SendChecklistOpts struct {
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendChecklist sends a checklist to chat
func (c *Client) SendChecklist(chatId int64, checklist *InputChecklist, opts *SendChecklistOpts) (*Message, error) {
	if opts == nil {
		opts = &SendChecklistOpts{}
	}
	content := &InputMessageChecklist{
		Checklist: checklist,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendContactOpts contains optional parameters for SendContact
type SendContactOpts struct {
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendContact sends a contact to chat
func (c *Client) SendContact(chatId int64, contact *Contact, opts *SendContactOpts) (*Message, error) {
	if opts == nil {
		opts = &SendContactOpts{}
	}
	content := &InputMessageContact{
		Contact: contact,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendDiceOpts contains optional parameters for SendDice
type SendDiceOpts struct {
	ClearDraft                        bool
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendDice sends a dice to chat
func (c *Client) SendDice(chatId int64, emoji string, opts *SendDiceOpts) (*Message, error) {
	if opts == nil {
		opts = &SendDiceOpts{}
	}
	content := &InputMessageDice{
		Emoji:      emoji,
		ClearDraft: opts.ClearDraft,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendGameOpts contains optional parameters for SendGame
type SendGameOpts struct {
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendGame sends a game to chat
func (c *Client) SendGame(chatId int64, botUserId int64, gameShortName string, opts *SendGameOpts) (*Message, error) {
	if opts == nil {
		opts = &SendGameOpts{}
	}
	content := &InputMessageGame{
		BotUserId:     botUserId,
		GameShortName: gameShortName,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendInvoiceOpts contains optional parameters for SendInvoice
type SendInvoiceOpts struct {
	PaidMedia                         *InputPaidMedia
	PaidMediaCaption                  string
	PaidMediaEntities                 []TextEntity
	ParseMode                         string
	PhotoHeight                       int32
	PhotoSize                         int32
	PhotoUrl                          string
	PhotoWidth                        int32
	ProviderData                      string
	ProviderToken                     string
	StartParameter                    string
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendInvoice sends an invoice to chat
func (c *Client) SendInvoice(chatId int64, invoice *Invoice, title string, description string, payload []byte, opts *SendInvoiceOpts) (*Message, error) {
	if opts == nil {
		opts = &SendInvoiceOpts{}
	}
	paidMediaCaption, err := c.GetFormattedText(opts.PaidMediaCaption, opts.PaidMediaEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}
	content := &InputMessageInvoice{
		Description:      description,
		Invoice:          invoice,
		PaidMedia:        opts.PaidMedia,
		PaidMediaCaption: paidMediaCaption,
		Payload:          payload,
		PhotoHeight:      opts.PhotoHeight,
		PhotoSize:        opts.PhotoSize,
		PhotoUrl:         opts.PhotoUrl,
		PhotoWidth:       opts.PhotoWidth,
		ProviderData:     opts.ProviderData,
		ProviderToken:    opts.ProviderToken,
		StartParameter:   opts.StartParameter,
		Title:            title,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendLocationOpts contains optional parameters for SendLocation
type SendLocationOpts struct {
	Heading                           int32
	LivePeriod                        int32
	ProximityAlertRadius              int32
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendLocation sends a location to chat
func (c *Client) SendLocation(chatId int64, location *Location, opts *SendLocationOpts) (*Message, error) {
	if opts == nil {
		opts = &SendLocationOpts{}
	}

	var content InputMessageContent
	if opts.LivePeriod > 0 {
		content = &InputMessageLiveLocation{
			Location: &LiveLocation{
				Location:             location,
				LivePeriod:           opts.LivePeriod,
				Heading:              opts.Heading,
				ProximityAlertRadius: opts.ProximityAlertRadius,
			},
		}
	} else {
		content = &InputMessageLocation{
			Location: location,
		}
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// SendPaidMediaOpts contains optional parameters for SendPaidMedia
type SendPaidMediaOpts struct {
	Caption                           string
	CaptionEntities                   []TextEntity
	ParseMode                         string
	Payload                           string
	ShowCaptionAboveMedia             bool
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendPaidMedia sends paid media to chat
func (c *Client) SendPaidMedia(chatId int64, starCount int64, paidMedia []InputPaidMedia, opts *SendPaidMediaOpts) (*Message, error) {
	if opts == nil {
		opts = &SendPaidMediaOpts{}
	}
	caption, err := c.GetFormattedText(opts.Caption, opts.CaptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}
	content := &InputMessagePaidMedia{
		Caption:               caption,
		PaidMedia:             paidMedia,
		Payload:               opts.Payload,
		ShowCaptionAboveMedia: opts.ShowCaptionAboveMedia,
		StarCount:             starCount,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendPollOpts contains optional parameters for SendPoll
type SendPollOpts struct {
	AllowsMultipleAnswers             bool
	AllowsRevoting                    bool
	CloseDate                         int32
	Description                       string
	DescriptionEntities               []TextEntity
	ParseMode                         string
	HideResultsUntilCloses            bool
	IsAnonymous                       bool
	IsClosed                          bool
	OpenPeriod                        int32
	QuestionEntities                  []TextEntity
	ShuffleOptions                    bool
	Type                              InputPollType
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	Media                             InputPollMedia
	MembersOnly                       bool
	CountryCodes                      []string
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendPoll sends a poll to chat
func (c *Client) SendPoll(chatId int64, question string, options []InputPollOption, opts *SendPollOpts) (*Message, error) {
	if opts == nil {
		opts = &SendPollOpts{}
	}
	formattedQuestion, err := c.GetFormattedText(question, opts.QuestionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}
	description, err := c.GetFormattedText(opts.Description, opts.DescriptionEntities, opts.ParseMode)
	if err != nil {
		return nil, err
	}
	content := &InputMessagePoll{
		AllowsMultipleAnswers:  opts.AllowsMultipleAnswers,
		AllowsRevoting:         opts.AllowsRevoting,
		CloseDate:              opts.CloseDate,
		Description:            description,
		HideResultsUntilCloses: opts.HideResultsUntilCloses,
		IsAnonymous:            opts.IsAnonymous,
		IsClosed:               opts.IsClosed,
		OpenPeriod:             opts.OpenPeriod,
		Options:                options,
		Question:               formattedQuestion,
		ShuffleOptions:         opts.ShuffleOptions,
		Type:                   opts.Type,
		Media:                  opts.Media,
		MembersOnly:            opts.MembersOnly,
		CountryCodes:           opts.CountryCodes,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendStakeDiceOpts contains optional parameters for SendStakeDice
type SendStakeDiceOpts struct {
	ClearDraft                        bool
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendStakeDice sends a stake dice to chat
func (c *Client) SendStakeDice(chatId int64, stakeGramAmount int64, stateHash string, opts *SendStakeDiceOpts) (*Message, error) {
	if opts == nil {
		opts = &SendStakeDiceOpts{}
	}
	content := &InputMessageStakeDice{
		ClearDraft:      opts.ClearDraft,
		StakeGramAmount: stakeGramAmount,
		StateHash:       stateHash,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendStoryOpts contains optional parameters for SendStory
type SendStoryOpts struct {
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
}

// SendStory sends a story to chat
func (c *Client) SendStory(chatId int64, storyPosterChatId int64, storyId int32, opts *SendStoryOpts) (*Message, error) {
	if opts == nil {
		opts = &SendStoryOpts{}
	}
	content := &InputMessageStory{
		StoryId:           storyId,
		StoryPosterChatId: storyPosterChatId,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}

// SendVenueOpts contains optional parameters for SendVenue
type SendVenueOpts struct {
	DisableNotification               bool
	ProtectContent                    bool
	AllowPaidBroadcast                bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
	EffectId                          int64
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	SuggestedPostInfo                 *InputSuggestedPostInfo
	UpdateOrderOfInstalledStickerSets bool
	CallbackQueryID                   int64
	ReceiverUserID                    int64
	ReplaceCallbackQueryMessage       bool
}

// SendVenue sends a venue to chat
func (c *Client) SendVenue(chatId int64, venue *Venue, opts *SendVenueOpts) (*Message, error) {
	if opts == nil {
		opts = &SendVenueOpts{}
	}
	content := &InputMessageVenue{
		Venue: venue,
	}
	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

// EditContent edits a message with the given content.
func (c *Client) EditContent(chatId int64, messageId int64, content InputMessageContent, replyMarkup ReplyMarkup) (*Message, error) {
	switch t := content.(type) {
	case *InputMessageText, *InputMessageRichMessage:
		return c.EditMessageText(chatId, content, messageId, &EditMessageTextOpts{
			ReplyMarkup: replyMarkup,
		})
	case *InputMessageAnimation, *InputMessageAudio, *InputMessageDocument, *InputMessagePhoto, *InputMessageVideo:
		return c.EditMessageMedia(chatId, content, messageId, &EditMessageMediaOpts{
			ReplyMarkup: replyMarkup,
		})
	case *InputMessageLiveLocation:
		return c.EditMessageLiveLocation(chatId, messageId, &EditMessageLiveLocationOpts{
			Location:    t.Location,
			ReplyMarkup: replyMarkup,
		})
	case *InputMessageChecklist:
		return c.EditMessageChecklist(chatId, t.Checklist, messageId, &EditMessageChecklistOpts{
			ReplyMarkup: replyMarkup,
		})
	default:
		return nil, fmt.Errorf("unsupported content type for editing: %T", content)
	}
}

// EditReplyMarkup edits the reply markup of a message.
func (c *Client) EditReplyMarkup(chatId int64, messageId int64, replyMarkup ReplyMarkup) (*Message, error) {
	return c.EditMessageReplyMarkup(chatId, messageId, &EditMessageReplyMarkupOpts{
		ReplyMarkup: replyMarkup,
	})
}

// SendContent sends a message with the given content.
func (c *Client) SendContent(chatId int64, content InputMessageContent, opts *SendMessageOpts) (*Message, error) {
	return c.SendMessage(chatId, content, opts)
}

// SendRichMessage sends a rich message to chat.
func (c *Client) SendRichMessage(chatId int64, richMessage *InputRichMessage, opts *SendTextMessageOpts) (*Message, error) {
	if opts == nil {
		opts = &SendTextMessageOpts{}
	}

	content := &InputMessageRichMessage{
		ClearDraft: opts.ClearDraft,
		Message:    richMessage,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		ProtectContent:                    opts.ProtectContent,
		AllowPaidBroadcast:                opts.AllowPaidBroadcast,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		SuggestedPostInfo:                 opts.SuggestedPostInfo,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, opts.CallbackQueryID, opts.ReceiverUserID, opts.ReplaceCallbackQueryMessage)
}

type SendForwardedOpts struct {
	InGameShare                       bool
	DisableNotification               bool
	EffectId                          int64
	ReplaceVideoStartTimestamp        bool
	NewVideoStartTimestamp            int32
	FromBackground                    bool
	OnlyPreview                       bool
	PaidMessageStarCount              int64
	ProtectContent                    bool
	SchedulingState                   MessageSchedulingState
	SendingId                         int32
	UpdateOrderOfInstalledStickerSets bool
	TopicId                           MessageTopic
	Quote                             *InputTextQuote
	ReplyTo                           InputMessageReplyTo
	ReplyToMessageID                  int64
	ReplyMarkup                       ReplyMarkup
}

// SendForwarded sends a forwarded message to chat.
func (c *Client) SendForwarded(chatId int64, fromChatId int64, messageId int64, inGameShare bool, opts *SendForwardedOpts) (*Message, error) {
	if opts == nil {
		opts = &SendForwardedOpts{}
	}

	content := &InputMessageForwarded{
		FromChatId:                 fromChatId,
		MessageId:                  messageId,
		InGameShare:                inGameShare,
		ReplaceVideoStartTimestamp: opts.ReplaceVideoStartTimestamp,
		NewVideoStartTimestamp:     opts.NewVideoStartTimestamp,
	}

	return c.sendMessageWithContent(chatId, content, &MessageSendOptions{
		DisableNotification:               opts.DisableNotification,
		EffectId:                          opts.EffectId,
		FromBackground:                    opts.FromBackground,
		OnlyPreview:                       opts.OnlyPreview,
		PaidMessageStarCount:              opts.PaidMessageStarCount,
		ProtectContent:                    opts.ProtectContent,
		SchedulingState:                   opts.SchedulingState,
		SendingId:                         opts.SendingId,
		UpdateOrderOfInstalledStickerSets: opts.UpdateOrderOfInstalledStickerSets,
	}, opts.TopicId, opts.Quote, opts.ReplyTo, opts.ReplyToMessageID, opts.ReplyMarkup, 0, 0, false)
}
