package com.example.books;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class BookService {

    private final BookRepository repository;

    public BookService(BookRepository repository) {
        this.repository = repository;
    }

    public Book create(Book book) {
        validate(book);
        return repository.create(book);
    }

    public List<Book> list(String author) {
        return repository.findAll(author);
    }

    public Optional<Book> get(Long id) {
        return repository.findById(id);
    }

    public Optional<Book> update(Long id, Book book) {
        validate(book);
        return repository.update(id, book);
    }

    public boolean delete(Long id) {
        return repository.delete(id);
    }

    private void validate(Book book) {
        if (book.title() == null || book.title().isBlank()) {
            throw new IllegalArgumentException("Title is required");
        }
        if (book.author() == null || book.author().isBlank()) {
            throw new IllegalArgumentException("Author is required");
        }
    }
}
