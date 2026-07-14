package com.example.books.service;

import java.util.List;

import com.example.books.dto.BookRequest;
import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.springframework.stereotype.Service;

@Service
public class BookService {

    private final BookRepository repository;

    public BookService(BookRepository repository) {
        this.repository = repository;
    }

    public Book create(BookRequest request) {
        return repository.save(request.getTitle(), request.getAuthor(),
                request.getYear(), request.getIsbn());
    }

    public List<Book> findAll(String author) {
        if (author != null && !author.isBlank()) {
            return repository.findByAuthor(author);
        }
        return repository.findAll();
    }

    public Book findById(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new com.example.books.exception.ResourceNotFoundException(
                        "Book not found with id " + id));
    }

    public Book update(Long id, BookRequest request) {
        boolean updated = repository.update(id, request.getTitle(), request.getAuthor(),
                request.getYear(), request.getIsbn());
        if (!updated) {
            throw new com.example.books.exception.ResourceNotFoundException(
                    "Book not found with id " + id);
        }
        return new Book(id, request.getTitle(), request.getAuthor(),
                request.getYear(), request.getIsbn());
    }

    public void delete(Long id) {
        boolean deleted = repository.deleteById(id);
        if (!deleted) {
            throw new com.example.books.exception.ResourceNotFoundException(
                    "Book not found with id " + id);
        }
    }
}
