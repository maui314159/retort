package com.example.books.controller;

import com.example.books.dto.BookRequest;
import com.example.books.dto.BookResponse;
import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/books")
public class BookController {

    private final BookRepository repository;

    public BookController(BookRepository repository) {
        this.repository = repository;
    }

    @PostMapping
    public ResponseEntity<BookResponse> create(@Valid @RequestBody BookRequest request) {
        Book book = new Book(request.getTitle(), request.getAuthor(), request.getYear(), request.getIsbn());
        Book saved = repository.save(book);
        return ResponseEntity.status(HttpStatus.CREATED).body(new BookResponse(saved));
    }

    @GetMapping
    public List<BookResponse> list(@RequestParam(name = "author", required = false) String author) {
        if (author == null || author.isBlank()) {
            return repository.findAll().stream().map(BookResponse::new).toList();
        }
        return repository.findByAuthorContainingIgnoreCase(author).stream().map(BookResponse::new).toList();
    }

    @GetMapping("/{id}")
    public ResponseEntity<BookResponse> get(@PathVariable Long id) {
        Optional<Book> found = repository.findById(id);
        return found.map(b -> ResponseEntity.ok(new BookResponse(b)))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PutMapping("/{id}")
    public ResponseEntity<BookResponse> update(@PathVariable Long id, @Valid @RequestBody BookRequest request) {
        Optional<Book> existing = repository.findById(id);
        if (existing.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        Book book = existing.get();
        book.setTitle(request.getTitle());
        book.setAuthor(request.getAuthor());
        book.setYear(request.getYear());
        book.setIsbn(request.getIsbn());
        Book saved = repository.save(book);
        return ResponseEntity.ok(new BookResponse(saved));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        if (!repository.existsById(id)) {
            return ResponseEntity.notFound().build();
        }
        repository.deleteById(id);
        return ResponseEntity.noContent().build();
    }
}
