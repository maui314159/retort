package com.example.books.service;

import com.example.books.model.Book;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Optional;

@Service
public class BookService {

    private final JdbcTemplate jdbcTemplate;

    private static final RowMapper<Book> BOOK_ROW_MAPPER = (rs, rowNum) ->
            new Book(
                    rs.getLong("id"),
                    rs.getString("title"),
                    rs.getString("author"),
                    rs.getObject("year") == null ? null : rs.getInt("year"),
                    rs.getString("isbn")
            );

    public BookService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Book create(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(conn -> {
            PreparedStatement ps = conn.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            ps.setObject(3, book.getYear());
            ps.setString(4, book.getIsbn());
            return ps;
        }, keyHolder);
        book.setId(keyHolder.getKey().longValue());
        return book;
    }

    public List<Book> findAll() {
        return jdbcTemplate.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", BOOK_ROW_MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbcTemplate.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                BOOK_ROW_MAPPER, author);
    }

    public Optional<Book> findById(Long id) {
        List<Book> books = jdbcTemplate.query(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                BOOK_ROW_MAPPER, id);
        return books.isEmpty() ? Optional.empty() : Optional.of(books.get(0));
    }

    public Optional<Book> update(Long id, Book book) {
        int rows = jdbcTemplate.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn(), id);
        if (rows == 0) {
            return Optional.empty();
        }
        book.setId(id);
        return Optional.of(book);
    }

    public boolean delete(Long id) {
        int rows = jdbcTemplate.update("DELETE FROM books WHERE id = ?", id);
        return rows > 0;
    }
}
