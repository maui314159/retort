package com.bookcollection.repository;

import com.bookcollection.model.Book;
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
    private final JdbcTemplate jdbcTemplate;

    public BookRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        initializeDatabase();
    }

    private void initializeDatabase() {
        String createTableSql = "CREATE TABLE IF NOT EXISTS books (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "title TEXT NOT NULL," +
                "author TEXT NOT NULL," +
                "year INTEGER," +
                "isbn TEXT)";
        jdbcTemplate.execute(createTableSql);
    }

    private final RowMapper<Book> bookRowMapper = (rs, rowNum) -> {
        Book book = new Book();
        book.setId(rs.getLong("id"));
        book.setTitle(rs.getString("title"));
        book.setAuthor(rs.getString("author"));
        int yearInt = rs.getInt("year");
        book.setYear(rs.wasNull() ? null : yearInt);
        book.setIsbn(rs.getString("isbn"));
        return book;
    };

    public Book save(Book book) {
        if (book.getId() == null) {
            String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
            KeyHolder keyHolder = new GeneratedKeyHolder();
            jdbcTemplate.update(connection -> {
                PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, book.getTitle());
                ps.setString(2, book.getAuthor());
                ps.setObject(3, book.getYear());
                ps.setString(4, book.getIsbn());
                return ps;
            }, keyHolder);
            book.setId(((Number) keyHolder.getKey()).longValue());
            return book;
        } else {
            String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
            jdbcTemplate.update(sql, book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn(), book.getId());
            return book;
        }
    }

    public List<Book> findAll(String authorFilter) {
        if (authorFilter != null && !authorFilter.isEmpty()) {
            String sql = "SELECT * FROM books WHERE author LIKE ?";
            return jdbcTemplate.query(sql, bookRowMapper, "%" + authorFilter + "%");
        } else {
            String sql = "SELECT * FROM books";
            return jdbcTemplate.query(sql, bookRowMapper);
        }
    }

    public Optional<Book> findById(Long id) {
        String sql = "SELECT * FROM books WHERE id = ?";
        List<Book> books = jdbcTemplate.query(sql, bookRowMapper, id);
        return books.isEmpty() ? Optional.empty() : Optional.of(books.get(0));
    }

    public void deleteById(Long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        jdbcTemplate.update(sql, id);
    }
}
