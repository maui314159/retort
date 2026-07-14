package com.example.books;

import java.util.List;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BookService {

    private final BookRepository repository;

    @Autowired
    public BookService(BookRepository repository) {
        this.repository = repository;
    }

    private void validate(Book book) {
        if (book.getTitle() == null || book.getTitle().isBlank()) {
            throw new ValidationException("title is required");
        }
        if (book.getAuthor() == null || book.getAuthor().isBlank()) {
            throw new ValidationException("author is required");
        }
        if (book.getYear() != null && (book.getYear() < 0 || book.getYear() > 9999)) {
            throw new ValidationException("year must be between 0 and 9999");
        }
    }

    @Transactional
    public Book create(Book book) {
        validate(book);
        return repository.save(book);
    }

    public List<Book> findAll(String author) {
        if (author != null && !author.isBlank()) {
            return repository.findByAuthor(author);
        }
        return repository.findAll();
    }

    public Book get(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new BookNotFoundException(id));
    }

    @Transactional
    public Book update(Long id, Book incoming) {
        Book existing = get(id);
        validateForUpdate(incoming, existing);
        existing.setTitle(incoming.getTitle() != null ? incoming.getTitle() : existing.getTitle());
        existing.setAuthor(incoming.getAuthor() != null ? incoming.getAuthor() : existing.getAuthor());
        existing.setYear(incoming.getYear());
        existing.setIsbn(incoming.getIsbn());
        return repository.save(existing);
    }

    private void validateForUpdate(Book incoming, Book existing) {
        String title = incoming.getTitle() != null ? incoming.getTitle() : existing.getTitle();
        String author = incoming.getAuthor() != null ? incoming.getAuthor() : existing.getAuthor();
        if (title == null || title.isBlank()) {
            throw new ValidationException("title is required");
        }
        if (author == null || author.isBlank()) {
            throw new ValidationException("author is required");
        }
        if (incoming.getYear() != null && (incoming.getYear() < 0 || incoming.getYear() > 9999)) {
            throw new ValidationException("year must be between 0 and 9999");
        }
    }

    @Transactional
    public void delete(Long id) {
        if (repository.findById(id).isEmpty()) {
            throw new BookNotFoundException(id);
        }
        repository.deleteById(id);
    }
}
