package com.example.bookapi.model;

/**
 * A book in the collection.
 *
 * @param id     database-generated identifier
 * @param title  non-blank title
 * @param author non-blank author
 * @param year   publication year (nullable)
 * @param isbn   ISBN identifier (nullable)
 */
public record Book(Long id, String title, String author, Integer year, String isbn) {
}
