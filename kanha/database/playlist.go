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

package database

import (
	"context"
	"crypto/rand"
	"fmt"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
)

const maxPlaylistsPerUser = 10

// PlaylistSong represents a single track saved inside a playlist.
type PlaylistSong struct {
	URL      string `bson:"url"`
	Name     string `bson:"name"`
	TrackID  string `bson:"track_id"`
	Duration int    `bson:"duration"`
	Platform string `bson:"platform"`
}

// Playlist represents a user's saved playlist.
type Playlist struct {
	ID     string         `bson:"_id"`
	Name   string         `bson:"name"`
	UserID int64          `bson:"user_id"`
	Songs  []PlaylistSong `bson:"songs"`
}

// generatePlaylistID returns a short, unique-enough playlist ID.
// Playlist IDs are prefixed with "tgpl_" so /play can detect a playlist
// ID vs. a normal search query/URL.
func generatePlaylistID() string {
	b := make([]byte, 5)
	_, _ = rand.Read(b)
	return fmt.Sprintf("tgpl_%x", b)
}

// CreatePlaylist creates a new playlist for a user and returns its ID.
func CreatePlaylist(name string, userID int64) (string, error) {
	ctx, cancel := ctx()
	defer cancel()

	id := generatePlaylistID()
	playlist := Playlist{
		ID:     id,
		Name:   name,
		UserID: userID,
		Songs:  []PlaylistSong{},
	}
	if _, err := playlistColl.InsertOne(ctx, playlist); err != nil {
		return "", err
	}
	return id, nil
}

// GetPlaylist retrieves a playlist by its ID.
func GetPlaylist(id string) (*Playlist, error) {
	dbCtx, cancel := ctx()
	defer cancel()

	var playlist Playlist
	if err := playlistColl.FindOne(dbCtx, bson.M{"_id": id}).Decode(&playlist); err != nil {
		return nil, err
	}
	return &playlist, nil
}

// DeletePlaylist deletes a playlist by its ID, scoped to its owner.
func DeletePlaylist(id string, userID int64) error {
	dbCtx, cancel := ctx()
	defer cancel()

	_, err := playlistColl.DeleteOne(dbCtx, bson.M{"_id": id, "user_id": userID})
	return err
}

func playlistSongExists(id, trackID string) bool {
	dbCtx, cancel := ctx()
	defer cancel()

	var playlist Playlist
	if err := playlistColl.FindOne(dbCtx, bson.M{"_id": id}).Decode(&playlist); err != nil {
		return false
	}
	for _, song := range playlist.Songs {
		if song.TrackID == trackID {
			return true
		}
	}
	return false
}

// AddSongToPlaylist appends a song to a playlist. It is a no-op if the
// track is already present.
func AddSongToPlaylist(id string, song PlaylistSong) error {
	if playlistSongExists(id, song.TrackID) {
		return nil
	}

	dbCtx, cancel := ctx()
	defer cancel()

	_, err := playlistColl.UpdateOne(
		dbCtx,
		bson.M{"_id": id},
		bson.M{"$push": bson.M{"songs": song}},
	)
	return err
}

// RemoveSongFromPlaylist removes a song from a playlist by its track ID.
func RemoveSongFromPlaylist(id, trackID string) error {
	if !playlistSongExists(id, trackID) {
		return fmt.Errorf("track with ID %s not found in playlist", trackID)
	}

	dbCtx, cancel := ctx()
	defer cancel()

	_, err := playlistColl.UpdateOne(
		dbCtx,
		bson.M{"_id": id},
		bson.M{"$pull": bson.M{"songs": bson.M{"track_id": trackID}}},
	)
	if err != nil {
		return fmt.Errorf("error removing song: %w", err)
	}
	return nil
}

// GetUserPlaylists returns every playlist owned by a user.
func GetUserPlaylists(userID int64) ([]Playlist, error) {
	dbCtx, cancel := ctx()
	defer cancel()

	var playlists []Playlist
	cursor, err := playlistColl.Find(dbCtx, bson.M{"user_id": userID})
	if err != nil {
		return nil, err
	}
	defer func(cursor *mongo.Cursor, ctx context.Context) {
		_ = cursor.Close(ctx)
	}(cursor, dbCtx)

	for cursor.Next(dbCtx) {
		var playlist Playlist
		if err := cursor.Decode(&playlist); err != nil {
			return nil, err
		}
		playlists = append(playlists, playlist)
	}
	return playlists, nil
}

// UserPlaylistLimitReached reports whether the user has hit the max
// number of playlists they're allowed to create.
func UserPlaylistLimitReached(userID int64) (bool, error) {
	playlists, err := GetUserPlaylists(userID)
	if err != nil {
		return false, err
	}
	return len(playlists) >= maxPlaylistsPerUser, nil
}
