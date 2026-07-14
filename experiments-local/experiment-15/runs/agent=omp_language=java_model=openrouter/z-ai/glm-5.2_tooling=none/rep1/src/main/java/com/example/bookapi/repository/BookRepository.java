package com.example.bookapi.repository;

import java.util.List;
import java.util.Optional;

import com.example.bookapi.model.Book;
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
            rs.getString("isbn"));

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Book save(String title, String author, Integer year, String isbn) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(con -> {
            var ps = con.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    new String[]{"id"});
            ps.setString(1, title);
            ps.setString(2, author);
            if (year == null) {
                ps.setNull(3, java.sql.Types.INTEGER);
            } else {
                ps.setInt(3, year);
            }
            ps.setString(4, isbn);
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to retrieve generated id");
        }
        return findById(key.longValue()).orElseThrow();
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", ROW_MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                ROW_MAPPER, author);
    }

    public Optional<Book> findById(Long id) {
        List<Book> result = jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                ROW_MAPPER, id);
        return result.isEmpty() ? Optional.empty() : Optional.of(result.get(0));
    }

    /** @return true if a row was updated. */
    public boolean update(Long id, String title, String author, Integer year, String isbn) {
        int affected = jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                title, author, year, isbn, id);
        return affected > 0;
    }

    /** @return true if a row was deleted. */
    public boolean deleteById(Long id) {
        int affected = jdbc.update("DELETE FROM books WHERE id = ?", id);
        return affected > 0;
    }
}
