package com.example.books;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * A book in the collection.
 *
 * Fields use {@code @JsonProperty} to define the wire contract independent of
 * the field names, and {@code @JsonInclude(NON_NULL)} to keep JSON responses
 * compact when optional fields are absent.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public final class Book {

    @JsonProperty("id")
    private Long id;

    @JsonProperty("title")
    private String title;

    @JsonProperty("author")
    private String author;

    @JsonProperty("year")
    private Integer year;

    @JsonProperty("isbn")
    private String isbn;

    public Book() {
        // Jackson
    }

    public Book(Long id, String title, String author, Integer year, String isbn) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public Integer getYear() {
        return year;
    }

    public void setYear(Integer year) {
        this.year = year;
    }

    public String getIsbn() {
        return isbn;
    }

    public void setIsbn(String isbn) {
        this.isbn = isbn;
    }
}
