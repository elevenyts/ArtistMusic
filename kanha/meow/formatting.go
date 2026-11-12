package gotdbot

import (
	"fmt"
	"sort"
	"strings"
	"unicode/utf16"
)

// OriginalMD gets the original markdown formatting of a message text.
func (m *Message) OriginalMD() string {
	text, err := m.GetFormattedText()
	if err != nil {
		return ""
	}
	return UnparseEntities(text.Text, text.Entities, "markdown")
}

// OriginalMDV2 gets the original markdownV2 formatting of a message text.
func (m *Message) OriginalMDV2() string {
	text, err := m.GetFormattedText()
	if err != nil {
		return ""
	}
	return UnparseEntities(text.Text, text.Entities, "markdownv2")
}

// OriginalHTML gets the original HTML formatting of a message text.
func (m *Message) OriginalHTML() string {
	text, err := m.GetFormattedText()
	if err != nil {
		return ""
	}
	return UnparseEntities(text.Text, text.Entities, "html")
}

// OriginalCaptionMD gets the original markdown formatting of a message caption.
func (m *Message) OriginalCaptionMD() string {
	caption, err := m.GetFormattedCaption()
	if err != nil {
		return ""
	}
	return UnparseEntities(caption.Text, caption.Entities, "markdown")
}

// OriginalCaptionMDV2 gets the original markdownV2 formatting of a message caption.
func (m *Message) OriginalCaptionMDV2() string {
	caption, err := m.GetFormattedCaption()
	if err != nil {
		return ""
	}
	return UnparseEntities(caption.Text, caption.Entities, "markdownv2")
}

// OriginalCaptionHTML gets the original HTML formatting of a message caption.
func (m *Message) OriginalCaptionHTML() string {
	caption, err := m.GetFormattedCaption()
	if err != nil {
		return ""
	}
	return UnparseEntities(caption.Text, caption.Entities, "html")
}

// entityEvent represents the start or end of an entity
type entityEvent struct {
	Index   int
	IsStart bool
	Entity  *TextEntity
	Level   int
}

func buildFormatString(format DateTimeFormattingType) string {
	if format == nil {
		return ""
	}
	switch f := format.(type) {
	case *DateTimeFormattingTypeRelative, DateTimeFormattingTypeRelative:
		return "r"
	case *DateTimeFormattingTypeAbsolute:
		formatStr := ""
		if f.ShowDayOfWeek {
			formatStr += "w"
		}
		if f.DatePrecision != nil {
			switch f.DatePrecision.(type) {
			case *DateTimePartPrecisionShort:
				formatStr += "d"
			case *DateTimePartPrecisionLong:
				formatStr += "D"
			}
		}
		if f.TimePrecision != nil {
			switch f.TimePrecision.(type) {
			case *DateTimePartPrecisionShort:
				formatStr += "t"
			case *DateTimePartPrecisionLong:
				formatStr += "T"
			}
		}
		return formatStr
	case DateTimeFormattingTypeAbsolute:
		formatStr := ""
		if f.ShowDayOfWeek {
			formatStr += "w"
		}
		if f.DatePrecision != nil {
			switch f.DatePrecision.(type) {
			case *DateTimePartPrecisionShort:
				formatStr += "d"
			case *DateTimePartPrecisionLong:
				formatStr += "D"
			}
		}
		if f.TimePrecision != nil {
			switch f.TimePrecision.(type) {
			case *DateTimePartPrecisionShort:
				formatStr += "t"
			case *DateTimePartPrecisionLong:
				formatStr += "T"
			}
		}
		return formatStr
	}
	return ""
}

// escapeText escapes special characters for HTML and MDV2.
func escapeText(text, mode string) string {
	if mode == "html" {
		text = strings.ReplaceAll(text, "&", "&amp;")
		text = strings.ReplaceAll(text, "<", "&lt;")
		text = strings.ReplaceAll(text, ">", "&gt;")
		return text
	} else if mode == "markdownv2" {
		specials := []string{"\\", "_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"}
		for _, s := range specials {
			text = strings.ReplaceAll(text, s, "\\"+s)
		}
		return text
	} else if mode == "markdownv2_url" {
		specials := []string{"\\", ")"}
		for _, s := range specials {
			text = strings.ReplaceAll(text, s, "\\"+s)
		}
		return text
	} else if mode == "markdownv2_code" {
		specials := []string{"\\", "`"}
		for _, s := range specials {
			text = strings.ReplaceAll(text, s, "\\"+s)
		}
		return text
	} else if mode == "markdown_code" {
		specials := []string{"\\", "`"}
		for _, s := range specials {
			text = strings.ReplaceAll(text, s, "\\"+s)
		}
		return text
	} else if mode == "markdown" {
		specials := []string{"*", "_", "`", "["}
		for _, s := range specials {
			text = strings.ReplaceAll(text, s, "\\"+s)
		}
		return text
	}
	return text
}

// UnparseEntities converts plain text with entities into a formatted string (Markdown, MarkdownV2, HTML).
func UnparseEntities(text string, entities []TextEntity, mode string) string {
	if len(entities) == 0 {
		return escapeText(text, mode)
	}

	utf16Str := utf16.Encode([]rune(text))
	var events []entityEvent

	for i, ent := range entities {
		e := ent
		events = append(events, entityEvent{Index: int(e.Offset), IsStart: true, Entity: &e, Level: i})
		events = append(events, entityEvent{Index: int(e.Offset + e.Length), IsStart: false, Entity: &e, Level: i})
	}

	sort.SliceStable(events, func(i, j int) bool {
		if events[i].Index != events[j].Index {
			return events[i].Index < events[j].Index
		}
		if events[i].IsStart != events[j].IsStart {
			return !events[i].IsStart
		}
		if events[i].IsStart {
			return events[i].Level < events[j].Level
		}

		return events[i].Level > events[j].Level
	})

	var result strings.Builder
	lastIndex := 0

	for _, ev := range events {
		if ev.Index > lastIndex {
			if lastIndex < len(utf16Str) {
				end := ev.Index
				if end > len(utf16Str) {
					end = len(utf16Str)
				}
				chunk := string(utf16.Decode(utf16Str[lastIndex:end]))

				inCode := false
				isRaw := false
				inBlockQuote := false
				for _, ent := range entities {
					switch ent.Type.(type) {
					case *TextEntityTypeCode, TextEntityTypeCode,
						*TextEntityTypePre, TextEntityTypePre,
						*TextEntityTypePreCode, TextEntityTypePreCode:
						if int(ent.Offset) <= lastIndex && int(ent.Offset+ent.Length) >= end {
							inCode = true
						}
					case *TextEntityTypeUrl, TextEntityTypeUrl,
						*TextEntityTypeEmailAddress, TextEntityTypeEmailAddress,
						*TextEntityTypePhoneNumber, TextEntityTypePhoneNumber,
						*TextEntityTypeHashtag, TextEntityTypeHashtag,
						*TextEntityTypeCashtag, TextEntityTypeCashtag,
						*TextEntityTypeBankCardNumber, TextEntityTypeBankCardNumber,
						*TextEntityTypeBotCommand, TextEntityTypeBotCommand,
						*TextEntityTypeMention, TextEntityTypeMention:
						if int(ent.Offset) <= lastIndex && int(ent.Offset+ent.Length) >= end {
							isRaw = true
						}
					case *TextEntityTypeBlockQuote, TextEntityTypeBlockQuote,
						*TextEntityTypeExpandableBlockQuote, TextEntityTypeExpandableBlockQuote:
						if int(ent.Offset) <= lastIndex && int(ent.Offset+ent.Length) >= end {
							inBlockQuote = true
						}
					}
				}

				if isRaw {
					//
				} else if inCode && (mode == "markdownv2" || mode == "markdown") {
					chunk = escapeText(chunk, mode+"_code")
				} else {
					chunk = escapeText(chunk, mode)
				}

				if inBlockQuote && mode == "markdownv2" {
					chunk = strings.ReplaceAll(chunk, "\n", "\n>")
				}

				result.WriteString(chunk)
			}
			lastIndex = ev.Index
		}

		end := int(ev.Entity.Offset + ev.Entity.Length)
		if end > len(utf16Str) {
			end = len(utf16Str)
		}
		extractedText := ""
		if ev.Entity.Offset <= int32(len(utf16Str)) {
			extractedText = string(utf16.Decode(utf16Str[ev.Entity.Offset:end]))
		}
		tag := getTag(ev.Entity, ev.IsStart, mode, extractedText)
		result.WriteString(tag)
	}

	if lastIndex < len(utf16Str) {
		chunk := string(utf16.Decode(utf16Str[lastIndex:]))
		result.WriteString(escapeText(chunk, mode))
	}

	if mode == "markdownv2" || mode == "markdown" {
		res := result.String()
		res = strings.ReplaceAll(res, "_\r", "_")
		res = strings.ReplaceAll(res, "\r_", "_")
		res = strings.ReplaceAll(res, "__\r", "__")
		res = strings.ReplaceAll(res, "\r__", "__")
		return res
	}

	return result.String()
}

func getTag(ent *TextEntity, isStart bool, mode string, _ string) string {
	switch e := ent.Type.(type) {
	case *TextEntityTypeBold, TextEntityTypeBold:
		if mode == "html" {
			if isStart {
				return "<b>"
			} else {
				return "</b>"
			}
		} else {
			return "*"
		}
	case *TextEntityTypeItalic, TextEntityTypeItalic:
		if mode == "html" {
			if isStart {
				return "<i>"
			} else {
				return "</i>"
			}
		} else {
			if isStart {
				return "_\r"
			} else {
				return "\r_"
			}
		}
	case *TextEntityTypeUnderline, TextEntityTypeUnderline:
		if mode == "html" {
			if isStart {
				return "<u>"
			} else {
				return "</u>"
			}
		} else if mode == "markdownv2" {
			if isStart {
				return "__\r"
			} else {
				return "\r__"
			}
		}
	case *TextEntityTypeStrikethrough, TextEntityTypeStrikethrough:
		if mode == "html" {
			if isStart {
				return "<s>"
			} else {
				return "</s>"
			}
		} else if mode == "markdownv2" {
			return "~"
		}
	case *TextEntityTypeSpoiler, TextEntityTypeSpoiler:
		if mode == "html" {
			if isStart {
				return "<tg-spoiler>"
			} else {
				return "</tg-spoiler>"
			}
		} else if mode == "markdownv2" {
			return "||"
		}
	case *TextEntityTypeCode, TextEntityTypeCode:
		if mode == "html" {
			if isStart {
				return "<code>"
			} else {
				return "</code>"
			}
		} else {
			return "`"
		}
	case *TextEntityTypePre, TextEntityTypePre:
		if mode == "html" {
			if isStart {
				return "<pre>"
			} else {
				return "</pre>"
			}
		} else {
			return "```\n"
		}
	case *TextEntityTypePreCode:
		lang := e.Language
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<pre><code class=\"language-%s\">", lang)
			} else {
				return "</code></pre>"
			}
		} else {
			if isStart {
				return fmt.Sprintf("```%s\n", lang)
			} else {
				return "```\n"
			}
		}
	case TextEntityTypePreCode:
		lang := e.Language
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<pre><code class=\"language-%s\">", lang)
			} else {
				return "</code></pre>"
			}
		} else {
			if isStart {
				return fmt.Sprintf("```%s\n", lang)
			} else {
				return "```\n"
			}
		}
	case *TextEntityTypeTextUrl:
		url := e.Url
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<a href=\"%s\">", url)
			} else {
				return "</a>"
			}
		} else {
			if isStart {
				return "["
			} else {
				return fmt.Sprintf("](%s)", escapeText(url, mode+"_url"))
			}
		}
	case TextEntityTypeTextUrl:
		url := e.Url
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<a href=\"%s\">", url)
			} else {
				return "</a>"
			}
		} else {
			if isStart {
				return "["
			} else {
				return fmt.Sprintf("](%s)", escapeText(url, mode+"_url"))
			}
		}
	case *TextEntityTypeMentionName:
		userId := e.UserId
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<a href=\"tg://user?id=%d\">", userId)
			} else {
				return "</a>"
			}
		} else {
			if isStart {
				return "["
			} else {
				return fmt.Sprintf("](tg://user?id=%d)", userId)
			}
		}
	case TextEntityTypeMentionName:
		userId := e.UserId
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<a href=\"tg://user?id=%d\">", userId)
			} else {
				return "</a>"
			}
		} else {
			if isStart {
				return "["
			} else {
				return fmt.Sprintf("](tg://user?id=%d)", userId)
			}
		}
	case *TextEntityTypeCustomEmoji:
		emojiId := e.CustomEmojiId
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<tg-emoji emoji-id=\"%d\">", emojiId)
			} else {
				return "</tg-emoji>"
			}
		} else if mode == "markdownv2" {
			if isStart {
				return "!["
			} else {
				return fmt.Sprintf("](tg://emoji?id=%d)", emojiId)
			}
		}
	case TextEntityTypeCustomEmoji:
		emojiId := e.CustomEmojiId
		if mode == "html" {
			if isStart {
				return fmt.Sprintf("<tg-emoji emoji-id=\"%d\">", emojiId)
			} else {
				return "</tg-emoji>"
			}
		} else if mode == "markdownv2" {
			if isStart {
				return "!["
			} else {
				return fmt.Sprintf("](tg://emoji?id=%d)", emojiId)
			}
		}
	case *TextEntityTypeBlockQuote, TextEntityTypeBlockQuote:
		if mode == "html" {
			if isStart {
				return "<blockquote>"
			} else {
				return "</blockquote>"
			}
		} else if mode == "markdownv2" {
			if isStart {
				return ">"
			} else {
				return ""
			}
		}
	case *TextEntityTypeExpandableBlockQuote, TextEntityTypeExpandableBlockQuote:
		if mode == "html" {
			if isStart {
				return "<blockquote expandable>"
			} else {
				return "</blockquote>"
			}
		} else if mode == "markdownv2" {
			if isStart {
				return "**>"
			} else {
				return "||"
			}
		}
	case *TextEntityTypeDateTime, TextEntityTypeDateTime:
		var unixTime int32
		var formattingType DateTimeFormattingType
		if ptr, ok := e.(*TextEntityTypeDateTime); ok {
			unixTime = ptr.UnixTime
			formattingType = ptr.FormattingType
		} else {
			val := e.(TextEntityTypeDateTime)
			unixTime = val.UnixTime
			formattingType = val.FormattingType
		}
		formatStr := buildFormatString(formattingType)

		if mode == "html" {
			if isStart {
				if formatStr == "" {
					return fmt.Sprintf("<tg-time unix=\"%d\">", unixTime)
				}
				return fmt.Sprintf("<tg-time unix=\"%d\" format=\"%s\">", unixTime, formatStr)
			} else {
				return "</tg-time>"
			}
		} else if mode == "markdownv2" {
			if isStart {
				return "!["
			} else {
				if formatStr == "" {
					return fmt.Sprintf("](tg://time?unix=%d)", unixTime)
				}
				return fmt.Sprintf("](tg://time?unix=%d&format=%s)", unixTime, escapeText(formatStr, "markdownv2_url"))
			}
		}
	// Entities that don't add formatting syntax because they're implicit (Urls, Emails, Phone numbers, Hashtags, etc.)
	case *TextEntityTypeUrl, TextEntityTypeUrl,
		*TextEntityTypeEmailAddress, TextEntityTypeEmailAddress,
		*TextEntityTypePhoneNumber, TextEntityTypePhoneNumber,
		*TextEntityTypeHashtag, TextEntityTypeHashtag,
		*TextEntityTypeCashtag, TextEntityTypeCashtag,
		*TextEntityTypeBankCardNumber, TextEntityTypeBankCardNumber,
		*TextEntityTypeBotCommand, TextEntityTypeBotCommand,
		*TextEntityTypeMention, TextEntityTypeMention,
		*TextEntityTypeMediaTimestamp, TextEntityTypeMediaTimestamp:
		return ""
	}
	return ""
}
