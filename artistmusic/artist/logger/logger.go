package logger

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type Logger struct {
	sl *slog.Logger
}

type Option func(*config)

type config struct {
	level   slog.Level
	out     io.Writer
	handler slog.Handler
}

func WithLevel(l slog.Level) Option {
	return func(c *config) { c.level = l }
}

func WithOutput(w io.Writer) Option {
	return func(c *config) { c.out = w }
}

// WithHandler supplies a custom slog.Handler, overriding level/output.
func WithHandler(h slog.Handler) Option {
	return func(c *config) { c.handler = h }
}

// New builds a Logger from options. With no options it logs INFO+ to stderr.
func New(opts ...Option) *Logger {
	c := &config{level: slog.LevelInfo, out: os.Stderr}
	for _, o := range opts {
		o(c)
	}
	h := c.handler
	if h == nil {
		h = &plainHandler{
			level: c.level,
			out:   c.out,
			mu:    &sync.Mutex{},
		}
	}
	return &Logger{sl: slog.New(h)}
}

// From wraps an existing *slog.Logger; a nil sl yields a disabled logger.
func From(sl *slog.Logger) *Logger {
	if sl == nil {
		return Disabled()
	}
	return &Logger{sl: sl}
}

// Disabled returns a logger that discards everything.
func Disabled() *Logger {
	h := slog.NewTextHandler(io.Discard, &slog.HandlerOptions{Level: slog.LevelError + 1})
	return &Logger{sl: slog.New(h)}
}

// With returns a child logger that attaches the given attrs to every record.
func (l *Logger) With(args ...any) *Logger {
	return &Logger{sl: l.sl.With(args...)}
}

func (l *Logger) Debug(msg string, args ...any) { l.log(slog.LevelDebug, msg, args...) }
func (l *Logger) Info(msg string, args ...any)  { l.log(slog.LevelInfo, msg, args...) }
func (l *Logger) Warn(msg string, args ...any)  { l.log(slog.LevelWarn, msg, args...) }
func (l *Logger) Error(msg string, args ...any) { l.log(slog.LevelError, msg, args...) }

func (l *Logger) Debugf(format string, args ...any) { l.logf(slog.LevelDebug, format, args...) }
func (l *Logger) Infof(format string, args ...any)  { l.logf(slog.LevelInfo, format, args...) }
func (l *Logger) Warnf(format string, args ...any)  { l.logf(slog.LevelWarn, format, args...) }
func (l *Logger) Errorf(format string, args ...any) { l.logf(slog.LevelError, format, args...) }

func (l *Logger) log(level slog.Level, msg string, args ...any) {
	if l == nil || l.sl == nil || !l.sl.Enabled(context.Background(), level) {
		return
	}
	var pcs [1]uintptr
	runtime.Callers(3, pcs[:])
	r := slog.NewRecord(time.Now(), level, msg, pcs[0])
	r.Add(args...)
	_ = l.sl.Handler().Handle(context.Background(), r)
}

func (l *Logger) logf(level slog.Level, format string, args ...any) {
	if l == nil || l.sl == nil || !l.sl.Enabled(context.Background(), level) {
		return
	}
	var pcs [1]uintptr
	runtime.Callers(3, pcs[:])
	r := slog.NewRecord(time.Now(), level, fmt.Sprintf(format, args...), pcs[0])
	_ = l.sl.Handler().Handle(context.Background(), r)
}

type plainHandler struct {
	level slog.Level
	out   io.Writer
	mu    *sync.Mutex
	attrs []slog.Attr
	group string
}

func (h *plainHandler) Enabled(_ context.Context, level slog.Level) bool {
	return level >= h.level
}

func (h *plainHandler) Handle(_ context.Context, r slog.Record) error {
	var b strings.Builder
	
	b.WriteString(r.Time.Format("15:04:05.000"))
	b.WriteString(" ")

	level := r.Level.String()
	b.WriteString(fmt.Sprintf("%-5s", level))
	b.WriteString(" ")

	if h.group != "" {
		b.WriteString(h.group)
		b.WriteString(" ")
	}

	if r.PC != 0 {
		fs := runtime.CallersFrames([]uintptr{r.PC})
		f, _ := fs.Next()
		b.WriteString(fmt.Sprintf("%s:%d", filepath.Base(f.File), f.Line))
		b.WriteString(" ")
	}

	b.WriteString(r.Message)

	r.Attrs(func(a slog.Attr) bool {
		b.WriteString(fmt.Sprintf(" %s=%v", a.Key, a.Value.Any()))
		return true
	})

	for _, a := range h.attrs {
		b.WriteString(fmt.Sprintf(" %s=%v", a.Key, a.Value.Any()))
	}

	b.WriteString("\n")

	h.mu.Lock()
	defer h.mu.Unlock()
	_, err := io.WriteString(h.out, b.String())
	return err
}

func (h *plainHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	newHandler := *h
	newHandler.attrs = make([]slog.Attr, len(h.attrs)+len(attrs))
	copy(newHandler.attrs, h.attrs)
	copy(newHandler.attrs[len(h.attrs):], attrs)
	return &newHandler
}

func (h *plainHandler) WithGroup(name string) slog.Handler {
	newHandler := *h
	if newHandler.group != "" {
		newHandler.group += "." + name
	} else {
		newHandler.group = name
	}
	return &newHandler
}
