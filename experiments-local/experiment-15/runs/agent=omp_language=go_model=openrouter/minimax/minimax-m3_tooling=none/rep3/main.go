// Command bookapi runs a REST API service for managing a book collection.
//
// It listens on $BOOKS_ADDR (default ":8080") and persists data in a
// SQLite database at $BOOKS_DB (default "./books.db").
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/example/bookapi/internal/books"
)

func main() {
	addr := envOr("BOOKS_ADDR", ":8080")
	dbPath := envOr("BOOKS_DB", "./books.db")

	log := slog.New(slog.NewJSONHandler(os.Stderr, nil))

	store, err := books.Open(dbPath)
	if err != nil {
		log.Error("open store", "err", err)
		os.Exit(1)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           books.NewServer(store, log).Routes(),
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Run the server in a goroutine so we can intercept signals and
	// shut down gracefully (in-flight requests get a chance to finish).
	errCh := make(chan error, 1)
	go func() {
		log.Info("listening", "addr", addr, "db", dbPath)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	select {
	case err := <-errCh:
		log.Error("server failed", "err", err)
		os.Exit(1)
	case sig := <-stop:
		log.Info("shutting down", "signal", sig.String())
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := srv.Shutdown(ctx); err != nil {
			log.Error("shutdown", "err", err)
			os.Exit(1)
		}
	}
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
