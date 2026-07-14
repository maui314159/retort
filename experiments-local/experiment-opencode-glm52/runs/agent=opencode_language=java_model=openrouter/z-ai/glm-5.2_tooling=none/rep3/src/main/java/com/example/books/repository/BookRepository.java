package com.example.books.repository;

import java.util.List;
import java.util.Optional;

import com.example.books.model.Book;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class BookRepository {

    private static final RowMapper<Book> ROW_MAPPER = (rs, rowNum) -> new Book(
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

    public List<Book> findAll(String author) {
        if (author == null || author.isBlank()) {
            return jdbc.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", ROW_MAPPER);
        }
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                ROW_MAPPER,
                author
        );
    }

    public Optional<Book> findById(Long id) {
        List<Book> rows = jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                ROW_MAPPER,
                id
        );
        return rows.isEmpty() ? Optional.empty() : Optional.of(rows.get(0));
    }

    public Book save(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(con -> {
            var ps = con.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    new String[]{"id"}
            );
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            if (book.year() == null) {
                ps.setNull(3, java.sql.Types.INTEGER);
            } else {
                ps.setInt(3, book.year());
            }
            ps.setString(4, book.isbn());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to retrieve generated id");
        }
        return book.withId(key.longValue());
    }

    public boolean update(Long id, Book book) {
        int affected = jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.title(),
                book.author(),
                book.year(),
                book.isbn(),
                id
        );
        return affected > 0;
    }

    public boolean deleteById(Long id) {
        int affected = jdbc.update("DELETE FROM books WHERE id = ?", id);
        return affected > 0;
    }
}
