package com.books.repository;

import com.books.model.Book;
import org.springframework.data.jdbc.repository.query.Query;
import org.springframework.data.repository.CrudRepository;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface BookRepository extends CrudRepository<Book, Long> {

    @Query("SELECT * FROM books WHERE author = :author")
    List<Book> findByAuthor(@Param("author") String author);
}
