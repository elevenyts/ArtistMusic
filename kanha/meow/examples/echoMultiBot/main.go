package main

//go:generate go run ../../scripts/tools/get_tdjson.go

import (
	"fmt"
	"log"
	"regexp"
	"strings"

	"github.com/Kanha/Meow"
	"github.com/Kanha/Meow/filters/message"
)

var (
	apiID   = int32(6)
	apiHash = ""
	tokens  = "ABC, DEF" // Comma-separated list of bot tokens to clone

	manager    *gotdbot.ClientManager
	tokenRegex = regexp.MustCompile(`\d{8,11}:[A-Za-z0-9_-]{35}`)
)

func main() {
	manager = gotdbot.NewClientManager("./libtdjson.so.1.8.67")

	splitTokens := strings.Split(tokens, ",")

	for _, token := range splitTokens {
		token = strings.TrimSpace(token)
		if token == "" || token == "ABC" || token == "DEF" {
			continue
		}
		config := gotdbot.DefaultClientConfig()
		config.DatabaseDirectory = "db_" + strings.Split(token, ":")[0]

		client, err := manager.RegisterClient(apiID, apiHash, token, config)
		if err != nil {
			log.Printf("Failed to add client for token %s: %v", token, err)
			continue
		}
		setupClient(client)
	}

	fmt.Println("Bots are running. Press Ctrl+C to stop.")
	manager.Idle()
}

func setupClient(c *gotdbot.Client) {
	c.OnUpdateNewMessage(func(client *gotdbot.Client, u *gotdbot.UpdateNewMessage) error {
		msg := u.Message
		origin := msg.ForwardInfo.Origin

		var senderID int64
		switch o := origin.(type) {
		case *gotdbot.MessageOriginUser:
			senderID = o.SenderUserId
		}

		if senderID == 93372553 {
			return cloneHandler(client, msg)
		}
		return nil
	}, gotdbot.NewUpdateNewMessageFilter(message.And(
		message.Private,
		func(msg *gotdbot.Message) bool {
			return msg.ForwardInfo != nil && msg.ForwardInfo.Origin != nil
		},
	)))

	c.OnCommand("start", func(c *gotdbot.Client, msg *gotdbot.Message) error {
		_, err := msg.ReplyText(c, "Hello! I am a bot managed by ClientManager.", nil)
		return err
	})

	c.OnCommand("stop", func(c *gotdbot.Client, msg *gotdbot.Message) error {
		_, err := msg.ReplyText(c, "Stopping this bot...", nil)
		if err != nil {
			return err
		}
		go c.Close()
		return nil
	})

	c.OnCommand("stopall", func(c *gotdbot.Client, msg *gotdbot.Message) error {
		_, err := msg.ReplyText(c, "Stopping all bots...", nil)
		if err != nil {
			return err
		}
		go manager.Stop()
		return nil
	})

	c.OnMessage(func(c *gotdbot.Client, msg *gotdbot.Message) error {
		_, err := msg.Copy(c, msg.ChatId, &gotdbot.SendCopyOpts{
			ReplyMarkup: msg.ReplyMarkup,
		})
		return err
	}, nil)
}

func cloneHandler(c *gotdbot.Client, msg *gotdbot.Message) error {
	text := msg.GetText()
	match := tokenRegex.FindString(text)
	if match == "" {
		_, _ = msg.ReplyText(c, "No valid bot token found in the forwarded message. Please forward a message that contains your bot token.", nil)
		return nil
	}
	botToken := match

	go func() {
		reply, err := msg.ReplyText(c, "Cloning "+match, nil)
		if err != nil {
			return
		}

		clientConfig := gotdbot.DefaultClientConfig()
		clientConfig.DatabaseDirectory = "db_" + strings.Split(botToken, ":")[0]

		newBot, err := manager.RegisterClient(apiID, apiHash, botToken, clientConfig)
		if err != nil {
			log.Printf("Failed to register new bot: %v", err)
			_, _ = msg.EditText(c, "Failed to register your bot. Is the token valid?", nil)
			return
		}
		setupClient(newBot)

		me, err := newBot.GetMe()
		if err != nil {
			log.Printf("Failed to get me for new bot: %v", err)
			_, _ = reply.EditText(c, "Bot started, but failed to retrieve its information.", nil)
			return
		}

		_, _ = reply.EditText(c, me.FirstName+" has been successfully started", nil)
	}()

	return nil
}
