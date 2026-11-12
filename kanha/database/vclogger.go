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
	"fmt"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
)

type vcLoggerDoc struct {
	ChatID  int64 `bson:"chat_id"`
	ID      int64 `bson:"_id,omitempty"`
	Enabled bool  `bson:"enabled"`
}

// IsVCLoggerEnabled returns whether VC Logger is enabled for the chat (defaults to true).
func IsVCLoggerEnabled(chatID int64) (bool, error) {
	ctx, cancel := ctx()
	defer cancel()

	var doc vcLoggerDoc
	err := vcLoggerColl.FindOne(ctx, bson.M{
		"$or": []bson.M{
			{"chat_id": chatID},
			{"_id": chatID},
		},
	}).Decode(&doc)

	if err == mongo.ErrNoDocuments {
		return true, nil // default ON
	}
	if err != nil {
		return true, fmt.Errorf("failed to get vclogger status for %d: %w", chatID, err)
	}

	return doc.Enabled, nil
}

// SetVCLoggerStatus sets the VC Logger enabled state for the chat.
func SetVCLoggerStatus(chatID int64, enabled bool) error {
	ctx, cancel := ctx()
	defer cancel()

	_, err := vcLoggerColl.UpdateOne(
		ctx,
		bson.M{
			"$or": []bson.M{
				{"chat_id": chatID},
				{"_id": chatID},
			},
		},
		bson.M{
			"$set": bson.M{
				"chat_id": chatID,
				"enabled": enabled,
			},
		},
		upsertOpt,
	)
	if err != nil {
		return fmt.Errorf("failed to set vclogger status for %d: %w", chatID, err)
	}
	return nil
}

// GetEnabledVCLoggerChats returns all chats where VC logger is enabled.
func GetEnabledVCLoggerChats() ([]int64, error) {
	ctx, cancel := ctx()
	defer cancel()

	cursor, err := vcLoggerColl.Find(ctx, bson.M{"enabled": true})
	if err != nil {
		return nil, fmt.Errorf("failed to find enabled vclogger chats: %w", err)
	}
	defer cursor.Close(ctx)

	var chatIDs []int64
	for cursor.Next(ctx) {
		var doc vcLoggerDoc
		if err := cursor.Decode(&doc); err == nil {
			id := doc.ChatID
			if id == 0 {
				id = doc.ID
			}
			if id != 0 {
				chatIDs = append(chatIDs, id)
			}
		}
	}
	return chatIDs, nil
}
