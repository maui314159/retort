package com.bookcollection.service;

import com.bookcollection.dto.BookRequest;
import com.bookcollection.dto.BookResponse;
import com.bookcollection.model.Book;
import com.bookcollection.repository.BookRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class BookService {
    private final BookRepository bookRepository;

    public BookService(BookRepository bookRepository) {
        this.bookRepository = bookRepository;
    }

    public BookResponse createBook(BookRequest request) {
        Book book = new Book();
        book.setTitle(request.getTitle());
        book.setAuthor(request.getAuthor());
        book.setYear(request.getYear());
        book.setIsbn(request.getIsbn());
        Book saved = bookRepository.save(book);
        return toResponse(saved);
    }

    public List<BookResponse> getAllBooks(String author) {
        return bookRepository.findAll(author).stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    public Optional<BookResponse> getBookById(Long id) {
        return bookRepository.findById(id).map(this::toResponse);
    }

    public Optional<BookResponse> updateBook(Long id, BookRequest request) {
        return bookRepository.findById(id).map(existing -> {
            existing.setTitle(request.getTitle());
            existing.setAuthor(request.getAuthor());
            existing.setYear(request.getYear());
            existing.setIsbn(request.getIsbn());
            Book updated = bookRepository.save(existing);
            return toResponse(updated);
        });
    }

    public void deleteBook(Long id) {
        bookRepository.deleteById(id);
    }

    private BookResponse toResponse(Book book) {
        return new BookResponse(book.getId(), book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn());
    }
}
