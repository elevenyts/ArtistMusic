package main

//go:generate go run ../../scripts/tools/get_tdjson.go

import (
	"fmt"
	"log"
	"runtime"
	"time"

	"github.com/Kanha/Meow"
	"github.com/Kanha/Meow/filters/message"
)

func main() {
	apiID := int32(6)
	apiHash := ""
	botToken := ""

	bot, err := gotdbot.NewClient(apiID, apiHash, botToken, &gotdbot.ClientOpts{LibraryPath: "./libtdjson.so.1.8.67"})
	if err != nil {
		panic(err)
	}

	var startTime = time.Now()

	bot.OnCommand("start", func(c *gotdbot.Client, u *gotdbot.Message) error {
		kb := &gotdbot.ReplyMarkupInlineKeyboard{
			Rows: [][]gotdbot.InlineKeyboardButton{
				{
					{
						Text: "GoTDBot GitHub",
						Type: &gotdbot.InlineKeyboardButtonTypeUrl{
							Url: "https://github.com/Kanha/Meow",
						},
					},
				},
			},
		}

		content := &gotdbot.InputMessageText{
			Text: &gotdbot.FormattedText{
				Text: "Hello! I am an echo bot powered by gotdbot " + gotdbot.Version,
			},
		}

		opts := &gotdbot.SendMessageOpts{
			ReplyTo: &gotdbot.InputMessageReplyToMessage{
				MessageId: u.Id,
			},
			ReplyMarkup: kb,
		}

		_, err := c.SendMessage(u.ChatId, content, opts)
		if err != nil {
			log.Printf("Error sending message: %v", err)
		}
		return nil
	})

	bot.OnUpdateDeleteMessages(func(c *gotdbot.Client, u *gotdbot.UpdateDeleteMessages) error {
		log.Printf("Messages deleted: %v (ChatID %d)", u.MessageIds, u.ChatId)
		return nil
	}, nil)

	bot.OnCommand("go", func(c *gotdbot.Client, u *gotdbot.Message) error {
		var m runtime.MemStats
		runtime.ReadMemStats(&m)

		uptime := time.Since(startTime).Round(time.Second)
		reply := fmt.Sprintf(
			"Go runtime stats\n\n"+
				"• Goroutines : %d\n"+
				"• CPUs       : %d\n"+
				"• GOMAXPROCS : %d\n"+
				"• Uptime     : %s\n\n"+
				"Memory\n"+
				"• Alloc      : %.2f MB\n"+
				"• HeapAlloc  : %.2f MB\n"+
				"• Sys        : %.2f MB\n"+
				"• GC cycles  : %d",
			runtime.NumGoroutine(),
			runtime.NumCPU(),
			runtime.GOMAXPROCS(0),
			uptime,
			float64(m.Alloc)/1024/1024,
			float64(m.HeapAlloc)/1024/1024,
			float64(m.Sys)/1024/1024,
			m.NumGC,
		)

		_, err := c.SendTextMessage(u.ChatId, reply, &gotdbot.SendTextMessageOpts{ReplyToMessageID: u.Id})
		return err
	})

	// Example using a filter to only echo private messages
	bot.OnMessage(func(c *gotdbot.Client, u *gotdbot.Message) error {
		_, err := c.ForwardMessages(u.ChatId, u.ChatId, []int64{u.Id}, &gotdbot.ForwardMessagesOpts{SendCopy: true})
		return err
	}, message.Private)

	err = bot.Start()
	if err != nil {
		log.Fatalf("Failed to start bot: %v", err)
	}

	me, _ := bot.GetMe()
	username := ""
	if me.Usernames != nil && len(me.Usernames.ActiveUsernames) > 0 {
		username = me.Usernames.ActiveUsernames[0]
	}
	bot.Logger.Info("Logged in", "username", username, "id", me.Id)
	bot.Idle()
}
