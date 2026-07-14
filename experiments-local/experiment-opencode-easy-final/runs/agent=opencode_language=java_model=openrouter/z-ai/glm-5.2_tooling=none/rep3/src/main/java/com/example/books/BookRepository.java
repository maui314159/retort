package com.example.books;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Optional;

@Repository
public class BookRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<Book> MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            rs.getObject("year") == null ? null : rs.getInt("year"),
            rs.getString("isbn")
    );

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Book save(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() == null) {
                ps.setNull(3, java.sql.Types.INTEGER);
            } else {
                ps.setInt(3, book.getYear());
            }
            ps.setString(4, book.getIsbn());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key != null) {
            book.setId(key.longValue());
        }
        return book;
    }

    public Optional<Book> findById(Long id) {
        List<Book> result = jdbc.query("SELECT id, title, author, year, isbn FROM books WHERE id = ?", MAPPER, id);
        return result.isEmpty() ? Optional.empty() : Optional.of(result.get(0));
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books", MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ?",
                MAPPER, author);
    }

    public int update(Book book) {
        return jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn(), book.getId());
    }

    public int deleteById(Long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id);
    }
}
