package com.example.books;

import org.springframework.stereotype.Service;

import java.util.List;

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
        return repository.findAll();
    }

    public Book findById(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new BookNotFoundException(id));
    }

    public Book update(Long id, Book incoming) {
        Book existing = findById(id);
        existing.setTitle(incoming.getTitle());
        existing.setAuthor(incoming.getAuthor());
        existing.setYear(incoming.getYear());
        existing.setIsbn(incoming.getIsbn());
        repository.update(existing);
        return existing;
    }

    public void delete(Long id) {
        repository.deleteById(id);
    }
}
