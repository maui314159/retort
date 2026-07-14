package com.example.books.controller;

import java.net.URI;
import java.util.List;

import com.example.books.dto.BookRequest;
import com.example.books.exception.ResourceNotFoundException;
import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/books")
public class BookController {

    private final BookRepository repository;

    public BookController(BookRepository repository) {
        this.repository = repository;
    }

    @PostMapping
    public ResponseEntity<Book> create(@Valid @RequestBody BookRequest request) {
        Book saved = repository.save(toBook(request, null));
        return ResponseEntity.created(URI.create("/books/" + saved.id())).body(saved);
    }

    @GetMapping
    public List<Book> list(@RequestParam(name = "author", required = false) String author) {
        return repository.findAll(author);
    }

    @GetMapping("/{id}")
    public Book getOne(@PathVariable Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book with id " + id + " not found"));
    }

    @PutMapping("/{id}")
    public Book update(@PathVariable Long id, @Valid @RequestBody BookRequest request) {
        Book existing = repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book with id " + id + " not found"));
        repository.update(id, toBook(request, existing.id()));
        return repository.findById(id).orElseThrow();
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        if (!repository.deleteById(id)) {
            throw new ResourceNotFoundException("Book with id " + id + " not found");
        }
    }

    private Book toBook(BookRequest request, Long id) {
        return new Book(id, request.title(), request.author(), request.year(), request.isbn());
    }
}
