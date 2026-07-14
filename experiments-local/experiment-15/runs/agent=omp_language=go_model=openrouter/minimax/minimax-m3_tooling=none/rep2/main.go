// Command books runs the book-collection REST API.
//
// It reads the database path and listen address from environment variables
// (BOOKS_DB, BOOKS_ADDR) with sensible defaults, opens the SQLite store,
// registers handlers, and serves HTTP until SIGINT/SIGTERM.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"books/internal/api"
	"books/internal/store"
)

func main() {
	logger := log.New(os.Stdout, "books ", log.LstdFlags|log.Lmsgprefix)

	addr := envDefault("BOOKS_ADDR", ":8080")
	dbPath := envDefault("BOOKS_DB", "books.db")

	s, err := store.Open(dbPath)
	if err != nil {
		logger.Fatalf("open store: %v", err)
	}
	defer func() {
		if err := s.Close(); err != nil {
			logger.Printf("close store: %v", err)
		}
	}()

	a := &api.API{Store: s, Logger: logger}
	srv := &http.Server{
		Addr:              addr,
		Handler:           a.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Run the server in the background; the main goroutine waits for a
	// signal so a clean shutdown can flush in-flight requests.
	errCh := make(chan error, 1)
	go func() {
		logger.Printf("listening on %s (db=%s)", addr, dbPath)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
		close(errCh)
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		logger.Printf("received %s, shutting down", sig)
	case err := <-errCh:
		if err != nil {
			logger.Fatalf("server error: %v", err)
		}
		return
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Printf("shutdown: %v", err)
	}
}

func envDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
