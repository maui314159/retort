package com.example.bookapi.controller;

import com.example.bookapi.dto.BookDTO;
import com.example.bookapi.entity.Book;
import com.example.bookapi.service.BookService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Arrays;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(BookController.class)
class BookControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @MockBean
    private BookService bookService;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    private Book sampleBook;
    private BookDTO sampleBookDTO;
    
    @BeforeEach
    void setUp() {
        sampleBook = new Book("The Great Gatsby", "F. Scott Fitzgerald", 1925, "9780743273565");
        sampleBook.setId(1L);
        
        sampleBookDTO = new BookDTO("The Great Gatsby", "F. Scott Fitzgerald", 1925, "9780743273565");
    }
    
    @Test
    void testGetAllBooks() throws Exception {
        Mockito.when(bookService.getAllBooks())
                .thenReturn(Arrays.asList(sampleBook));
        
        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("The Great Gatsby"))
                .andExpect(jsonPath("$[0].author").value("F. Scott Fitzgerald"));
    }
    
    @Test
    void testGetBooksByAuthor() throws Exception {
        Mockito.when(bookService.getBooksByAuthor("Fitzgerald"))
                .thenReturn(Arrays.asList(sampleBook));
        
        mockMvc.perform(get("/books").param("author", "Fitzgerald"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("The Great Gatsby"));
    }
    
    @Test
    void testGetBookById_Success() throws Exception {
        Mockito.when(bookService.getBookById(1L))
                .thenReturn(Optional.of(sampleBook));
        
        mockMvc.perform(get("/books/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"))
                .andExpect(jsonPath("$.author").value("F. Scott Fitzgerald"));
    }
    
    @Test
    void testGetBookById_NotFound() throws Exception {
        Mockito.when(bookService.getBookById(99L))
                .thenReturn(Optional.empty());
        
        mockMvc.perform(get("/books/99"))
                .andExpect(status().isNotFound());
    }
    
    @Test
    void testCreateBook_Success() throws Exception {
        Mockito.when(bookService.createBook(any(BookDTO.class)))
                .thenReturn(sampleBook);
        
        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleBookDTO)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"))
                .andExpect(jsonPath("$.author").value("F. Scott Fitzgerald"));
    }
    
    @Test
    void testCreateBook_ValidationFailure() throws Exception {
        BookDTO invalidBookDTO = new BookDTO("", "", null, "");
        
        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidBookDTO)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists())
                .andExpect(jsonPath("$.errors.author").exists())
                .andExpect(jsonPath("$.errors.year").exists());
    }
    
    @Test
    void testUpdateBook_Success() throws Exception {
        Mockito.when(bookService.updateBook(eq(1L), any(BookDTO.class)))
                .thenReturn(Optional.of(sampleBook));
        
        mockMvc.perform(put("/books/1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleBookDTO)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"));
    }
    
    @Test
    void testUpdateBook_NotFound() throws Exception {
        Mockito.when(bookService.updateBook(eq(99L), any(BookDTO.class)))
                .thenReturn(Optional.empty());
        
        mockMvc.perform(put("/books/99")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleBookDTO)))
                .andExpect(status().isNotFound());
    }
    
    @Test
    void testDeleteBook_Success() throws Exception {
        Mockito.when(bookService.deleteBook(1L))
                .thenReturn(true);
        
        mockMvc.perform(delete("/books/1"))
                .andExpect(status().isNoContent());
    }
    
    @Test
    void testDeleteBook_NotFound() throws Exception {
        Mockito.when(bookService.deleteBook(99L))
                .thenReturn(false);
        
        mockMvc.perform(delete("/books/99"))
                .andExpect(status().isNotFound());
    }
}