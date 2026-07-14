package com.example;

import java.sql.SQLException;
import java.util.List;

public class BookService implements AutoCloseable {

    private final Database db;

    public BookService(Database db) {
        this.db = db;
    }

    public BookService(String url) throws SQLException {
        this(new Database(url));
    }

    public Book create(Book book) throws ValidationException, SQLException {
        validate(book);
        return db.insert(book);
    }

    public List<Book> list(String author) throws SQLException {
        return db.findAll(author);
    }

    public Book get(Long id) throws SQLException {
        return db.findById(id);
    }

    public Book update(Long id, Book book) throws ValidationException, SQLException, NotFoundException {
        validate(book);
        if (db.findById(id) == null) throw new NotFoundException(id);
        db.update(id, book);
        book.setId(id);
        return book;
    }

    public void delete(Long id) throws SQLException, NotFoundException {
        if (!db.delete(id)) throw new NotFoundException(id);
    }

    private void validate(Book book) throws ValidationException {
        if (book == null) throw new ValidationException("body", "request body is required");
        if (book.getTitle() == null || book.getTitle().isBlank())
            throw new ValidationException("title", "title is required");
        if (book.getAuthor() == null || book.getAuthor().isBlank())
            throw new ValidationException("author", "author is required");
        if (book.getYear() != null && (book.getYear() < 0 || book.getYear() > 9999))
            throw new ValidationException("year", "year must be between 0 and 9999");
    }

    @Override
    public void close() throws SQLException {
        db.close();
    }
}
