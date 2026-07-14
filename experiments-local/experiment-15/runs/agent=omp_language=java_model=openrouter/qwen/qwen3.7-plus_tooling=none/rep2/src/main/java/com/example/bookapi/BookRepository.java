package com.example.bookapi;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Types;
import java.util.List;
import java.util.Optional;

@Repository
public class BookRepository {
    private final JdbcTemplate jdbcTemplate;

    public BookRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    private final RowMapper<Book> rowMapper = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            rs.getObject("year", Integer.class),
            rs.getString("isbn")
    );

    public Book save(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            if (book.year() != null) {
                ps.setInt(3, book.year());
            } else {
                ps.setNull(3, Types.INTEGER);
            }
            ps.setString(4, book.isbn());
            return ps;
        }, keyHolder);
        
        Long id = keyHolder.getKey().longValue();
        return new Book(id, book.title(), book.author(), book.year(), book.isbn());
    }

    public List<Book> findAll(String authorFilter) {
        if (authorFilter != null && !authorFilter.trim().isEmpty()) {
            return jdbcTemplate.query("SELECT * FROM books WHERE author LIKE ?", rowMapper, "%" + authorFilter + "%");
        }
        return jdbcTemplate.query("SELECT * FROM books", rowMapper);
    }

    public Optional<Book> findById(Long id) {
        try {
            Book book = jdbcTemplate.queryForObject("SELECT * FROM books WHERE id = ?", rowMapper, id);
            return Optional.of(book);
        } catch (EmptyResultDataAccessException e) {
            return Optional.empty();
        }
    }

    public boolean update(Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        int rows = jdbcTemplate.update(sql, book.title(), book.author(), book.year(), book.isbn(), book.id());
        return rows > 0;
    }

    public boolean deleteById(Long id) {
        int rows = jdbcTemplate.update("DELETE FROM books WHERE id = ?", id);
        return rows > 0;
    }
}