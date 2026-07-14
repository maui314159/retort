package com.bookcollection.controller;

import com.bookcollection.exception.GlobalExceptionHandler;
import com.bookcollection.model.Book;
import com.bookcollection.repository.BookRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.Arrays;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@ExtendWith(MockitoExtension.class)
class BookControllerTest {
    private MockMvc mockMvc;
    private ObjectMapper objectMapper;

    @Mock
    private BookRepository bookRepository;

    @InjectMocks
    private BookController bookController;

    @InjectMocks
    private HealthController healthController;

    @InjectMocks
    private GlobalExceptionHandler globalExceptionHandler;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        mockMvc = MockMvcBuilders.standaloneSetup(bookController, healthController)
                .setControllerAdvice(globalExceptionHandler)
                .build();
    }

    @Test
    void createBook_returnsCreatedBook() throws Exception {
        Book book = new Book();
        book.setTitle("Test Book");
        book.setAuthor("Test Author");
        book.setYear(2023);
        book.setIsbn("1234567890");

        when(bookRepository.save(any(Book.class))).thenReturn(book);

        mockMvc.perform(post("/books")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Test Book"))
                .andExpect(jsonPath("$.author").value("Test Author"));
    }

    @Test
    void getAllBooks_returnsListOfBooks() throws Exception {
        Book book1 = new Book();
        book1.setId(1L);
        book1.setTitle("Book 1");
        book1.setAuthor("Author 1");

        Book book2 = new Book();
        book2.setId(2L);
        book2.setTitle("Book 2");
        book2.setAuthor("Author 2");

        when(bookRepository.findAll()).thenReturn(Arrays.asList(book1, book2));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].title").value("Book 1"))
                .andExpect(jsonPath("$[1].title").value("Book 2"));
    }

    @Test
    void getAllBooks_withAuthorFilter_returnsFilteredBooks() throws Exception {
        Book book = new Book();
        book.setId(1L);
        book.setTitle("Book 1");
        book.setAuthor("Author 1");

        when(bookRepository.findByAuthor("Author 1")).thenReturn(Arrays.asList(book));

        mockMvc.perform(get("/books").param("author", "Author 1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].author").value("Author 1"));
    }

    @Test
    void getBookById_returnsBookIfExists() throws Exception {
        Book book = new Book();
        book.setId(1L);
        book.setTitle("Test Book");
        book.setAuthor("Test Author");

        when(bookRepository.findById(1L)).thenReturn(book);

        mockMvc.perform(get("/books/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.title").value("Test Book"));
    }

    @Test
    void getBookById_returnsNotFoundIfNotExists() throws Exception {
        when(bookRepository.findById(1L)).thenReturn(null);

        mockMvc.perform(get("/books/1"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateBook_returnsUpdatedBook() throws Exception {
        Book existingBook = new Book();
        existingBook.setId(1L);
        existingBook.setTitle("Old Title");
        existingBook.setAuthor("Old Author");

        Book updatedDetails = new Book();
        updatedDetails.setTitle("New Title");
        updatedDetails.setAuthor("New Author");
        updatedDetails.setYear(2024);
        updatedDetails.setIsbn("0987654321");

        when(bookRepository.findById(1L)).thenReturn(existingBook);
        when(bookRepository.save(any(Book.class))).thenReturn(existingBook);

        mockMvc.perform(put("/books/1")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(updatedDetails)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"));
    }

    @Test
    void deleteBook_returnsNoContent() throws Exception {
        Book existingBook = new Book();
        existingBook.setId(1L);

        when(bookRepository.findById(1L)).thenReturn(existingBook);
        doNothing().when(bookRepository).deleteById(1L);

        mockMvc.perform(delete("/books/1"))
                .andExpect(status().isNoContent());
    }

    @Test
    void createBook_withMissingTitle_returnsBadRequest() throws Exception {
        Book book = new Book();
        book.setAuthor("Test Author");

        mockMvc.perform(post("/books")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Title is required"));
    }

    @Test
    void healthCheck_returnsUpStatus() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}