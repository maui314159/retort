package com.example.books;

import org.springframework.dao.EmptyResultDataAccessException;
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

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<Book> ROW_MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            (Integer) rs.getObject("year"),
            rs.getString("isbn")
    );

    public Book save(Book book) {
        KeyHolder keys = new GeneratedKeyHolder();
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO book(title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            return ps;
        }, keys);
        Number key = keys.getKey();
        if (key != null) book.setId(key.longValue());
        return book;
    }

    public List<Book> findAll(String authorFilter) {
        if (authorFilter != null && !authorFilter.isBlank()) {
            return jdbc.query(
                    "SELECT id, title, author, year, isbn FROM book WHERE author = ? ORDER BY id",
                    ROW_MAPPER, authorFilter);
        }
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM book ORDER BY id",
                ROW_MAPPER);
    }

    public Optional<Book> findById(long id) {
        try {
            Book b = jdbc.queryForObject(
                    "SELECT id, title, author, year, isbn FROM book WHERE id = ?",
                    ROW_MAPPER, id);
            return Optional.ofNullable(b);
        } catch (EmptyResultDataAccessException e) {
            return Optional.empty();
        }
    }

    public boolean update(long id, Book book) {
        int rows = jdbc.update(
                "UPDATE book SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.getTitle(),
                book.getAuthor(),
                book.getYear(),
                book.getIsbn(),
                id);
        return rows > 0;
    }

    public boolean delete(long id) {
        int rows = jdbc.update("DELETE FROM book WHERE id = ?", id);
        return rows > 0;
    }
}
