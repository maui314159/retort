package com.example.books;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private BookRepository repository;

    @BeforeEach
    void cleanDatabase() {
        repository.initSchema();
        repository.findAll().forEach(b -> repository.deleteById(b.getId()));
    }

    private static String extractId(String createdJson) {
        return com.jayway.jsonpath.JsonPath.parse(createdJson).read("$.id").toString();
    }

    @Test
    void createAndRetrieveBook_returnsCreatedAndPersistedBook() throws Exception {
        String body = "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";

        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Frank Herbert"))
                .andReturn().getResponse().getContentAsString();

        String id = extractId(created);

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.isbn").value("9780441172719"));
    }

    @Test
    void listBooks_supportsAuthorFilter() throws Exception {
        repository.save(new Book(null, "Dune", "Frank Herbert", 1965, "111"));
        repository.save(new Book(null, "Foundation", "Isaac Asimov", 1951, "222"));
        repository.save(new Book(null, "Children of Dune", "Frank Herbert", 1976, "333"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));

        mockMvc.perform(get("/books").param("author", "Frank Herbert"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[*].author").value(
                        org.hamcrest.Matchers.everyItem(org.hamcrest.Matchers.equalTo("Frank Herbert"))));
    }

    @Test
    void createBook_withMissingTitleReturns400() throws Exception {
        String body = "{\"author\":\"Frank Herbert\",\"year\":1965}";

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists());
    }

    @Test
    void createBook_withMissingAuthorReturns400() throws Exception {
        String body = "{\"title\":\"Dune\",\"year\":1965}";

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.author").exists());
    }

    @Test
    void getBook_notFoundReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateBook_existingUpdatesAndReturns200() throws Exception {
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965}"))
                .andReturn().getResponse().getContentAsString();
        String id = extractId(created);

        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Dune Updated\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"999\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune Updated"))
                .andExpect(jsonPath("$.isbn").value("999"));
    }

    @Test
    void updateBook_nonExistingReturns404() throws Exception {
        mockMvc.perform(put("/books/888888")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"X\",\"author\":\"Y\"}"))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteBook_existingReturns204() throws Exception {
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}"))
                .andReturn().getResponse().getContentAsString();
        String id = extractId(created);

        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteBook_nonExistingReturns404() throws Exception {
        mockMvc.perform(delete("/books/777777"))
                .andExpect(status().isNotFound());
    }

    @Test
    void healthCheck_returnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}
