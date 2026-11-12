package gotdbot

import (
	"log/slog"
	"os"
	"runtime"
	"time"

	"github.com/Kanha/Meow/logger"
)

type AutoRetry struct {
	ChatNotFound    bool
	MessageNotFound bool
	MaxFloodWait    time.Duration
}

type ClientOpts struct {
	PanicHandler func(client *Client, update TlObject, r interface{})
	ErrorHandler func(client *Client, update TlObject, err error) error

	LibraryPath             string
	UseTestDC               bool
	DatabaseDirectory       string
	FilesDirectory          string
	DatabaseEncryptionKey   string
	UseFileDatabase         *bool
	UseChatInfoDatabase     *bool
	UseMessageDatabase      *bool
	UseSecretChats          bool
	LoadMessagesBeforeReply bool
	SystemLanguageCode      string
	DeviceModel             string
	SystemVersion           string
	ApplicationVersion      string
	TDLibOptions            *TDLibOptions
	Logger                  *logger.Logger
	QrMode                  bool
	AuthorizationTimeout    time.Duration
	LogVerbosityLevel       int32
	LogStream               LogStream
	AutoRetry               *AutoRetry
	ParseMode               string
}

// TDLibOptions contains TDLib options that can be set
type TDLibOptions struct {
	// If true, text entities will be automatically parsed in all inputMessageText objects
	AlwaysParseMarkdown bool `json:"always_parse_markdown,omitempty"`
	// If true, animated emoji will be disabled and shown as plain emoji
	DisableAnimatedEmoji bool `json:"disable_animated_emoji,omitempty"`
	// If true, notifications about the user's contacts who have joined Telegram will be disabled. User will still receive the corresponding message in the private chat. getOption needs to be called explicitly to fetch the latest value of the option, changed from another device
	DisableContactRegisteredNotifications bool `json:"disable_contact_registered_notifications,omitempty"`
	// Since TDLib 1.8.24. If true, then network statistics will be completely disabled
	DisableNetworkStatistics bool `json:"disable_network_statistics,omitempty"`
	// If true, persistent network statistics will be disabled, which significantly reduces disk usage
	DisablePersistentNetworkStatistics bool `json:"disable_persistent_network_statistics,omitempty"`
	// If true, notifications about outgoing scheduled messages that were sent will be disabled
	DisableSentScheduledMessageNotifications bool `json:"disable_sent_scheduled_message_notifications,omitempty"`
	// If true, protection from external time adjustment will be disabled, which significantly reduces disk usage
	DisableTimeAdjustmentProtection bool `json:"disable_time_adjustment_protection,omitempty"`
	// If true, support for top chats and statistics collection is disabled
	DisableTopChats bool `json:"disable_top_chats,omitempty"`
	// If true, allows to skip all updates received while the TDLib instance was not running. The option does nothing if the database or secret chats are used
	IgnoreBackgroundUpdates bool `json:"ignore_background_updates,omitempty"`
	// If true, the disable_notification value specified in the request will be always used instead of the default value
	IgnoreDefaultDisableNotification bool `json:"ignore_default_disable_notification,omitempty"`
	// Since TDLib 1.8.24. If true, document file names will be ignored and numerical names will be used instead
	IgnoreFileNames bool `json:"ignore_file_names,omitempty"`
	// If true, prevents file thumbnails sent by the server along with messages from being saved on the disk
	IgnoreInlineThumbnails bool `json:"ignore_inline_thumbnails,omitempty"`
	// If true, chat and message restrictions specific to the currently used operating system will be ignored
	IgnorePlatformRestrictions bool `json:"ignore_platform_restrictions,omitempty"`
	// If true, sensitive content will be shown on all user devices. getOption needs to be called explicitly to fetch the latest value of the option, changed from another device
	IgnoreSensitiveContentRestrictions bool `json:"ignore_sensitive_content_restrictions,omitempty"`
	// TDLib 1.8.36-1.8.44. If true, added paid reactions are anonymous by default. If false, they are non-anonymous.
	IsPaidReactionAnonymous bool `json:"is_paid_reaction_anonymous,omitempty"`
	// Path to a database for storing language pack strings, so that this database can be shared between different accounts. By default, language pack strings are stored only in memory. Changes of value of this option will be applied only after TDLib restart, so it should be set before call to setTdlibParameters.
	LanguagePackDatabasePath string `json:"language_pack_database_path,omitempty"`
	// Identifier of the currently used language pack from the current localization target
	LanguagePackId string `json:"language_pack_id,omitempty"`
	// Name for the current localization target (for example, “android”, “android_x”, “ios”, “macos”, “tdesktop”, “unigram”, “web”, “webz”)
	LocalizationTarget string `json:"localization_target,omitempty"`
	// The maximum time messages are stored in memory before they are unloaded, 60-86400; in seconds. Defaults to 60 for users and 1800 for bots
	MessageUnloadDelay int64 `json:"message_unload_delay,omitempty"`
	// The maximum number of notification groups to be shown simultaneously, 0-25
	NotificationGroupCountMax int64 `json:"notification_group_count_max,omitempty"`
	// The maximum number of simultaneously shown notifications in a group, 1-25. Defaults to 10
	NotificationGroupSizeMax int64 `json:"notification_group_size_max,omitempty"`
	// Online status of the current user
	Online bool `json:"online,omitempty"`
	// If true, IPv6 addresses will be preferred over IPv4 addresses
	PreferIpv6 bool `json:"prefer_ipv6,omitempty"`
	// Since TDLib 1.8.24. If true, then all pinned messages will be treated as mentions even posted without notification of chat members
	ProcessPinnedMessagesAsMentions bool `json:"process_pinned_messages_as_mentions,omitempty"`
	// If true, Perfect Forward Secrecy will be enabled for interaction with the Telegram servers for cloud chats
	UsePfs bool `json:"use_pfs,omitempty"`
	// If true, quick acknowledgement will be enabled for outgoing messages
	UseQuickAck bool `json:"use_quick_ack,omitempty"`
	// If true, the background storage optimizer will be enabled
	UseStorageOptimizer bool `json:"use_storage_optimizer,omitempty"`
	// A UTC time offset used for splitting messages by days. The option is reset automatically on each TDLib instance launch, so it needs to be set manually only if the time offset is changed during execution.
	UtcTimeOffset int64 `json:"utc_time_offset,omitempty"`
}

// forEachSet calls fn for each non-default TDLib option.
func (o *TDLibOptions) forEachSet(fn func(name string, value interface{})) {
	if o == nil || fn == nil {
		return
	}
	if o.AlwaysParseMarkdown {
		fn("always_parse_markdown", o.AlwaysParseMarkdown)
	}
	if o.DisableAnimatedEmoji {
		fn("disable_animated_emoji", o.DisableAnimatedEmoji)
	}
	if o.DisableContactRegisteredNotifications {
		fn("disable_contact_registered_notifications", o.DisableContactRegisteredNotifications)
	}
	if o.DisableNetworkStatistics {
		fn("disable_network_statistics", o.DisableNetworkStatistics)
	}
	if o.DisablePersistentNetworkStatistics {
		fn("disable_persistent_network_statistics", o.DisablePersistentNetworkStatistics)
	}
	if o.DisableSentScheduledMessageNotifications {
		fn("disable_sent_scheduled_message_notifications", o.DisableSentScheduledMessageNotifications)
	}
	if o.DisableTimeAdjustmentProtection {
		fn("disable_time_adjustment_protection", o.DisableTimeAdjustmentProtection)
	}
	if o.DisableTopChats {
		fn("disable_top_chats", o.DisableTopChats)
	}
	if o.IgnoreBackgroundUpdates {
		fn("ignore_background_updates", o.IgnoreBackgroundUpdates)
	}
	if o.IgnoreDefaultDisableNotification {
		fn("ignore_default_disable_notification", o.IgnoreDefaultDisableNotification)
	}
	if o.IgnoreFileNames {
		fn("ignore_file_names", o.IgnoreFileNames)
	}
	if o.IgnoreInlineThumbnails {
		fn("ignore_inline_thumbnails", o.IgnoreInlineThumbnails)
	}
	if o.IgnorePlatformRestrictions {
		fn("ignore_platform_restrictions", o.IgnorePlatformRestrictions)
	}
	if o.IgnoreSensitiveContentRestrictions {
		fn("ignore_sensitive_content_restrictions", o.IgnoreSensitiveContentRestrictions)
	}
	if o.IsPaidReactionAnonymous {
		fn("is_paid_reaction_anonymous", o.IsPaidReactionAnonymous)
	}
	if o.LanguagePackDatabasePath != "" {
		fn("language_pack_database_path", o.LanguagePackDatabasePath)
	}
	if o.LanguagePackId != "" {
		fn("language_pack_id", o.LanguagePackId)
	}
	if o.LocalizationTarget != "" {
		fn("localization_target", o.LocalizationTarget)
	}
	if o.MessageUnloadDelay != 0 {
		fn("message_unload_delay", o.MessageUnloadDelay)
	}
	if o.NotificationGroupCountMax != 0 {
		fn("notification_group_count_max", o.NotificationGroupCountMax)
	}
	if o.NotificationGroupSizeMax != 0 {
		fn("notification_group_size_max", o.NotificationGroupSizeMax)
	}
	if o.Online {
		fn("online", o.Online)
	}
	if o.PreferIpv6 {
		fn("prefer_ipv6", o.PreferIpv6)
	}
	if o.ProcessPinnedMessagesAsMentions {
		fn("process_pinned_messages_as_mentions", o.ProcessPinnedMessagesAsMentions)
	}
	if o.UsePfs {
		fn("use_pfs", o.UsePfs)
	}
	if o.UseQuickAck {
		fn("use_quick_ack", o.UseQuickAck)
	}
	if o.UseStorageOptimizer {
		fn("use_storage_optimizer", o.UseStorageOptimizer)
	}
	if o.UtcTimeOffset != 0 {
		fn("utc_time_offset", o.UtcTimeOffset)
	}
}

func DefaultClientConfig() *ClientOpts {
	return &ClientOpts{
		DatabaseDirectory:       "database",
		FilesDirectory:          "",
		DatabaseEncryptionKey:   "",
		UseFileDatabase:         Bool(true),
		UseChatInfoDatabase:     Bool(true),
		UseMessageDatabase:      Bool(true),
		UseSecretChats:          false,
		LoadMessagesBeforeReply: false,
		SystemLanguageCode:      "en",
		DeviceModel:             "Gotdbot",
		SystemVersion:           runtime.GOOS,
		ApplicationVersion:      "Gotdbot " + Version,
		Logger:                  logger.New(logger.WithLevel(slog.LevelInfo), logger.WithOutput(os.Stdout)),
		QrMode:                  false,
		AuthorizationTimeout:    60 * time.Second,
		LogVerbosityLevel:       2,
		AutoRetry:               &AutoRetry{},
		ParseMode:               "",
	}
}
