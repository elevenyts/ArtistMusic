/*
 * ● KanhaMusic
 * ○ A high-performance engine for streaming music in Telegram voicechats.
 *
 * Copyright (C) 2026 Kanha
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 * Repository: https://github.com/Oyekanhaa/KanhaMusic
 */

package modules

import (
	"strconv"
	"strings"

	td "github.com/Kanha/Meow"

	state "KanhaMusic/kanha/core/models"
	"KanhaMusic/kanha/database"
	"KanhaMusic/kanha/locales"
	"KanhaMusic/kanha/platforms"
	"KanhaMusic/kanha/utils"
)

// playlistIDPrefix marks a /play query as a saved playlist ID rather than
// a search term or URL.
const playlistIDPrefix = "tgpl_"

const maxPlaylistNameLen = 40

func init() {
	helpTexts["/createplaylist"] = `<i>Create a new personal playlist.</i>

<u>Usage:</u>
<b>/createplaylist [name]</b> — Create a playlist with the given name

<b>💡 Notes:</b>
• Up to 10 playlists per user
• Names longer than 40 characters are trimmed`

	helpTexts["/deleteplaylist"] = `<i>Delete one of your playlists.</i>

<u>Usage:</u>
<b>/deleteplaylist [playlist id]</b>`

	helpTexts["/addtoplaylist"] = `<i>Add a track to one of your playlists.</i>

<u>Usage:</u>
<b>/addtoplaylist [playlist id] [song name or URL]</b>`

	helpTexts["/removefromplaylist"] = `<i>Remove a track from one of your playlists.</i>

<u>Usage:</u>
<b>/removefromplaylist [playlist id] [song number or url]</b>`

	helpTexts["/playlistinfo"] = `<i>Show the tracks saved in a playlist.</i>

<u>Usage:</u>
<b>/playlistinfo [playlist id]</b>`

	helpTexts["/myplaylists"] = `<i>List all of your saved playlists.</i>

<u>Usage:</u>
<b>/myplaylists</b>`
}

func createPlaylistHandler(c *td.Client, m *td.Message) error {
	chatID := m.ChatID()
	userID := m.SenderID()

	name := m.Args()
	if name == "" {
		_, err := m.ReplyText(c, F(chatID, "playlist_usage_create", locales.Arg{"cmd": getCommand(m)}), nil)
		return err
	}

	limitReached, err := database.UserPlaylistLimitReached(userID)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_fetch_fail"), nil)
		return err
	}
	if limitReached {
		_, err := m.ReplyText(c, F(chatID, "playlist_limit_reached"), nil)
		return err
	}

	if runes := []rune(name); len(runes) > maxPlaylistNameLen {
		name = string(runes[:maxPlaylistNameLen])
	}

	playlistID, err := database.CreatePlaylist(name, userID)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_create_fail", locales.Arg{"error": err.Error()}), nil)
		return err
	}

	_, err = m.ReplyText(c, F(chatID, "playlist_create_success", locales.Arg{
		"name": utils.EscapeHTML(name),
		"id":   playlistID,
	}), &td.SendTextMessageOpts{ParseMode: "HTML"})
	return err
}

func deletePlaylistHandler(c *td.Client, m *td.Message) error {
	chatID := m.ChatID()
	userID := m.SenderID()

	id := m.Args()
	if id == "" {
		_, err := m.ReplyText(c, F(chatID, "playlist_usage_delete", locales.Arg{"cmd": getCommand(m)}), nil)
		return err
	}

	playlist, err := database.GetPlaylist(id)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_found"), nil)
		return err
	}
	if playlist.UserID != userID {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_owner"), nil)
		return err
	}

	if err := database.DeletePlaylist(id, userID); err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_delete_fail", locales.Arg{"error": err.Error()}), nil)
		return err
	}

	_, err = m.ReplyText(c, F(chatID, "playlist_delete_success", locales.Arg{
		"name": utils.EscapeHTML(playlist.Name),
	}), &td.SendTextMessageOpts{ParseMode: "HTML"})
	return err
}

func addToPlaylistHandler(c *td.Client, m *td.Message) error {
	chatID := m.ChatID()
	userID := m.SenderID()

	args := strings.SplitN(m.Args(), " ", 2)
	if len(args) != 2 || args[1] == "" {
		_, err := m.ReplyText(c, F(chatID, "playlist_usage_add", locales.Arg{"cmd": getCommand(m)}), nil)
		return err
	}
	playlistID, query := args[0], args[1]

	playlist, err := database.GetPlaylist(playlistID)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_found"), nil)
		return err
	}
	if playlist.UserID != userID {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_owner"), nil)
		return err
	}

	tracks, err := platforms.ResolveQuery(query, false)
	if err != nil || len(tracks) == 0 {
		_, err := m.ReplyText(c, F(chatID, "playlist_invalid_query"), nil)
		return err
	}
	track := tracks[0]

	song := database.PlaylistSong{
		URL:      track.URL,
		Name:     track.Title,
		TrackID:  track.ID,
		Duration: track.Duration,
		Platform: string(track.Source),
	}

	if err := database.AddSongToPlaylist(playlistID, song); err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_add_fail", locales.Arg{"error": err.Error()}), nil)
		return err
	}

	_, err = m.ReplyText(c, F(chatID, "playlist_add_success", locales.Arg{
		"song":     utils.EscapeHTML(song.Name),
		"playlist": utils.EscapeHTML(playlist.Name),
	}), &td.SendTextMessageOpts{ParseMode: "HTML"})
	return err
}

func removeFromPlaylistHandler(c *td.Client, m *td.Message) error {
	chatID := m.ChatID()
	userID := m.SenderID()

	args := strings.SplitN(m.Args(), " ", 2)
	if len(args) != 2 || args[1] == "" {
		_, err := m.ReplyText(c, F(chatID, "playlist_usage_remove", locales.Arg{"cmd": getCommand(m)}), nil)
		return err
	}
	playlistID, songIdentifier := args[0], args[1]

	playlist, err := database.GetPlaylist(playlistID)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_found"), nil)
		return err
	}
	if playlist.UserID != userID {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_owner"), nil)
		return err
	}

	var trackID string
	if songIndex, err := strconv.Atoi(songIdentifier); err == nil {
		if songIndex < 1 || songIndex > len(playlist.Songs) {
			_, err := m.ReplyText(c, F(chatID, "playlist_invalid_song_number"), nil)
			return err
		}
		trackID = playlist.Songs[songIndex-1].TrackID
	} else {
		for _, song := range playlist.Songs {
			if song.URL == songIdentifier || song.TrackID == songIdentifier {
				trackID = song.TrackID
				break
			}
		}
	}

	if trackID == "" {
		_, err := m.ReplyText(c, F(chatID, "playlist_song_not_found"), nil)
		return err
	}

	if err := database.RemoveSongFromPlaylist(playlistID, trackID); err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_remove_fail", locales.Arg{"error": err.Error()}), nil)
		return err
	}

	_, err = m.ReplyText(c, F(chatID, "playlist_remove_success", locales.Arg{
		"name": utils.EscapeHTML(playlist.Name),
	}), &td.SendTextMessageOpts{ParseMode: "HTML"})
	return err
}

func playlistInfoHandler(c *td.Client, m *td.Message) error {
	chatID := m.ChatID()

	id := m.Args()
	if id == "" {
		_, err := m.ReplyText(c, F(chatID, "playlist_usage_info", locales.Arg{"cmd": getCommand(m)}), nil)
		return err
	}

	playlist, err := database.GetPlaylist(id)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_not_found"), nil)
		return err
	}

	owner, err := c.GetUser(playlist.UserID)
	ownerName := "Unknown"
	if err == nil && owner != nil {
		ownerName = owner.FirstName
	}

	songsText := F(chatID, "playlist_songs_empty")
	if len(playlist.Songs) > 0 {
		lines := make([]string, 0, len(playlist.Songs))
		for i, song := range playlist.Songs {
			lines = append(lines, F(chatID, "playlist_song_line", locales.Arg{
				"index": i + 1,
				"name":  utils.EscapeHTML(song.Name),
				"url":   song.URL,
			}))
		}
		songsText = strings.Join(lines, "\n")
	}

	_, err = m.ReplyText(c, F(chatID, "playlist_info", locales.Arg{
		"name":  utils.EscapeHTML(playlist.Name),
		"owner": utils.EscapeHTML(ownerName),
		"count": len(playlist.Songs),
		"songs": songsText,
	}), &td.SendTextMessageOpts{ParseMode: "HTML", DisableWebPagePreview: true})
	return err
}

func myPlaylistsHandler(c *td.Client, m *td.Message) error {
	chatID := m.ChatID()
	userID := m.SenderID()

	playlists, err := database.GetUserPlaylists(userID)
	if err != nil {
		_, err := m.ReplyText(c, F(chatID, "playlist_fetch_fail"), nil)
		return err
	}
	if len(playlists) == 0 {
		_, err := m.ReplyText(c, F(chatID, "playlist_none"), nil)
		return err
	}

	lines := make([]string, 0, len(playlists))
	for _, playlist := range playlists {
		lines = append(lines, F(chatID, "playlist_list_line", locales.Arg{
			"name": utils.EscapeHTML(playlist.Name),
			"id":   playlist.ID,
		}))
	}

	_, err = m.ReplyText(c, F(chatID, "playlist_list", locales.Arg{
		"playlists": strings.Join(lines, "\n"),
	}), &td.SendTextMessageOpts{ParseMode: "HTML"})
	return err
}

// isPlaylistQuery reports whether a /play query refers to a saved playlist.
func isPlaylistQuery(query string) bool {
	return strings.HasPrefix(query, playlistIDPrefix)
}

// playlistTracks loads every song saved in the given playlist as playable
// tracks, for /play [playlist id] to queue in one go.
func playlistTracks(id string) ([]*state.Track, error) {
	playlist, err := database.GetPlaylist(id)
	if err != nil {
		return nil, err
	}

	tracks := make([]*state.Track, 0, len(playlist.Songs))
	for _, song := range playlist.Songs {
		tracks = append(tracks, &state.Track{
			ID:       song.TrackID,
			Title:    song.Name,
			Duration: song.Duration,
			URL:      song.URL,
			Source:   state.PlatformName(song.Platform),
		})
	}
	return tracks, nil
}
