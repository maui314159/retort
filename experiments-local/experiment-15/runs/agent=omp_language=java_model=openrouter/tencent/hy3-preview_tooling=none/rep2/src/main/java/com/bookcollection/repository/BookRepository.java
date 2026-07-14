package com.bookcollection.repository;

import com.bookcollection.model.Book;
import java.util.List;

public interface BookRepository {
    Book save(Book book);
    List<Book> findAll();
    List<Book> findByAuthor(String author);
    Book findById(Long id);
    void deleteById(Long id);
}