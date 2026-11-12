package gotdbot_test

import (
	"testing"

	"github.com/Kanha/Meow"
)

func TestUnparseEntities(t *testing.T) {
	tests := []struct {
		name     string
		text     string
		entities []gotdbot.TextEntity
		mode     string
		expected string
	}{
		{
			name:     "Plain text HTML",
			text:     "Hello <World> & Everyone",
			entities: nil,
			mode:     "html",
			expected: "Hello &lt;World&gt; &amp; Everyone",
		},
		{
			name:     "Plain text MDV2",
			text:     "Hello. World!",
			entities: nil,
			mode:     "markdownv2",
			expected: "Hello\\. World\\!",
		},
		{
			name: "Bold and Italic HTML",
			text: "Bold and Italic",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 4, Type: &gotdbot.TextEntityTypeBold{}},
				{Offset: 9, Length: 6, Type: &gotdbot.TextEntityTypeItalic{}},
			},
			mode:     "html",
			expected: "<b>Bold</b> and <i>Italic</i>",
		},
		{
			name: "Bold and Italic MDV2",
			text: "Bold and Italic",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 4, Type: &gotdbot.TextEntityTypeBold{}},
				{Offset: 9, Length: 6, Type: &gotdbot.TextEntityTypeItalic{}},
			},
			mode:     "markdownv2",
			expected: "*Bold* and _Italic_",
		},
		{
			name: "Mention Name HTML",
			text: "User Name",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 9, Type: &gotdbot.TextEntityTypeMentionName{UserId: 123456789}},
			},
			mode:     "html",
			expected: "<a href=\"tg://user?id=123456789\">User Name</a>",
		},
		{
			name: "Mention Name MDV2",
			text: "User Name",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 9, Type: &gotdbot.TextEntityTypeMentionName{UserId: 123456789}},
			},
			mode:     "markdownv2",
			expected: "[User Name](tg://user?id=123456789)",
		},
		{
			name: "Text URL HTML",
			text: "Open Link",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 9, Type: &gotdbot.TextEntityTypeTextUrl{Url: "https://example.com"}},
			},
			mode:     "html",
			expected: "<a href=\"https://example.com\">Open Link</a>",
		},
		{
			name: "Text URL MDV2",
			text: "Open Link",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 9, Type: &gotdbot.TextEntityTypeTextUrl{Url: "https://example.com/test?a=1&b=2"}},
			},
			mode:     "markdownv2",
			expected: "[Open Link](https://example.com/test?a=1&b=2)",
		},
		{
			name: "Custom Emoji HTML",
			text: "Smile",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 5, Type: &gotdbot.TextEntityTypeCustomEmoji{CustomEmojiId: 123456}},
			},
			mode:     "html",
			expected: "<tg-emoji emoji-id=\"123456\">Smile</tg-emoji>",
		},
		{
			name: "Custom Emoji MDV2",
			text: "Smile",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 5, Type: &gotdbot.TextEntityTypeCustomEmoji{CustomEmojiId: 123456}},
			},
			mode:     "markdownv2",
			expected: "![Smile](tg://emoji?id=123456)",
		},
		{
			name: "Date Time HTML",
			text: "tomorrow",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 8, Type: &gotdbot.TextEntityTypeDateTime{UnixTime: 1234567890, FormattingType: &gotdbot.DateTimeFormattingTypeRelative{}}},
			},
			mode:     "html",
			expected: "<tg-time unix=\"1234567890\" format=\"r\">tomorrow</tg-time>",
		},
		{
			name: "Date Time MDV2",
			text: "tomorrow",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 8, Type: &gotdbot.TextEntityTypeDateTime{UnixTime: 1234567890, FormattingType: &gotdbot.DateTimeFormattingTypeRelative{}}},
			},
			mode:     "markdownv2",
			expected: "![tomorrow](tg://time?unix=1234567890&format=r)",
		},
		{
			name: "Implicit Entity Mention MDV2",
			text: "@username",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 9, Type: &gotdbot.TextEntityTypeMention{}},
			},
			mode:     "markdownv2",
			expected: "@username",
		},
		{
			name: "Implicit Entity URL MDV2",
			text: "https://example.com",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 19, Type: &gotdbot.TextEntityTypeUrl{}},
			},
			mode:     "markdownv2",
			expected: "https://example.com",
		},
		{
			name: "Pre Code HTML",
			text: "print('hello')",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 14, Type: &gotdbot.TextEntityTypePreCode{Language: "python"}},
			},
			mode:     "html",
			expected: "<pre><code class=\"language-python\">print('hello')</code></pre>",
		},
		{
			name: "Pre Code MDV2",
			text: "print('hello')",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 14, Type: &gotdbot.TextEntityTypePreCode{Language: "python"}},
			},
			mode:     "markdownv2",
			expected: "```python\nprint('hello')```\n",
		},
		{
			name: "Underline MDV2 Ambiguity Test",
			text: "under",
			entities: []gotdbot.TextEntity{
				{Offset: 0, Length: 5, Type: &gotdbot.TextEntityTypeUnderline{}},
			},
			mode:     "markdownv2",
			expected: "__under__",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := gotdbot.UnparseEntities(tt.text, tt.entities, tt.mode)
			if result != tt.expected {
				t.Errorf("UnparseEntities() = %v, want %v", result, tt.expected)
			}
		})
	}
}
