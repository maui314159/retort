package com.example.bookapi;

public record Book(
        Long id,
        String title,
        String author,
        Integer year,
        String isbn
) {}