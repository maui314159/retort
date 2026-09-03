package main

import (
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
)

// Config holds runtime configuration parsed from flags/env.
type Config struct {
	Addr string
	DB   string
}

func loadConfig() Config {
	c := Config{Addr: ":8080", DB: "books.db"}
	flag.StringVar(&c.Addr, "addr", c.Addr, "address to listen on")
	flag.StringVar(&c.DB, "db", c.DB, "path to the SQLite database file")
	flag.Parse()
	if v := os.Getenv("BOOKAPI_ADDR"); v != "" {
		c.Addr = v
	}
	if v := os.Getenv("BOOKAPI_DB"); v != "" {
		c.DB = v
	}
	return c
}

func main() {
	cfg := loadConfig()

	store, err := NewStore(cfg.DB)
	if err != nil {
		log.Fatalf("failed to open store: %v", err)
	}
	defer store.Close()

	h := &handlers{store: store}
	srv := &http.Server{
		Addr:    cfg.Addr,
		Handler: h.routes(),
	}

	// Graceful shutdown on SIGINT/SIGTERM.
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
		<-sig
		log.Println("shutting down...")
		_ = srv.Close()
	}()

	log.Printf("bookapi listening on %s (db=%s)", cfg.Addr, cfg.DB)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}
