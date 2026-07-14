package com.example.books.service;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
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
        return repository.save(book);
    }

    public List<Book> findAll(String author) {
        if (author != null && !author.isBlank()) {
            return repository.findByAuthor(author);
        }
        return (List<Book>) repository.findAll();
    }

    public Optional<Book> findById(Long id) {
        return repository.findById(id);
    }

    public Optional<Book> update(Long id, Book updates) {
        return repository.findById(id).map(existing -> {
            if (updates.getTitle() != null) existing.setTitle(updates.getTitle());
            if (updates.getAuthor() != null) existing.setAuthor(updates.getAuthor());
            if (updates.getYear() != null) existing.setYear(updates.getYear());
            if (updates.getIsbn() != null) existing.setIsbn(updates.getIsbn());
            return repository.save(existing);
        });
    }

    public boolean delete(Long id) {
        if (repository.existsById(id)) {
            repository.deleteById(id);
            return true;
        }
        return false;
    }
}
