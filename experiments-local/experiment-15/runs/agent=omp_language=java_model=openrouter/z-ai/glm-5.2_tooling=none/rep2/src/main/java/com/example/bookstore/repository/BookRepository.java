package com.example.bookstore.repository;

import java.util.List;
import java.util.Optional;

import com.example.bookstore.model.Book;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class BookRepository {

    private static final RowMapper<Book> MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            rs.getObject("year", Integer.class),
            rs.getString("isbn"));

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                MAPPER, author);
    }

    public Optional<Book> findById(Long id) {
        List<Book> rows = jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                MAPPER, id);
        return rows.isEmpty() ? Optional.empty() : Optional.of(rows.get(0));
    }

    public Book save(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(con -> {
            var ps = con.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    new String[] { "id" });
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            ps.setObject(3, book.getYear());
            ps.setString(4, book.getIsbn());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key != null) {
            book.setId(key.longValue());
        }
        return book;
    }

    public int update(Long id, Book book) {
        return jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn(), id);
    }

    public int deleteById(Long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id);
    }
}
