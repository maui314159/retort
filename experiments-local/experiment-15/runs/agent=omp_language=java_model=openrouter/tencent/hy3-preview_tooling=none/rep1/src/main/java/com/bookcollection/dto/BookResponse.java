package com.bookcollection.dto;

public class BookResponse {
    private Long id;
    private String title;
    private String author;
    private Integer year;
    private String isbn;

    public BookResponse(Long id, String title, String author, Integer year, String isbn) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.year = year;
        this.isbn = isbn;
    }

    public Long getId() { return id; }
    public String getTitle() { return title; }
    public String getAuthor() { return author; }
    public Integer getYear() { return year; }
    public String getIsbn() { return isbn; }
}
