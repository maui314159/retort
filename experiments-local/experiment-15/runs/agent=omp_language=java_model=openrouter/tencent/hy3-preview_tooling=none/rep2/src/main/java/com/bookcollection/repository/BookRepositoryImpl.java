package com.bookcollection.repository;

import com.bookcollection.model.Book;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

@Repository
public class BookRepositoryImpl implements BookRepository {
    private final JdbcTemplate jdbcTemplate;

    public BookRepositoryImpl(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public Book save(Book book) {
        if (book.getId() == null) {
            jdbcTemplate.update(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn()
            );
            Long id = jdbcTemplate.queryForObject("SELECT last_insert_rowid()", Long.class);
            book.setId(id);
        } else {
            jdbcTemplate.update(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                    book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn(), book.getId()
            );
        }
        return book;
    }

    @Override
    public List<Book> findAll() {
        return jdbcTemplate.query("SELECT * FROM books", new BookRowMapper());
    }

    @Override
    public List<Book> findByAuthor(String author) {
        return jdbcTemplate.query(
                "SELECT * FROM books WHERE author = ?",
                new BookRowMapper(),
                author
        );
    }

    @Override
    public Book findById(Long id) {
        List<Book> books = jdbcTemplate.query(
                "SELECT * FROM books WHERE id = ?",
                new BookRowMapper(),
                id
        );
        return books.isEmpty() ? null : books.get(0);
    }

    @Override
    public void deleteById(Long id) {
        jdbcTemplate.update("DELETE FROM books WHERE id = ?", id);
    }

    private static class BookRowMapper implements RowMapper<Book> {
        @Override
        public Book mapRow(ResultSet rs, int rowNum) throws SQLException {
            Book book = new Book();
            book.setId(rs.getLong("id"));
            book.setTitle(rs.getString("title"));
            book.setAuthor(rs.getString("author"));
            book.setYear(rs.getInt("year"));
            if (rs.wasNull()) {
                book.setYear(null);
            }
            book.setIsbn(rs.getString("isbn"));
            return book;
        }
    }
}