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

package platforms

import (
	"KanhaMusic/config"
	state "KanhaMusic/kanha/core/models"
	"KanhaMusic/kanha/logger"
	"KanhaMusic/kanha/utils"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	td "github.com/Kanha/Meow"
)

const (
	audioDownloadTimeout = 300 * time.Second
	videoDownloadTimeout = 600 * time.Second

	minValidDownloadBytes = 10_000
)

const PlatformMeowApi state.PlatformName = "MeowApi"

type MeowApiPlatform struct{}

func init() {
	Register(&MeowApiPlatform{})
}

func (m *MeowApiPlatform) Name() state.PlatformName { return PlatformMeowApi }
func (m *MeowApiPlatform) Priority() int             { return 85 }

func (m *MeowApiPlatform) CanGet(_ string) bool { return false }

func (m *MeowApiPlatform) Get(_ string, _ bool) ([]*state.Track, error) {
	return nil, errors.New("meowapi platform does not support search")
}

func (m *MeowApiPlatform) CanDownload(source state.PlatformName) bool {
	if config.MeowAPIURL == "" || config.MeowAPIKey == "" {
		return false
	}
	return source == PlatformYouTube || source == PlatformSpotify || source == PlatformDeezer
}

func (m *MeowApiPlatform) Download(
	ctx context.Context,
	track *state.Track,
	_ *td.Message,
) (string, error) {
	if p := findFile(track); p != "" {
		logger.Debug("MeowApi: cache hit " + p)
		return p, nil
	}

	if track.ID == "" {
		return "", errors.New("meowapi: missing video id")
	}

	dtype, quality, ext, timeout := "audio", "128", ".mp3", audioDownloadTimeout
	if track.Video {
		dtype, quality, ext, timeout = "video", "480", ".mp4", videoDownloadTimeout
	}

	dctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	path := getPath(track, ext)

	streamURL := fmt.Sprintf(
		"%s/stream/%s?key=%s&type=%s&quality=%s",
		config.MeowAPIURL, track.ID, config.MeowAPIKey, dtype, quality,
	)
	switch track.Source {
	case PlatformSpotify:
		streamURL = fmt.Sprintf("%s/stream/spotify/%s?key=%s", config.MeowAPIURL, track.ID, config.MeowAPIKey)
	case PlatformDeezer:
		streamURL = fmt.Sprintf("%s/stream/deezer/%s?key=%s", config.MeowAPIURL, track.ID, config.MeowAPIKey)
	}

	r, err := rc.R().
		SetContext(dctx).
		SetHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36").
		SetResponseSaveFileName(path).
		Get(streamURL)
	if err != nil {
		os.Remove(path)
		if isDownloadCancelled(err) {
			return "", err
		}
		return "", sanitizeAPIError(
			fmt.Errorf("meowapi request failed: %w", err),
			config.MeowAPIKey,
		)
	}
	if r.IsStatusFailure() {
		os.Remove(path)
		return "", sanitizeAPIError(fmt.Errorf(
			"meowapi returned %d", r.StatusCode(),
		), config.MeowAPIKey)
	}

	info, statErr := os.Stat(path)
	if statErr != nil || info.Size() < minValidDownloadBytes {
		os.Remove(path)
		return "", errors.New("meowapi returned an invalid or empty file")
	}

	return path, nil
}

const (
	PlatformSpotify state.PlatformName = "Spotify"
	spotifyUA                           = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)

type SpotifyPlatform struct {
	cache *utils.Cache[string, []*state.Track]
}

var (
	spotifyEntityRe = regexp.MustCompile(
		`(?i)open\.spotify\.com/(?:intl-[a-z-]+/)?(?:embed/)?(track|album|playlist)/([A-Za-z0-9]{22})`,
	)
	spotifyNextDataRe = regexp.MustCompile(
		`(?s)<script id="__NEXT_DATA__" type="application/json">(.*?)</script>`,
	)
	spotifyHTTP  = &http.Client{Timeout: 15 * time.Second}
)

func init() {
	Register(&SpotifyPlatform{
		cache: utils.NewCache[string, []*state.Track](1 * time.Hour),
	})
}

func (s *SpotifyPlatform) Name() state.PlatformName { return PlatformSpotify }
func (s *SpotifyPlatform) Priority() int            { return 80 }

func (s *SpotifyPlatform) CanGet(query string) bool {
	q := strings.TrimSpace(query)
	return spotifyEntityRe.MatchString(q)
}

func (s *SpotifyPlatform) Get(query string, _ bool) ([]*state.Track, error) {
	link := strings.TrimSpace(query)

	m := spotifyEntityRe.FindStringSubmatch(link)
	if m == nil {
		return nil, errors.New("spotify: unsupported link")
	}
	kind, id := strings.ToLower(m[1]), m[2]

	cacheKey := kind + ":" + id
	if cached, ok := s.cache.Get(cacheKey); ok && len(cached) > 0 {
		return cloneTracks(cached), nil
	}

	var (
		tracks []*state.Track
		err    error
	)
	if kind == "track" {
		tracks, err = s.fetchTrack(id)
	} else {
		tracks, err = s.fetchCollection(kind, id)
	}
	if err != nil {
		return nil, fmt.Errorf("spotify: %w", err)
	}
	if len(tracks) == 0 {
		return nil, errors.New("spotify: no tracks found")
	}

	s.cache.Set(cacheKey, tracks)
	return cloneTracks(tracks), nil
}

func (s *SpotifyPlatform) CanDownload(_ state.PlatformName) bool { return false }

func (s *SpotifyPlatform) Download(_ context.Context, _ *state.Track, _ *td.Message) (string, error) {
	return "", errors.New("spotify platform does not support downloading")
}

func (s *SpotifyPlatform) fetchTrack(id string) ([]*state.Track, error) {
	entity, err := s.fetchEntity("track", id)
	if err == nil {
		if t := spotifyTrackFromEntity(entity, id); t != nil {
			return []*state.Track{t}, nil
		}
		err = errors.New("track data missing in embed page")
	}
	logger.Warnf("[Spotify] embed lookup failed for %s: %v, trying oembed", id, err)

	t, oerr := s.fetchOEmbed(id)
	if oerr != nil {
		return nil, fmt.Errorf("%v; oembed: %v", err, oerr)
	}
	return []*state.Track{t}, nil
}

func (s *SpotifyPlatform) fetchCollection(kind, id string) ([]*state.Track, error) {
	entity, err := s.fetchEntity(kind, id)
	if err != nil {
		return nil, err
	}

	list, _ := entity["trackList"].([]any)
	cover := spotifyCover(entity)

	limit := config.QueueLimit
	if limit <= 0 {
		limit = 15
	}

	tracks := make([]*state.Track, 0, len(list))
	for _, item := range list {
		it, ok := item.(map[string]any)
		if !ok {
			continue
		}
		uri := safeStr(it["uri"])
		tid := uri[strings.LastIndex(uri, ":")+1:]
		if len(tid) != 22 {
			continue
		}
		if playable, ok := it["isPlayable"].(bool); ok && !playable {
			continue
		}

		tracks = append(tracks, &state.Track{
			ID:       tid,
			Title:    spotifyTitle(safeStr(it["title"]), safeStr(it["subtitle"])),
			Duration: int(spotifyNum(it["duration"]) / 1000),
			Artwork:  cover,
			URL:      "https://open.spotify.com/track/" + tid,
			Source:   PlatformSpotify,
		})
		if len(tracks) >= limit {
			break
		}
	}
	return tracks, nil
}

func (s *SpotifyPlatform) fetchEntity(kind, id string) (map[string]any, error) {
	req, err := http.NewRequest(http.MethodGet, "https://open.spotify.com/embed/"+kind+"/"+id, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", spotifyUA)
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")

	resp, err := spotifyHTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("embed page returned %d", resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if err != nil {
		return nil, err
	}

	m := spotifyNextDataRe.FindSubmatch(body)
	if m == nil {
		return nil, errors.New("embed data not found")
	}

	var data map[string]any
	if err := json.Unmarshal(m[1], &data); err != nil {
		return nil, fmt.Errorf("embed data invalid: %w", err)
	}

	for _, path := range [][]any{
		{"props", "pageProps", "state", "data", "entity"},
		{"props", "pageProps", "data", "entity"},
	} {
		if entity, ok := dig(data, path...).(map[string]any); ok && len(entity) > 0 {
			return entity, nil
		}
	}
	return nil, errors.New("entity not found in embed data")
}

func (s *SpotifyPlatform) fetchOEmbed(id string) (*state.Track, error) {
	trackURL := "https://open.spotify.com/track/" + id
	req, err := http.NewRequest(
		http.MethodGet,
		"https://open.spotify.com/oembed?url="+url.QueryEscape(trackURL),
		nil,
	)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", spotifyUA)

	resp, err := spotifyHTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("returned %d", resp.StatusCode)
	}

	var out struct {
		Title     string `json:"title"`
		Thumbnail string `json:"thumbnail_url"`
	}
	if err := json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(&out); err != nil {
		return nil, err
	}
	if strings.TrimSpace(out.Title) == "" {
		return nil, errors.New("empty title")
	}

	return &state.Track{
		ID:      id,
		Title:   out.Title,
		Artwork: out.Thumbnail,
		URL:     trackURL,
		Source:  PlatformSpotify,
	}, nil
}

func spotifyTrackFromEntity(e map[string]any, id string) *state.Track {
	name := firstNonEmpty(safeStr(e["name"]), safeStr(e["title"]))
	if name == "" {
		return nil
	}

	var artists []string
	if list, ok := e["artists"].([]any); ok {
		for _, a := range list {
			if n := safeStr(dig(a, "name")); n != "" {
				artists = append(artists, n)
			}
		}
	}
	artist := strings.Join(artists, ", ")
	if artist == "" {
		artist = safeStr(e["subtitle"])
	}

	return &state.Track{
		ID:       id,
		Title:    spotifyTitle(name, artist),
		Duration: int(spotifyNum(e["duration"]) / 1000),
		Artwork:  spotifyCover(e),
		URL:      "https://open.spotify.com/track/" + id,
		Source:   PlatformSpotify,
	}
}

func spotifyTitle(name, artist string) string {
	name, artist = strings.TrimSpace(name), strings.TrimSpace(artist)
	if name == "" {
		return artist
	}
	if artist == "" {
		return name
	}
	return name + " - " + artist
}

func spotifyCover(e map[string]any) string {
	sources, _ := dig(e, "coverArt", "sources").([]any)
	best, bestW := "", -1.0
	for _, src := range sources {
		sm, ok := src.(map[string]any)
		if !ok {
			continue
		}
		imgURL := safeStr(sm["url"])
		if imgURL == "" {
			continue
		}
		if w := spotifyNum(sm["width"]); w > bestW {
			best, bestW = imgURL, w
		}
	}
	return best
}

func spotifyNum(v any) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	}
	return 0
}

func cloneTracks(in []*state.Track) []*state.Track {
	out := make([]*state.Track, 0, len(in))
	for _, t := range in {
		if t == nil {
			continue
		}
		c := *t
		out = append(out, &c)
	}
	return out
}

const PlatformDeezer state.PlatformName = "Deezer"

type DeezerPlatform struct {
	cache *utils.Cache[string, []*state.Track]
}

var (
	deezerEntityRe = regexp.MustCompile(
		`(?i)deezer\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?(track|album|playlist)/(\d+)`,
	)
	deezerHTTP  = &http.Client{Timeout: 15 * time.Second}
)

type deezerTrack struct {
	ID       int64  `json:"id"`
	Title    string `json:"title"`
	Duration int    `json:"duration"`
	Artist   struct {
		Name string `json:"name"`
	} `json:"artist"`
	Album struct {
		CoverXL  string `json:"cover_xl"`
		CoverBig string `json:"cover_big"`
		Cover    string `json:"cover_medium"`
	} `json:"album"`
	Error *deezerError `json:"error"`
}

type deezerCollection struct {
	Title    string `json:"title"`
	CoverXL  string `json:"cover_xl"`
	CoverBig string `json:"cover_big"`
	Tracks   struct {
		Data []deezerTrack `json:"data"`
	} `json:"tracks"`
	Error *deezerError `json:"error"`
}

type deezerError struct {
	Type    string `json:"type"`
	Message string `json:"message"`
}

func init() {
	Register(&DeezerPlatform{
		cache: utils.NewCache[string, []*state.Track](1 * time.Hour),
	})
}

func (d *DeezerPlatform) Name() state.PlatformName { return PlatformDeezer }
func (d *DeezerPlatform) Priority() int            { return 80 }

func (d *DeezerPlatform) CanGet(query string) bool {
	q := strings.TrimSpace(query)
	return deezerEntityRe.MatchString(q)
}

func (d *DeezerPlatform) Get(query string, _ bool) ([]*state.Track, error) {
	link := strings.TrimSpace(query)

	m := deezerEntityRe.FindStringSubmatch(link)
	if m == nil {
		return nil, errors.New("deezer: unsupported link")
	}
	kind, id := strings.ToLower(m[1]), m[2]

	cacheKey := kind + ":" + id
	if cached, ok := d.cache.Get(cacheKey); ok && len(cached) > 0 {
		return cloneTracks(cached), nil
	}

	var (
		tracks []*state.Track
		err    error
	)
	if kind == "track" {
		tracks, err = d.fetchTrack(id)
	} else {
		tracks, err = d.fetchCollection(kind, id)
	}
	if err != nil {
		return nil, fmt.Errorf("deezer: %w", err)
	}
	if len(tracks) == 0 {
		return nil, errors.New("deezer: no tracks found")
	}

	d.cache.Set(cacheKey, tracks)
	return cloneTracks(tracks), nil
}

func (d *DeezerPlatform) CanDownload(_ state.PlatformName) bool { return false }

func (d *DeezerPlatform) Download(_ context.Context, _ *state.Track, _ *td.Message) (string, error) {
	return "", errors.New("deezer platform does not support downloading")
}

func (d *DeezerPlatform) fetchTrack(id string) ([]*state.Track, error) {
	var dt deezerTrack
	if err := deezerGet("track/"+id, &dt); err != nil {
		return nil, err
	}
	if dt.Error != nil {
		return nil, errors.New(dt.Error.Message)
	}

	t := deezerToTrack(&dt, "")
	if t == nil {
		return nil, errors.New("track not found")
	}
	return []*state.Track{t}, nil
}

func (d *DeezerPlatform) fetchCollection(kind, id string) ([]*state.Track, error) {
	var col deezerCollection
	if err := deezerGet(kind+"/"+id, &col); err != nil {
		return nil, err
	}
	if col.Error != nil {
		return nil, errors.New(col.Error.Message)
	}

	cover := firstNonEmpty(col.CoverXL, col.CoverBig)

	limit := config.QueueLimit
	if limit <= 0 {
		limit = 15
	}

	tracks := make([]*state.Track, 0, len(col.Tracks.Data))
	for i := range col.Tracks.Data {
		if t := deezerToTrack(&col.Tracks.Data[i], cover); t != nil {
			tracks = append(tracks, t)
		}
		if len(tracks) >= limit {
			break
		}
	}
	return tracks, nil
}

func deezerToTrack(dt *deezerTrack, fallbackCover string) *state.Track {
	if dt == nil || dt.ID <= 0 || strings.TrimSpace(dt.Title) == "" {
		return nil
	}

	id := strconv.FormatInt(dt.ID, 10)
	title := dt.Title
	if a := strings.TrimSpace(dt.Artist.Name); a != "" {
		title += " - " + a
	}

	return &state.Track{
		ID:       id,
		Title:    title,
		Duration: dt.Duration,
		Artwork:  firstNonEmpty(dt.Album.CoverXL, dt.Album.CoverBig, dt.Album.Cover, fallbackCover),
		URL:      "https://www.deezer.com/track/" + id,
		Source:   PlatformDeezer,
	}
}

func deezerGet(path string, out any) error {
	req, err := http.NewRequest(http.MethodGet, "https://api.deezer.com/"+path, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

	resp, err := deezerHTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("api returned %d", resp.StatusCode)
	}
	return json.NewDecoder(io.LimitReader(resp.Body, 8<<20)).Decode(out)
}
