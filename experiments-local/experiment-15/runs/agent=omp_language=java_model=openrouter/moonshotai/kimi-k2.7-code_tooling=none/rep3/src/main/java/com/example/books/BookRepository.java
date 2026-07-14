package com.example.books;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Optional;

@Repository
public class BookRepository {

    private final JdbcTemplate jdbc;
    private final RowMapper<Book> mapper = (rs, rowNum) -> new Book(
        rs.getLong("id"),
        rs.getString("title"),
        rs.getString("author"),
        rs.getObject("year", Integer.class),
        rs.getString("isbn")
    );

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Book create(Book book) {
        var keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                Statement.RETURN_GENERATED_KEYS
            );
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            ps.setObject(3, book.year());
            ps.setString(4, book.isbn());
            return ps;
        }, keyHolder);
        Number id = keyHolder.getKey();
        return new Book(id.longValue(), book.title(), book.author(), book.year(), book.isbn());
    }

    public List<Book> findAll(String author) {
        if (author != null && !author.isBlank()) {
            return jdbc.query("SELECT * FROM books WHERE author LIKE ?", mapper, "%" + author + "%");
        }
        return jdbc.query("SELECT * FROM books", mapper);
    }

    public Optional<Book> findById(Long id) {
        try {
            return Optional.ofNullable(jdbc.queryForObject("SELECT * FROM books WHERE id = ?", mapper, id));
        } catch (EmptyResultDataAccessException e) {
            return Optional.empty();
        }
    }

    public Optional<Book> update(Long id, Book book) {
        int updated = jdbc.update(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            book.title(), book.author(), book.year(), book.isbn(), id
        );
        if (updated == 0) {
            return Optional.empty();
        }
        return findById(id);
    }

    public boolean delete(Long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id) > 0;
    }
}
