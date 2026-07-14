package com.example.books.service;

import com.example.books.exception.ResourceNotFoundException;
import com.example.books.model.Book;
import com.example.books.model.BookRequest;
import com.example.books.repository.BookRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class BookService {

    private final BookRepository repository;

    public BookService(BookRepository repository) {
        this.repository = repository;
    }

    public Book create(BookRequest request) {
        Book book = new Book();
        book.setTitle(request.getTitle());
        book.setAuthor(request.getAuthor());
        book.setYear(request.getYear());
        book.setIsbn(request.getIsbn());
        return repository.save(book);
    }

    public List<Book> findAll(String author) {
        return repository.findAll(author);
    }

    public Book findById(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book with id " + id + " not found"));
    }

    public Book update(Long id, BookRequest request) {
        findById(id);
        Book book = new Book();
        book.setId(id);
        book.setTitle(request.getTitle());
        book.setAuthor(request.getAuthor());
        book.setYear(request.getYear());
        book.setIsbn(request.getIsbn());
        repository.update(id, book);
        return book;
    }

    public void delete(Long id) {
        findById(id);
        repository.deleteById(id);
    }
}
