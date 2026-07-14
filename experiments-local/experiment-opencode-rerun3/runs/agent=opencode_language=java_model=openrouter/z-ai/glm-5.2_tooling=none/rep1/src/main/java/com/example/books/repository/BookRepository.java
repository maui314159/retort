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

    private static final String CREATE_TABLE_SQL =
            "CREATE TABLE IF NOT EXISTS books (" +
            "  id INTEGER PRIMARY KEY AUTOINCREMENT," +
            "  title TEXT NOT NULL," +
            "  author TEXT NOT NULL," +
            "  year INTEGER," +
            "  isbn TEXT" +
            ")";

    private static final String INSERT_SQL =
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";

    private static final String UPDATE_SQL =
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";

    private static final String DELETE_SQL =
            "DELETE FROM books WHERE id = ?";

    private static final String SELECT_BY_ID_SQL =
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?";

    private static final String SELECT_ALL_SQL =
            "SELECT id, title, author, year, isbn FROM books ORDER BY id";

    private static final String SELECT_BY_AUTHOR_SQL =
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id";

    private static final String DELETE_ALL_SQL =
            "DELETE FROM books";

    private final JdbcTemplate jdbcTemplate;

    private static final RowMapper<Book> BOOK_ROW_MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            (Integer) rs.getObject("year"),
            rs.getString("isbn"));

    public BookRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void initSchema() {
        jdbcTemplate.execute(CREATE_TABLE_SQL);
    }

    public Book save(String title, String author, Integer year, String isbn) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(con -> {
            var ps = con.prepareStatement(INSERT_SQL, new String[] { "id" });
            ps.setString(1, title);
            ps.setString(2, author);
            if (year != null) {
                ps.setInt(3, year);
            } else {
                ps.setNull(3, java.sql.Types.INTEGER);
            }
            ps.setString(4, isbn);
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to retrieve generated id");
        }
        return new Book(key.longValue(), title, author, year, isbn);
    }

    public Optional<Book> findById(Long id) {
        return jdbcTemplate.query(SELECT_BY_ID_SQL, BOOK_ROW_MAPPER, id)
                .stream()
                .findFirst();
    }

    public List<Book> findAll() {
        return jdbcTemplate.query(SELECT_ALL_SQL, BOOK_ROW_MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbcTemplate.query(SELECT_BY_AUTHOR_SQL, BOOK_ROW_MAPPER, author);
    }

    public boolean update(Long id, String title, String author, Integer year, String isbn) {
        int rows = jdbcTemplate.update(UPDATE_SQL, title, author,
                (year != null ? year : null), isbn, id);
        return rows > 0;
    }

    public boolean deleteById(Long id) {
        int rows = jdbcTemplate.update(DELETE_SQL, id);
        return rows > 0;
    }

    public void deleteAll() {
        jdbcTemplate.update(DELETE_ALL_SQL);
    }
}
