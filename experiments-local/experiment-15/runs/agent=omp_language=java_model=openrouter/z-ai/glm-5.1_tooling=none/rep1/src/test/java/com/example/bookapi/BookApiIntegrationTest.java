package com.example.bookapi;

import com.example.bookapi.model.Book;
import com.example.bookapi.repository.BookRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTest {

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired BookRepository repository;

    @BeforeEach
    void clean() {
        repository.deleteAll();
    }

    @Test
    void createAndRetrieveBook() throws Exception {
        Book book = new Book("1984", "George Orwell", 1949, "978-0451524935");
        String json = mapper.writeValueAsString(book);

        // Create
        String location = mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("1984"))
                .andExpect(jsonPath("$.author").value("George Orwell"))
                .andReturn().getResponse().getContentAsString();

        Long id = mapper.readTree(json.contains("\"id\"") ? location : json) // use response
                .get("id").asLong();

        // Retrieve
        mvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("1984"))
                .andExpect(jsonPath("$.year").value(1949));
    }

    @Test
    void listBooksWithAuthorFilter() throws Exception {
        repository.save(new Book("1984", "George Orwell", 1949, "978-0451524935"));
        repository.save(new Book("Brave New World", "Aldous Huxley", 1932, "978-0060850524"));
        repository.save(new Book("Animal Farm", "George Orwell", 1945, "978-0451526342"));

        // All books
        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)));

        // Filter by author
        mvc.perform(get("/books").param("author", "George Orwell"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[*].author", everyItem(is("George Orwell"))));
    }

    @Test
    void updateAndDeleteBook() throws Exception {
        Book saved = repository.save(new Book("Dune", "Frank Herbert", 1965, "978-0441172719"));

        // Update
        Book updated = new Book("Dune", "Frank Herbert", 1965, "978-0441013593");
        mvc.perform(put("/books/{id}", saved.getId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(updated)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isbn").value("978-0441013593"));

        // Delete
        mvc.perform(delete("/books/{id}", saved.getId()))
                .andExpect(status().isNoContent());

        // Verify gone
        mvc.perform(get("/books/{id}", saved.getId()))
                .andExpect(status().isNotFound());
    }

    @Test
    void validationRejectsBlankTitleAndAuthor() throws Exception {
        Book invalid = new Book("", null, 2000, "isbn");
        mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(invalid)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}
