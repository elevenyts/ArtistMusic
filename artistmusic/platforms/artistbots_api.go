/*
 * ● ArtistMusic
 * ○ A high-performance engine for streaming music in Telegram voicechats.
 *
 * Copyright (C) 2026 Kanha
 * Copyright (C) 2026 ArtistMusic
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 * Repository: https://github.com/elevenyts/ArtistMusic
 */

package platforms

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"ArtistMusic/config"
	state "ArtistMusic/artistmusic/core/models"
	"ArtistMusic/artistmusic/logger"

	td "github.com/ArtistMusic/Artist"
)

// PlatformArtistbotsApi downloads YouTube tracks through the Artistbots API:
//
//	GET {ARTISTBOTS_API_URL}/download?url=VIDEO_ID&type=audio|video&api_key=KEY
//
// The endpoint answers with JSON carrying a download link (download_url); the
// file is then fetched from that link. If the endpoint streams the media
// directly instead, the body is saved as-is.
const PlatformArtistbotsApi state.PlatformName = "ArtistbotsApi"

var artistbotsHTTP = &http.Client{}

type ArtistbotsApiPlatform struct{}

func init() {
	Register(&ArtistbotsApiPlatform{})
}

func (a *ArtistbotsApiPlatform) Name() state.PlatformName { return PlatformArtistbotsApi }

// Priority 88: tried before ArtistApi (85) and yt-dlp (60) for YouTube tracks.
func (a *ArtistbotsApiPlatform) Priority() int { return 88 }

func (a *ArtistbotsApiPlatform) CanGet(_ string) bool { return false }

func (a *ArtistbotsApiPlatform) Get(_ string, _ bool) ([]*state.Track, error) {
	return nil, errors.New("artistbotsapi platform does not support search")
}

func (a *ArtistbotsApiPlatform) CanDownload(source state.PlatformName) bool {
	if config.ArtistbotsAPIURL == "" || config.ArtistbotsAPIKey == "" {
		return false
	}
	return source == PlatformYouTube
}

func (a *ArtistbotsApiPlatform) Download(
	ctx context.Context,
	track *state.Track,
	_ *td.Message,
) (string, error) {
	if p := findFile(track); p != "" {
		logger.Debug("ArtistbotsApi: cache hit " + p)
		return p, nil
	}

	if track.ID == "" {
		return "", errors.New("artistbotsapi: missing video id")
	}

	dtype, ext, timeout := "audio", ".mp3", audioDownloadTimeout
	if track.Video {
		dtype, ext, timeout = "video", ".mp4", videoDownloadTimeout
	}

	dctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	path := getPath(track, ext)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return "", errors.New("artistbotsapi: cannot create downloads dir")
	}

	fail := func(err error) (string, error) {
		os.Remove(path)
		if ctx.Err() != nil {
			return "", ctx.Err() // cancelled by the caller
		}
		if dctx.Err() != nil {
			return "", errors.New("artistbotsapi: request timed out")
		}
		return "", scrubArtistbotsErr(err)
	}

	base := strings.TrimRight(config.ArtistbotsAPIURL, "/")
	if !strings.HasSuffix(base, "/download") {
		base += "/download"
	}
	q := url.Values{}
	q.Set("url", track.ID)
	q.Set("type", dtype)
	q.Set("api_key", config.ArtistbotsAPIKey)

	resp, err := artistbotsGet(dctx, base+"?"+q.Encode())
	if err != nil {
		return fail(fmt.Errorf("artistbotsapi request failed: %w", err))
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fail(fmt.Errorf("artistbotsapi returned %d", resp.StatusCode))
	}

	ct := strings.ToLower(resp.Header.Get("Content-Type"))
	body := io.Reader(resp.Body)

	if strings.Contains(ct, "json") || strings.HasPrefix(ct, "text/") {
		raw, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		if err != nil {
			return fail(fmt.Errorf("artistbotsapi read failed: %w", err))
		}

		link, err := parseArtistbotsLink(raw, config.ArtistbotsAPIURL)
		if err != nil {
			return fail(err)
		}

		resp2, err := artistbotsGet(dctx, link)
		if err != nil {
			return fail(fmt.Errorf("artistbotsapi file request failed: %w", err))
		}
		defer resp2.Body.Close()

		if resp2.StatusCode >= 400 {
			return fail(fmt.Errorf("artistbotsapi file returned %d", resp2.StatusCode))
		}
		body = resp2.Body
	}

	out, err := os.Create(path)
	if err != nil {
		return fail(errors.New("artistbotsapi: cannot create file"))
	}
	if _, err := io.Copy(out, body); err != nil {
		out.Close()
		return fail(fmt.Errorf("artistbotsapi download failed: %w", err))
	}
	if err := out.Close(); err != nil {
		return fail(errors.New("artistbotsapi: cannot write file"))
	}

	info, statErr := os.Stat(path)
	if statErr != nil || info.Size() < minValidDownloadBytes {
		return fail(errors.New("artistbotsapi returned an invalid or empty file"))
	}

	return path, nil
}

func artistbotsGet(ctx context.Context, rawURL string) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	return artistbotsHTTP.Do(req)
}

// parseArtistbotsLink extracts the download link from the API's JSON reply.
func parseArtistbotsLink(raw []byte, apiBase string) (string, error) {
	var m map[string]any
	if err := json.Unmarshal(raw, &m); err != nil {
		return "", errors.New("artistbotsapi: unexpected response")
	}

	if ok, has := m["success"].(bool); has && !ok {
		return "", errors.New("artistbotsapi: request rejected")
	}
	if st, has := m["status"].(string); has {
		switch strings.ToLower(st) {
		case "error", "failed", "fail":
			return "", errors.New("artistbotsapi: request failed")
		}
	}

	pick := func(mm map[string]any) string {
		for _, k := range []string{"download_url", "url", "link", "stream_url"} {
			if s, ok := mm[k].(string); ok && strings.TrimSpace(s) != "" {
				return strings.TrimSpace(s)
			}
		}
		return ""
	}

	link := pick(m)
	if link == "" {
		if data, ok := m["data"].(map[string]any); ok {
			link = pick(data)
		}
	}
	if link == "" {
		return "", errors.New("artistbotsapi: no download link in response")
	}

	if strings.HasPrefix(link, "/") {
		link = strings.TrimRight(apiBase, "/") + link
	}

	safe, err := sanitizeMediaURL(link)
	if err != nil {
		return "", errors.New("artistbotsapi: unsafe download link")
	}
	return safe, nil
}

// scrubArtistbotsErr removes the API key and base URL from an error message.
func scrubArtistbotsErr(err error) error {
	if err == nil {
		return nil
	}
	msg := err.Error()
	for _, s := range []string{
		config.ArtistbotsAPIKey,
		url.QueryEscape(config.ArtistbotsAPIKey),
		config.ArtistbotsAPIURL,
	} {
		if s != "" {
			msg = strings.ReplaceAll(msg, s, "***")
		}
	}
	return errors.New(msg)
}
