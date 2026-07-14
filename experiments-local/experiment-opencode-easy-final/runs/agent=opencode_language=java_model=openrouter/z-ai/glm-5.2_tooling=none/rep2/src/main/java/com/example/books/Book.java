package com.example.books;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Objects;

public class Book {
    private Long id;
    private String title;
    private String author;
    private Integer year;
    private String isbn;

    public Book() {}

    public Book(Long id, String title, String author, Integer year, String isbn) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    @JsonProperty("id")
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    @JsonProperty("title")
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    @JsonProperty("author")
    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }

    @JsonProperty("year")
    public Integer getYear() { return year; }
    public void setYear(Integer year) { this.year = year; }

    @JsonProperty("isbn")
    public String getIsbn() { return isbn; }
    public void setIsbn(String isbn) { this.isbn = isbn; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Book b)) return false;
        return Objects.equals(id, b.id) && Objects.equals(title, b.title)
                && Objects.equals(author, b.author) && Objects.equals(year, b.year)
                && Objects.equals(isbn, b.isbn);
    }

    @Override
    public int hashCode() { return Objects.hash(id, title, author, year, isbn); }
}
