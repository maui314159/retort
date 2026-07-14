package com.example.bookapi.controller;

import java.util.List;
import java.util.Map;

import com.example.bookapi.dto.BookRequest;
import com.example.bookapi.exception.BookNotFoundException;
import com.example.bookapi.model.Book;
import com.example.bookapi.repository.BookRepository;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST endpoints for the book collection.
 */
@RestController
@RequestMapping("/books")
public class BookController {

    private final BookRepository books;

    public BookController(BookRepository books) {
        this.books = books;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Book create(@Valid @RequestBody BookRequest request) {
        Book toSave = new Book(null, request.title(), request.author(), request.year(), request.isbn());
        return books.save(toSave);
    }

    @GetMapping
    public List<Book> list(@RequestParam(name = "author", required = false) String author) {
        if (author != null && !author.isBlank()) {
            return books.findByAuthor(author);
        }
        return books.findAll();
    }

    @GetMapping("/{id}")
    public Book get(@PathVariable Long id) {
        return books.findById(id)
                .orElseThrow(() -> new BookNotFoundException(id));
    }

    @PutMapping("/{id}")
    public Book update(@PathVariable Long id, @Valid @RequestBody BookRequest request) {
        Book toUpdate = new Book(id, request.title(), request.author(), request.year(), request.isbn());
        return books.update(id, toUpdate)
                .orElseThrow(() -> new BookNotFoundException(id));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        if (!books.deleteById(id)) {
            throw new BookNotFoundException(id);
        }
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP"));
    }
}
