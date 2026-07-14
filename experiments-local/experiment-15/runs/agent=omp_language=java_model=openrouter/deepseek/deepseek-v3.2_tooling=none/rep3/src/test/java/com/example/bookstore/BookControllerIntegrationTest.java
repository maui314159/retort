package com.example.bookstore;

import com.example.bookstore.model.Book;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookControllerIntegrationTest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void testCreateAndRetrieveBook() throws Exception {
        // Create a new book
        Book newBook = new Book("The Great Gatsby", "F. Scott Fitzgerald", 1925, "9780743273565");
        String bookJson = objectMapper.writeValueAsString(newBook);

        String response = mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(bookJson))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"))
                .andExpect(jsonPath("$.author").value("F. Scott Fitzgerald"))
                .andReturn()
                .getResponse()
                .getContentAsString();

        Book createdBook = objectMapper.readValue(response, Book.class);
        assertThat(createdBook.getId()).isNotNull();

        // Retrieve the book by ID
        mockMvc.perform(get("/books/{id}", createdBook.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"))
                .andExpect(jsonPath("$.author").value("F. Scott Fitzgerald"));
    }

    @Test
    void testGetAllBooks() throws Exception {
        // Create two books
        Book book1 = new Book("1984", "George Orwell", 1949, "9780451524935");
        Book book2 = new Book("Brave New World", "Aldous Huxley", 1932, "9780060850524");

        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(book1)))
                .andExpect(status().isCreated());

        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(book2)))
                .andExpect(status().isCreated());

        // Get all books
        String response = mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();

        List<Book> books = objectMapper.readValue(response,
                objectMapper.getTypeFactory().constructCollectionType(List.class, Book.class));
        assertThat(books).isNotEmpty();
    }

    @Test
    void testGetBooksByAuthor() throws Exception {
        // Create books by same author
        Book book1 = new Book("The Hobbit", "J.R.R. Tolkien", 1937, "9780547928227");
        Book book2 = new Book("The Fellowship of the Ring", "J.R.R. Tolkien", 1954, "9780547928210");

        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(book1)))
                .andExpect(status().isCreated());

        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(book2)))
                .andExpect(status().isCreated());

        // Filter by author
        String response = mockMvc.perform(get("/books?author=J.R.R. Tolkien"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();

        List<Book> books = objectMapper.readValue(response,
                objectMapper.getTypeFactory().constructCollectionType(List.class, Book.class));
        assertThat(books).hasSize(2);
        assertThat(books).allMatch(book -> book.getAuthor().equals("J.R.R. Tolkien"));
    }

    @Test
    void testUpdateBook() throws Exception {
        // Create a book
        Book newBook = new Book("Old Title", "Old Author", 2000, "1111111111");
        String createResponse = mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newBook)))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();

        Book createdBook = objectMapper.readValue(createResponse, Book.class);

        // Update the book
        Book updatedBook = new Book("New Title", "New Author", 2024, "2222222222");
        mockMvc.perform(put("/books/{id}", createdBook.getId())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updatedBook)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"));
    }

    @Test
    void testDeleteBook() throws Exception {
        // Create a book
        Book newBook = new Book("To Delete", "Author", 2020, "3333333333");
        String createResponse = mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newBook)))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();

        Book createdBook = objectMapper.readValue(createResponse, Book.class);

        // Delete the book
        mockMvc.perform(delete("/books/{id}", createdBook.getId()))
                .andExpect(status().isNoContent());

        // Verify it's gone
        mockMvc.perform(get("/books/{id}", createdBook.getId()))
                .andExpect(status().isNotFound());
    }

    @Test
    void testHealthEndpoint() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(content().string("OK"));
    }

    @Test
    void testValidation() throws Exception {
        // Missing required fields
        Book invalidBook = new Book(null, null, null, "4444444444");
        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidBook)))
                .andExpect(status().isBadRequest());
    }
}