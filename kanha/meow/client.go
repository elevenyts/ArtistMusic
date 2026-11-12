package gotdbot

//go:generate go run ./internal/gen

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"

	"os/signal"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/Kanha/Meow/logger"

	"github.com/Kanha/Meow/internal/qrcode"
	"github.com/Kanha/Meow/internal/tdjson"
)

type Client struct {
	manager  *ClientManager
	clientID int

	apiID    int32
	apiHash  string
	botToken string
	// phoneNumber is set if the user is logging in with a phone number.
	phoneNumber string
	config      *ClientOpts
	Logger      *logger.Logger

	updates chan TlObject
	stop    chan struct{}
	closed  chan struct{}
	wg      sync.WaitGroup

	handlers     atomic.Pointer[handlersData]
	hMu          sync.Mutex
	panicHandler func(client *Client, update TlObject, r interface{})
	errorHandler func(client *Client, update TlObject, err error) error

	pendingRequests sync.Map // map[string]chan TlObject
	pendingMessages sync.Map // map[string]chan TlObject

	waiters     map[int64]map[string]*Waiter
	waiterCount atomic.Int64
	wMu         sync.RWMutex

	// Auth state management
	authErrorChan chan error
	isAuthorized  bool
	startOnce     sync.Once
	closeOnce     sync.Once
	requestID     atomic.Uint64

	// Me is the bot's User info, as returned by client.GetMe.
	// Populated when authorization is ready.
	Me *User
}

func NewClient(apiID int32, apiHash, tokenOrPhone string, config *ClientOpts) (*Client, error) {
	tokenOrPhone = strings.TrimSpace(tokenOrPhone)
	if config == nil {
		config = DefaultClientConfig()
	} else {
		def := DefaultClientConfig()
		if config.UseFileDatabase == nil {
			config.UseFileDatabase = def.UseFileDatabase
		}
		if config.UseChatInfoDatabase == nil {
			config.UseChatInfoDatabase = def.UseChatInfoDatabase
		}
		if config.UseMessageDatabase == nil {
			config.UseMessageDatabase = def.UseMessageDatabase
		}
		if config.SystemLanguageCode == "" {
			config.SystemLanguageCode = def.SystemLanguageCode
		}
		if config.DeviceModel == "" {
			config.DeviceModel = def.DeviceModel
		}
		if config.SystemVersion == "" {
			config.SystemVersion = def.SystemVersion
		}
		if config.ApplicationVersion == "" {
			config.ApplicationVersion = def.ApplicationVersion
		}
		if config.DatabaseDirectory == "" {
			config.DatabaseDirectory = def.DatabaseDirectory
		}
		if config.FilesDirectory == "" {
			config.FilesDirectory = def.FilesDirectory
		}
		if config.Logger == nil {
			config.Logger = def.Logger
		}
		if config.AuthorizationTimeout == 0 {
			config.AuthorizationTimeout = def.AuthorizationTimeout
		}
		if config.AutoRetry == nil {
			config.AutoRetry = def.AutoRetry
		}
		if config.ParseMode == "" {
			config.ParseMode = def.ParseMode
		}
	}

	if err := tdjson.Init(config.LibraryPath); err != nil {
		return nil, err
	}

	botTokenRegex := regexp.MustCompile(`^\d+:[a-zA-Z0-9_-]+$`)
	var botToken, phoneNumber string
	if botTokenRegex.MatchString(tokenOrPhone) {
		botToken = tokenOrPhone
	} else {
		phoneNumber = tokenOrPhone
	}

	c := &Client{
		clientID:      tdjson.CreateClientID(),
		apiID:         apiID,
		apiHash:       apiHash,
		botToken:      botToken,
		phoneNumber:   phoneNumber,
		config:        config,
		Logger:        config.Logger,
		updates:       make(chan TlObject, 1000),
		stop:          make(chan struct{}),
		closed:        make(chan struct{}),
		authErrorChan: make(chan error, 1),
	}

	c.handlers.Store(&handlersData{
		handlers: make(map[int][]Handler),
	})
	c.waiters = make(map[int64]map[string]*Waiter)
	c.panicHandler = config.PanicHandler
	c.errorHandler = config.ErrorHandler

	c.AddUpdateAuthorizationStateHandlerGroup(c.authHandler, nil, -100)
	c.AddUpdateMessageSendSucceededHandlerGroup(c.messageSendSucceededHandler, nil, -99)
	c.AddUpdateMessageSendFailedHandlerGroup(c.messageSendFailedHandler, nil, -98)
	c.AddUpdateConnectionStateHandlerGroup(c.connectionStateHandler, nil, -97)
	return c, nil
}

// initClient initializes the client's internal state and processor loop exactly once.
func (c *Client) initClient() {
	tdjson.Send(c.clientID, `{"@type": "getOption", "name": "version"}`)

	c.startOnce.Do(func() {
		if c.manager == nil {
			m := GetDefaultManager(c.config.LibraryPath)
			m.AddClient(c)
		}

		c.wg.Add(1)
		go c.processor()
	})
}

// Start initializes the client and blocks until authorization is successful or fails.
func (c *Client) Start() error {
	c.initClient()

	select {
	case err := <-c.authErrorChan:
		return err
	case <-time.After(c.config.AuthorizationTimeout):
		return fmt.Errorf("authorization timeout")
	}
}

// SendDummyRequest sends a dummy request to TDLib to initialize its state.
// This is useful if you need to call unauthenticated TDLib methods before calling Start().
func (c *Client) SendDummyRequest() {
	c.initClient()
}

// Idle blocks the current goroutine until a SIGINT or SIGTERM signal is received.
func (c *Client) Idle() {
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	c.Close()
}

// Close closes the TDLib instance. All databases will be flushed to disk and properly
// closed. After the close completes, updateAuthorizationState with authorizationStateClosed
// will be sent. Can be called before initialization.
func (c *Client) Close() {
	c.closeOnce.Do(func() {
		_, _ = c.Send(&Close{})

		select {
		case <-c.closed:
		case <-time.After(5 * time.Second):
			c.Logger.Warn("Timeout waiting for TDLib to close")
		}

		close(c.stop)
		c.wg.Wait()
	})
}

func (c *Client) processor() {
	defer c.wg.Done()
	for {
		select {
		case <-c.stop:
			return
		case update := <-c.updates:
			go func() {
				defer func() {
					if r := recover(); r != nil {
						if c.panicHandler != nil {
							c.panicHandler(c, update, r)
						} else {
							c.Logger.Error("Panic in handler", "panic", r)
						}
					}
				}()

				c.wMu.RLock()
				if len(c.waiters) > 0 {
					var matchedWaiters []*Waiter
					chatID := getChatIDFromUpdate(update)

					collectWaiters := func(id int64) {
						if inner, ok := c.waiters[id]; ok {
							for _, w := range inner {
								if w.Filter(c, update) {
									matchedWaiters = append(matchedWaiters, w)
								}
							}
						}
					}

					collectWaiters(0)
					if chatID != 0 {
						collectWaiters(chatID)
					}
					c.wMu.RUnlock()

					for _, w := range matchedWaiters {
						select {
						case w.C <- update:
						default:
						}
					}
				} else {
					c.wMu.RUnlock()
				}

				hData := c.handlers.Load()
				handlersMap := hData.handlers
				groups := hData.groups

				handleError := func(err error) error {
					if err == nil {
						return nil
					}
					if errors.Is(err, EndGroups) || errors.Is(err, ContinueGroups) || errors.Is(err, ContinueHandlers) {
						return err
					}
					if c.errorHandler != nil {
						return c.errorHandler(c, update, err)
					}
					c.Logger.Error("Handler error", "error", err, "type", update.GetType())
					return nil
				}

			outerLoop:
				for _, group := range groups {
					groupHandlers := handlersMap[group]
					for _, h := range groupHandlers {
						if h.CheckUpdate(c, update) {
							err := h.HandleUpdate(c, update)
							action := handleError(err)

							if errors.Is(action, EndGroups) {
								return
							}
							if errors.Is(action, ContinueGroups) {
								break // Move to next group
							}
							if errors.Is(action, ContinueHandlers) {
								continue // Move to next handler in same group
							}
							// Handler matched and succeeded; move to next group.
							break outerLoop
						}
					}
				}
			}()
		}
	}
}

// sendAuthError delivers err to authErrorChan without blocking.
func (c *Client) sendAuthError(err error) {
	select {
	case c.authErrorChan <- err:
	default:
	}
}

func (c *Client) authHandler(client *Client, authState *UpdateAuthorizationState) error {
	c.Logger.Debug("Authorization state update", "state", authState.AuthorizationState.GetType())

	switch state := authState.AuthorizationState.(type) {
	case *AuthorizationStateWaitTdlibParameters:
		if c.config.TDLibOptions != nil {
			c.config.TDLibOptions.forEachSet(func(k string, v interface{}) {
				if opt := toOptionValue(v); opt != nil {
					err := c.SetOption(k, &SetOptionOpts{Value: opt})
					if err != nil {
						c.Logger.Error("Error setting option", "option", k, "error", err)
					}
				}
			})
		}

		err := c.SetTdlibParameters(
			c.apiHash,
			c.apiID,
			c.config.ApplicationVersion,
			c.config.DatabaseDirectory,
			[]byte(c.config.DatabaseEncryptionKey),
			c.config.DeviceModel,
			c.config.FilesDirectory,
			c.config.SystemLanguageCode,
			c.config.SystemVersion,
			&SetTdlibParametersOpts{
				UseChatInfoDatabase: *c.config.UseChatInfoDatabase,
				UseFileDatabase:     *c.config.UseFileDatabase,
				UseMessageDatabase:  *c.config.UseMessageDatabase,
				UseSecretChats:      c.config.UseSecretChats,
				UseTestDc:           c.config.UseTestDC,
			},
		)
		if err != nil {
			c.Logger.Error("Error setting tdlib parameters", "error", err)
			c.sendAuthError(err)
		}

	case *AuthorizationStateWaitPhoneNumber:
		if c.botToken != "" {
			err := c.CheckAuthenticationBotToken(c.botToken)
			if err != nil {
				c.Logger.Error("Error checking bot token", "error", err)
				c.sendAuthError(err)
			}
		} else {
			if c.config.QrMode {
				err := c.RequestQrCodeAuthentication(nil)
				if err != nil {
					c.Logger.Error("Error requesting QR code", "error", err)
					c.sendAuthError(err)
				}
			} else if c.phoneNumber != "" {
				err := c.SetAuthenticationPhoneNumber(c.phoneNumber, nil)
				if err != nil {
					c.Logger.Error("Error setting phone number", "error", err)
					c.sendAuthError(err)
				}
			} else {
				fmt.Print("Enter phone number: ")
				reader := bufio.NewReader(os.Stdin)
				phone, _ := reader.ReadString('\n')
				phone = strings.TrimSpace(phone)
				err := c.SetAuthenticationPhoneNumber(phone, nil)
				if err != nil {
					c.Logger.Error("Error setting phone number", "error", err)
					c.sendAuthError(err)
				}
			}
		}

	case *AuthorizationStateWaitOtherDeviceConfirmation:
		link := state.Link
		fmt.Printf("Scan the QR code below: or open the link in Telegram: %s\n", link)
		q, err := qrcode.NewQRCode(link)
		if err != nil {
			fmt.Printf("Failed to generate QR: %v\nLink: %s\n", err, link)
		} else {
			fmt.Println(q.ToSmallString(false))
		}

	case *AuthorizationStateWaitCode:
		codeInfo := state.CodeInfo
		codeType := strings.TrimPrefix(codeInfo.Type.GetType(), "authenticationCodeType")
		reader := bufio.NewReader(os.Stdin)
		for {
			fmt.Printf("Enter the code received via %s: ", codeType)
			code, _ := reader.ReadString('\n')
			code = strings.TrimSpace(code)
			if code == "" {
				continue
			}
			err := c.CheckAuthenticationCode(code)
			if err != nil {
				fmt.Printf("Error checking code: %v\n", err)
				continue
			}
			break
		}

	case *AuthorizationStateWaitPassword:
		hint := state.PasswordHint
		reader := bufio.NewReader(os.Stdin)
		for {
			fmt.Printf("Enter your 2FA password (hint: %s): ", hint)
			password, _ := reader.ReadString('\n')
			password = strings.TrimSpace(password)
			if password == "" {
				continue
			}
			err := c.CheckAuthenticationPassword(password)
			if err != nil {
				fmt.Printf("Error checking password: %v\n", err)
				continue
			}
			break
		}

	case *AuthorizationStateWaitRegistration:
		reader := bufio.NewReader(os.Stdin)
		fmt.Print("Enter first name: ")
		firstName, _ := reader.ReadString('\n')
		firstName = strings.TrimSpace(firstName)
		fmt.Print("Enter last name: ")
		lastName, _ := reader.ReadString('\n')
		lastName = strings.TrimSpace(lastName)

		err := c.RegisterUser(firstName, lastName, nil)
		if err != nil {
			c.Logger.Error("Error registering user", "error", err)
			c.sendAuthError(err)
		}

	case *AuthorizationStateWaitPremiumPurchase:
		c.Logger.Warn("Account is limited and requires Telegram Premium.")
		c.sendAuthError(WaitPremiumPurchase)

	case *AuthorizationStateReady:
		c.isAuthorized = true
		me, err := c.GetMe()
		if err != nil {
			c.Logger.Error("Failed to get me", "error", err)
			c.sendAuthError(err)
			return nil
		}

		c.Me = me

		username := ""
		if me.Usernames != nil && len(me.Usernames.ActiveUsernames) > 0 {
			username = me.Usernames.ActiveUsernames[0]
		}
		c.Logger.Info("Logged in", "user_id", me.Id, "username", username)

		c.sendAuthError(nil)

	case *AuthorizationStateClosed:
		if !c.isAuthorized {
			c.sendAuthError(fmt.Errorf("authorization closed unexpectedly"))
		}
		select {
		case <-c.closed:
		default:
			close(c.closed)
		}
	}
	return nil
}

func (c *Client) connectionStateHandler(client *Client, u *UpdateConnectionState) error {
	state := strings.TrimPrefix(u.State.GetType(), "connectionState")
	c.Logger.Info("Connection state changed", "state", state)
	return nil
}

func (c *Client) messageSendSucceededHandler(client *Client, u *UpdateMessageSendSucceeded) error {
	key := fmt.Sprintf("%d:%d", u.Message.ChatId, u.OldMessageId)
	if ch, ok := c.pendingMessages.Load(key); ok {
		ch.(chan TlObject) <- u
		c.pendingMessages.Delete(key)
	}
	return nil
}

func (c *Client) messageSendFailedHandler(client *Client, u *UpdateMessageSendFailed) error {
	key := fmt.Sprintf("%d:%d", u.Message.ChatId, u.OldMessageId)
	if ch, ok := c.pendingMessages.Load(key); ok {
		ch.(chan TlObject) <- u
		c.pendingMessages.Delete(key)
	}
	if u.Message.Id != 0 {
		go func() {
			_ = c.DeleteMessages(u.Message.ChatId, []int64{u.Message.Id}, &DeleteMessagesOpts{Revoke: false})
		}()
	}
	return nil
}

// Send dispatches req to TDLib and waits for the response.
func (c *Client) Send(req TlObject) (TlObject, error) {
	return c.SendWithContext(context.Background(), req)
}

// SendWithContext dispatches req to TDLib and waits for the response, honouring ctx.
func (c *Client) SendWithContext(ctx context.Context, req TlObject) (TlObject, error) {
	reqType := strings.ToLower(req.GetType())

	isChatAttemptedLoad := reqType == "getchat"
	isMessageAttemptedLoad := reqType == "getmessage" || reqType == "getmessagelocally" ||
		reqType == "getrepliedmessage" || reqType == "getcallbackquerymessage"

	fn, isFn := req.(tlFunction)

	for {
		var extra string
		if isFn {
			extra = strconv.FormatUint(c.requestID.Add(1), 10)
			fn.setExtra(extra)
		}

		sendData, err := json.Marshal(req)
		if err != nil {
			return nil, err
		}

		var ch chan TlObject
		if isFn {
			ch = make(chan TlObject, 1)
			c.pendingRequests.Store(extra, ch)
		}

		tdjson.SendBytes(c.clientID, sendData)

		if !isFn {
			return nil, nil
		}

		var result TlObject

		select {
		case res := <-ch:
			result = res
		case <-time.After(30 * time.Second):
			c.pendingRequests.Delete(extra)
			go func() { <-ch }()
			return nil, SendTimeout
		case <-ctx.Done():
			c.pendingRequests.Delete(extra)
			go func() { <-ch }()
			return nil, ctx.Err()
		}

		errObj, isErr := result.(*Error)
		if !isErr {
			return result, nil
		}

		if c.handleAutoRetry(req, errObj, &isChatAttemptedLoad, &isMessageAttemptedLoad) {
			continue
		}

		return nil, errObj
	}
}

// handleAutoRetry decides whether to retry after a TDLib error.
func (c *Client) handleAutoRetry(req TlObject, errObj *Error, isChatAttemptedLoad, isMessageAttemptedLoad *bool) bool {
	if c.config.AutoRetry == nil {
		return false
	}

	if errObj.Code == 429 && c.config.AutoRetry.MaxFloodWait > 0 {
		prefix := "Too Many Requests: retry after "
		if strings.HasPrefix(errObj.Message, prefix) {
			seconds, err := strconv.Atoi(strings.TrimPrefix(errObj.Message, prefix))
			if err == nil {
				waitTime := time.Duration(seconds) * time.Second
				if waitTime <= c.config.AutoRetry.MaxFloodWait {
					c.Logger.Info("Flood wait", "seconds", seconds)
					time.Sleep(waitTime)
					return true
				}
			}
		}
	}

	if errObj.Code != 400 {
		return false
	}

	if !*isMessageAttemptedLoad && errObj.Message == "Message not found" && c.config.AutoRetry.MessageNotFound {
		*isMessageAttemptedLoad = true
		chatId, messageId := extractChatAndMessageID(req)
		if chatId != 0 && messageId != 0 {
			c.Logger.Debug("Attempting to load message", "chat_id", chatId, "message_id", messageId)
			msg, loadErr := c.GetMessage(chatId, messageId)
			if loadErr == nil && msg != nil {
				c.Logger.Debug("Successfully loaded message, retrying request", "chat_id", chatId, "message_id", messageId)
				return true
			}
			c.Logger.Debug("Failed to load message", "chat_id", chatId, "message_id", messageId, "error", loadErr)
		}
	}

	if !*isChatAttemptedLoad && errObj.Message == "Chat not found" && c.config.AutoRetry.ChatNotFound {
		*isChatAttemptedLoad = true
		chatId := extractChatID(req)
		if chatId != 0 {
			c.Logger.Debug("Attempting to load chat", "chat_id", chatId)
			chat, loadErr := c.GetChat(chatId)
			if loadErr == nil && chat != nil {
				c.Logger.Debug("Successfully loaded chat, retrying request", "chat_id", chatId)
				if replyToMessageId := extractReplyToMessageID(req); replyToMessageId > 0 {
					_, _ = c.GetMessage(chatId, replyToMessageId)
				}
				return true
			}
			c.Logger.Debug("Failed to load chat", "chat_id", chatId, "error", loadErr)
		}
	}
	return false
}

func extractChatID(req TlObject) int64 {
	switch v := req.(type) {
	case *GetChat:
		return v.ChatId
	case *GetMessage:
		return v.ChatId
	case *SendMessage:
		return v.ChatId
	case *EditMessageText:
		return v.ChatId
	case *EditMessageCaption:
		return v.ChatId
	case *EditMessageReplyMarkup:
		return v.ChatId
	case *DeleteMessages:
		return v.ChatId
	case *ForwardMessages:
		return v.ChatId
	default:
		data, err := json.Marshal(req)
		if err != nil {
			return 0
		}
		var reqMap map[string]interface{}
		if err := json.Unmarshal(data, &reqMap); err != nil {
			return 0
		}
		if cId, ok := reqMap["chat_id"].(float64); ok {
			return int64(cId)
		}
		return 0
	}
}

func extractChatAndMessageID(req TlObject) (int64, int64) {
	switch v := req.(type) {
	case *GetMessage:
		return v.ChatId, v.MessageId
	case *GetMessageLocally:
		return v.ChatId, v.MessageId
	case *GetRepliedMessage:
		return v.ChatId, v.MessageId
	case *GetCallbackQueryMessage:
		return v.ChatId, v.MessageId
	default:
		data, err := json.Marshal(req)
		if err != nil {
			return 0, 0
		}
		var reqMap map[string]interface{}
		if err := json.Unmarshal(data, &reqMap); err != nil {
			return 0, 0
		}
		var chatId, messageId int64
		if cId, ok := reqMap["chat_id"].(float64); ok {
			chatId = int64(cId)
		}
		if mId, ok := reqMap["message_id"].(float64); ok {
			messageId = int64(mId)
		}
		return chatId, messageId
	}
}

func extractReplyToMessageID(req TlObject) int64 {
	data, err := json.Marshal(req)
	if err != nil {
		return 0
	}
	var reqMap map[string]interface{}
	if err := json.Unmarshal(data, &reqMap); err != nil {
		return 0
	}
	if replyToMap, ok := reqMap["reply_to"].(map[string]interface{}); ok {
		if mId, ok := replyToMap["message_id"].(float64); ok {
			return int64(mId)
		}
	}
	return 0
}

// waitMessage waits for the message to be sent and returns the final message.
func (c *Client) waitMessage(msg *Message) (*Message, error) {
	if _, ok := msg.SendingState.(*MessageSendingStatePending); !ok {
		return msg, nil
	}

	key := fmt.Sprintf("%d:%d", msg.ChatId, msg.Id)
	ch := make(chan TlObject, 1)

	c.pendingMessages.Store(key, ch)
	defer c.pendingMessages.Delete(key)

	select {
	case res := <-ch:
		if errObj, ok := res.(*Error); ok {
			return nil, errObj
		}
		if u, ok := res.(*UpdateMessageSendFailed); ok {
			return u.Message, u.Error
		}
		if finalMsg, ok := res.(*Message); ok {
			return finalMsg, nil
		}
		if u, ok := res.(*UpdateMessageSendSucceeded); ok {
			return u.Message, nil
		}
		return nil, fmt.Errorf("unexpected response type from waiter: %T", res)
	case <-time.After(30 * time.Second):
		return msg, nil
	}
}

// waitMessages waits for all messages in the album to be sent and returns the final messages.
func (c *Client) waitMessages(msgs *Messages) (*Messages, error) {
	if msgs == nil || len(msgs.Messages) == 0 {
		return msgs, nil
	}

	totalCount := len(msgs.Messages)
	type result struct {
		res TlObject
		idx int
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	resChan := make(chan result, totalCount)
	entries := make([]string, totalCount)

	for i := range msgs.Messages {
		msg := &msgs.Messages[i]
		if _, ok := msg.SendingState.(*MessageSendingStatePending); !ok {
			resChan <- result{res: msg, idx: i}
			continue
		}

		key := fmt.Sprintf("%d:%d", msg.ChatId, msg.Id)
		entries[i] = key
		ch := make(chan TlObject, 1)
		c.pendingMessages.Store(key, ch)

		go func(idx int, cch chan TlObject) {
			select {
			case r := <-cch:
				resChan <- result{res: r, idx: idx}
			case <-ctx.Done():
			}
		}(i, ch)
	}

	defer func() {
		for _, key := range entries {
			if key != "" {
				c.pendingMessages.Delete(key)
			}
		}
	}()

	errs := make([]error, totalCount)
	receivedCount := 0

	for receivedCount < totalCount {
		select {
		case item := <-resChan:
			res := item.res
			resIdx := item.idx
			if errObj, ok := res.(*Error); ok {
				errs[resIdx] = errObj
			} else if u, ok := res.(*UpdateMessageSendFailed); ok {
				errs[resIdx] = u.Error
				if u.Message != nil {
					msgs.Messages[resIdx] = *u.Message
				}
			} else if finalMsg, ok := res.(*Message); ok {
				msgs.Messages[resIdx] = *finalMsg
			} else if u, ok := res.(*UpdateMessageSendSucceeded); ok {
				if u.Message != nil {
					msgs.Messages[resIdx] = *u.Message
				}
			}
			receivedCount++
		case <-ctx.Done():
			return msgs, errors.Join(errs...)
		}
	}

	return msgs, errors.Join(errs...)
}

func toOptionValue(v interface{}) OptionValue {
	switch val := v.(type) {
	case bool:
		return &OptionValueBoolean{Value: val}
	case int:
		return &OptionValueInteger{Value: int64(val)}
	case int32:
		return &OptionValueInteger{Value: int64(val)}
	case int64:
		return &OptionValueInteger{Value: val}
	case string:
		return &OptionValueString{Value: val}
	case nil:
		return &OptionValueEmpty{}
	default:
		return nil
	}
}

func Bool(b bool) *bool {
	return &b
}

type handlersData struct {
	handlers map[int][]Handler
	groups   []int
}

type Waiter struct {
	Filter func(client *Client, update TlObject) bool
	C      chan TlObject
	ChatId int64
}

// WaitFor registers a waiter and blocks until a matching update arrives or timeout occurs.
func (c *Client) WaitFor(filter func(client *Client, update TlObject) bool, timeout time.Duration) (TlObject, error) {
	return c.WaitForChat(0, filter, timeout)
}

// WaitForContext registers a waiter and blocks until a matching update arrives,
// timeout occurs, or ctx is cancelled.
func (c *Client) WaitForContext(ctx context.Context, chatId int64, filter func(client *Client, update TlObject) bool, timeout time.Duration) (TlObject, error) {
	ch := make(chan TlObject, 1)
	idNum := c.waiterCount.Add(1)
	id := fmt.Sprintf("%d", idNum)

	c.wMu.Lock()
	if c.waiters[chatId] == nil {
		c.waiters[chatId] = make(map[string]*Waiter)
	}
	c.waiters[chatId][id] = &Waiter{Filter: filter, C: ch, ChatId: chatId}
	c.wMu.Unlock()

	defer func() {
		c.wMu.Lock()
		delete(c.waiters[chatId], id)
		if len(c.waiters[chatId]) == 0 {
			delete(c.waiters, chatId)
		}
		c.wMu.Unlock()
	}()

	select {
	case u := <-ch:
		return u, nil
	case <-time.After(timeout):
		return nil, ConversationTimeout
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// WaitForChat registers a waiter for a specific chat and blocks until a matching
// update arrives or timeout occurs.
func (c *Client) WaitForChat(chatId int64, filter func(client *Client, update TlObject) bool, timeout time.Duration) (TlObject, error) {
	return c.WaitForContext(context.Background(), chatId, filter, timeout)
}
