package com.example.books;

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
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/books")
public class BookController {

    private final BookRepository repo;

    public BookController(BookRepository repo) {
        this.repo = repo;
    }

    @PostMapping
    public ResponseEntity<Book> create(@Valid @RequestBody Book book) {
        Book saved = repo.save(book);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(saved.getId())
                .toUri();
        return ResponseEntity.created(location).body(saved);
    }

    @GetMapping
    public List<Book> list(@RequestParam(value = "author", required = false) String author) {
        return repo.findAll(author);
    }

    @GetMapping("/{id}")
    public Book get(@PathVariable long id) {
        return repo.findById(id).orElseThrow(() -> new BookNotFoundException(id));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Book> update(@PathVariable long id, @Valid @RequestBody Book book) {
        if (!repo.findById(id).isPresent()) {
            throw new BookNotFoundException(id);
        }
        repo.update(id, book);
        book.setId(id);
        return ResponseEntity.ok(book);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable long id) {
        if (!repo.delete(id)) {
            throw new BookNotFoundException(id);
        }
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }
}
