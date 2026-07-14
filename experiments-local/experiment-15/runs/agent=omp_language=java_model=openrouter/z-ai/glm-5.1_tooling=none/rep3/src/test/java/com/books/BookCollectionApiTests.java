package com.books;

import com.books.model.Book;
import com.books.repository.BookRepository;
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
class BookCollectionApiTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private BookRepository repository;

    @BeforeEach
    void cleanDb() {
        repository.deleteAll();
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createAndGetBook() throws Exception {
        Book book = new Book("1984", "George Orwell", 1949, "978-0451524935");

        // Create
        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("1984"))
                .andExpect(jsonPath("$.author").value("George Orwell"))
                .andExpect(jsonPath("$.year").value(1949))
                .andExpect(jsonPath("$.isbn").value("978-0451524935"))
                .andReturn().getResponse().getContentAsString();

        Long id = objectMapper.readTree(response).get("id").asLong();

        // Get by ID
        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("1984"));
    }

    @Test
    void listAllBooks() throws Exception {
        repository.save(new Book("Dune", "Frank Herbert", 1965, "978-0441172719"));
        repository.save(new Book("Neuromancer", "William Gibson", 1984, "978-0441569595"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)));
    }

    @Test
    void filterByAuthor() throws Exception {
        repository.save(new Book("Dune", "Frank Herbert", 1965, null));
        repository.save(new Book("The Hobbit", "J.R.R. Tolkien", 1937, null));
        repository.save(new Book("The Silmarillion", "J.R.R. Tolkien", 1977, null));

        mockMvc.perform(get("/books").param("author", "J.R.R. Tolkien"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[*].author", everyItem(is("J.R.R. Tolkien"))));
    }

    @Test
    void updateBook() throws Exception {
        Book saved = repository.save(new Book("Old Title", "Author", 2000, null));

        Book updated = new Book("New Title", "New Author", 2020, "978-1234567890");
        mockMvc.perform(put("/books/{id}", saved.getId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updated)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"));
    }

    @Test
    void deleteBook() throws Exception {
        Book saved = repository.save(new Book("ToDelete", "Author", 2020, null));

        mockMvc.perform(delete("/books/{id}", saved.getId()))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/{id}", saved.getId()))
                .andExpect(status().isNotFound());
    }

    @Test
    void getNonexistentBookReturns404() throws Exception {
        mockMvc.perform(get("/books/9999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteNonexistentBookReturns404() throws Exception {
        mockMvc.perform(delete("/books/9999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void createBookWithoutTitleReturns400() throws Exception {
        Book book = new Book("", "Author", 2000, null);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void createBookWithoutAuthorReturns400() throws Exception {
        Book book = new Book("Title", "", 2000, null);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest());
    }
}
