package com.example.books;

import java.util.List;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class BookRepository {

    private final JdbcTemplate jdbc;

    @Autowired
    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<Book> MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            rs.getInt("year"),
            rs.getString("isbn"));

    public Book save(Book book) {
        if (book.getId() == null) {
            String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
            KeyHolder kh = new GeneratedKeyHolder();
            jdbc.update(con -> {
                var ps = con.prepareStatement(sql, new String[]{"id"});
                ps.setString(1, book.getTitle());
                ps.setString(2, book.getAuthor());
                if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
                if (book.getIsbn() != null) ps.setString(4, book.getIsbn()); else ps.setNull(4, java.sql.Types.VARCHAR);
                return ps;
            }, kh);
            Number key = kh.getKey();
            if (key == null) {
                throw new IllegalStateException("Insert failed: no key generated");
            }
            book.setId(key.longValue());
        } else {
            String sql = "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?";
            jdbc.update(sql, book.getTitle(), book.getAuthor(), book.getYear(), book.getIsbn(), book.getId());
        }
        return book;
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
        try {
            return Optional.ofNullable(
                    jdbc.queryForObject("SELECT id, title, author, year, isbn FROM books WHERE id = ?", MAPPER, id));
        } catch (org.springframework.dao.EmptyResultDataAccessException e) {
            return Optional.empty();
        }
    }

    public void deleteById(Long id) {
        jdbc.update("DELETE FROM books WHERE id = ?", id);
    }

    public int count() {
        return jdbc.queryForObject("SELECT COUNT(*) FROM books", Integer.class);
    }
}
