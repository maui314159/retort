package com.example.bookapi.repository;

import java.util.List;
import java.util.Optional;

import com.example.bookapi.model.Book;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

/**
 * JDBC-backed persistence for {@link Book}.
 */
@Repository
public class BookRepository {

    private static final RowMapper<Book> BOOK_MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            rs.getObject("year", Integer.class),
            rs.getString("isbn")
    );

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Book save(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(con -> {
            var ps = con.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    new String[]{"id"});
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            ps.setObject(3, book.year());
            ps.setString(4, book.isbn());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to retrieve generated id");
        }
        return new Book(key.longValue(), book.title(), book.author(), book.year(), book.isbn());
    }

    public Optional<Book> update(Long id, Book book) {
        int affected = jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.title(), book.author(), book.year(), book.isbn(), id);
        if (affected == 0) {
            return Optional.empty();
        }
        return Optional.of(new Book(id, book.title(), book.author(), book.year(), book.isbn()));
    }

    public Optional<Book> findById(Long id) {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                rs -> rs.next() ? Optional.of(BOOK_MAPPER.mapRow(rs, 1)) : Optional.empty(), id);
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", BOOK_MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                BOOK_MAPPER, author);
    }

    public boolean deleteById(Long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id) > 0;
    }
}
