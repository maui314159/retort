package com.bookapi.repository;

import com.bookapi.model.Book;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

@Repository
public class BookRepository {

    private final JdbcTemplate jdbcTemplate;

    @Autowired
    public BookRepository(DataSource dataSource) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        initializeDatabase();
    }

    private void initializeDatabase() {
        jdbcTemplate.execute(
            "CREATE TABLE IF NOT EXISTS books (" +
            "id INTEGER PRIMARY KEY AUTOINCREMENT," +
            "title TEXT NOT NULL," +
            "author TEXT NOT NULL," +
            "year INTEGER," +
            "isbn TEXT)"
        );
    }

    private final RowMapper<Book> bookRowMapper = (rs, rowNum) -> new Book(
        rs.getLong("id"),
        rs.getString("title"),
        rs.getString("author"),
        rs.getObject("year", Integer.class),
        rs.getString("isbn")
    );

    public Book save(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                Statement.RETURN_GENERATED_KEYS
            );
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) {
                ps.setInt(3, book.getYear());
            } else {
                ps.setNull(3, java.sql.Types.INTEGER);
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

    public List<Book> findAll() {
        return jdbcTemplate.query("SELECT * FROM books ORDER BY id", bookRowMapper);
    }

    public List<Book> findByAuthor(String author) {
        return jdbcTemplate.query(
            "SELECT * FROM books WHERE author LIKE ? ORDER BY id",
            bookRowMapper,
            "%" + author + "%"
        );
    }

    public Optional<Book> findById(Long id) {
        List<Book> books = jdbcTemplate.query(
            "SELECT * FROM books WHERE id = ?",
            bookRowMapper,
            id
        );
        return books.isEmpty() ? Optional.empty() : Optional.of(books.get(0));
    }

    public Book update(Book book) {
        jdbcTemplate.update(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            book.getTitle(),
            book.getAuthor(),
            book.getYear(),
            book.getIsbn(),
            book.getId()
        );
        return book;
    }

    public boolean deleteById(Long id) {
        return jdbcTemplate.update("DELETE FROM books WHERE id = ?", id) > 0;
    }
}
