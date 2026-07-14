package com.example.bookapi.model;

/** Persisted book entity. */
public record Book(Long id, String title, String author, Integer year, String isbn) {
}
