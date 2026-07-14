package com.example.bookapi.service;

import com.example.bookapi.dto.BookDTO;
import com.example.bookapi.entity.Book;
import com.example.bookapi.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class BookServiceTest {
    
    @Mock
    private BookRepository bookRepository;
    
    @InjectMocks
    private BookService bookService;
    
    private Book sampleBook;
    private BookDTO sampleBookDTO;
    
    @BeforeEach
    void setUp() {
        sampleBook = new Book("The Great Gatsby", "F. Scott Fitzgerald", 1925, "9780743273565");
        sampleBook.setId(1L);
        
        sampleBookDTO = new BookDTO("The Great Gatsby", "F. Scott Fitzgerald", 1925, "9780743273565");
    }
    
    @Test
    void testGetAllBooks() {
        List<Book> books = Arrays.asList(sampleBook);
        when(bookRepository.findAll()).thenReturn(books);
        
        List<Book> result = bookService.getAllBooks();
        
        assertEquals(1, result.size());
        assertEquals("The Great Gatsby", result.get(0).getTitle());
        verify(bookRepository, times(1)).findAll();
    }
    
    @Test
    void testGetBooksByAuthor() {
        List<Book> books = Arrays.asList(sampleBook);
        when(bookRepository.findByAuthorContainingIgnoreCase("Fitzgerald")).thenReturn(books);
        
        List<Book> result = bookService.getBooksByAuthor("Fitzgerald");
        
        assertEquals(1, result.size());
        assertEquals("F. Scott Fitzgerald", result.get(0).getAuthor());
        verify(bookRepository, times(1)).findByAuthorContainingIgnoreCase("Fitzgerald");
    }
    
    @Test
    void testGetBookById_Success() {
        when(bookRepository.findById(1L)).thenReturn(Optional.of(sampleBook));
        
        Optional<Book> result = bookService.getBookById(1L);
        
        assertTrue(result.isPresent());
        assertEquals("The Great Gatsby", result.get().getTitle());
        verify(bookRepository, times(1)).findById(1L);
    }
    
    @Test
    void testGetBookById_NotFound() {
        when(bookRepository.findById(99L)).thenReturn(Optional.empty());
        
        Optional<Book> result = bookService.getBookById(99L);
        
        assertFalse(result.isPresent());
        verify(bookRepository, times(1)).findById(99L);
    }
    
    @Test
    void testCreateBook() {
        when(bookRepository.save(any(Book.class))).thenReturn(sampleBook);
        
        Book result = bookService.createBook(sampleBookDTO);
        
        assertEquals("The Great Gatsby", result.getTitle());
        assertEquals("F. Scott Fitzgerald", result.getAuthor());
        assertEquals(1925, result.getYear());
        assertEquals("9780743273565", result.getIsbn());
        verify(bookRepository, times(1)).save(any(Book.class));
    }
    
    @Test
    void testUpdateBook_Success() {
        when(bookRepository.findById(1L)).thenReturn(Optional.of(sampleBook));
        when(bookRepository.save(any(Book.class))).thenReturn(sampleBook);
        
        Optional<Book> result = bookService.updateBook(1L, sampleBookDTO);
        
        assertTrue(result.isPresent());
        assertEquals("The Great Gatsby", result.get().getTitle());
        verify(bookRepository, times(1)).findById(1L);
        verify(bookRepository, times(1)).save(any(Book.class));
    }
    
    @Test
    void testUpdateBook_NotFound() {
        when(bookRepository.findById(99L)).thenReturn(Optional.empty());
        
        Optional<Book> result = bookService.updateBook(99L, sampleBookDTO);
        
        assertFalse(result.isPresent());
        verify(bookRepository, times(1)).findById(99L);
        verify(bookRepository, never()).save(any(Book.class));
    }
    
    @Test
    void testDeleteBook_Success() {
        when(bookRepository.existsById(1L)).thenReturn(true);
        
        boolean result = bookService.deleteBook(1L);
        
        assertTrue(result);
        verify(bookRepository, times(1)).existsById(1L);
        verify(bookRepository, times(1)).deleteById(1L);
    }
    
    @Test
    void testDeleteBook_NotFound() {
        when(bookRepository.existsById(99L)).thenReturn(false);
        
        boolean result = bookService.deleteBook(99L);
        
        assertFalse(result);
        verify(bookRepository, times(1)).existsById(99L);
        verify(bookRepository, never()).deleteById(anyLong());
    }
}