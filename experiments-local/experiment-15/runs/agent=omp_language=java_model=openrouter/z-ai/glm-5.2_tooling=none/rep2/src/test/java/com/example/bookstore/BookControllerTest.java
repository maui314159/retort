package com.example.bookstore;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(locations = "classpath:application-test.properties")
@Transactional
class BookControllerTest {

    @Autowired
    private MockMvc mvc;

    @Autowired
    private JdbcTemplate jdbc;

    @BeforeEach
    void clean() {
        jdbc.update("DELETE FROM books");
    }

    private String bookJson(String title, String author, Integer year, String isbn) {
        return """
                {"title":"%s","author":"%s","year":%d,"isbn":"%s"}
                """.formatted(title, author, year, isbn);
    }

    @Test
    void healthReturnsOk() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void createBookReturnsCreatedWithId() throws Exception {
        mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("1984", "George Orwell", 1949, "978-0451524935")))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("1984"))
                .andExpect(jsonPath("$.author").value("George Orwell"))
                .andExpect(jsonPath("$.year").value(1949))
                .andExpect(jsonPath("$.isbn").value("978-0451524935"));
    }

    @Test
    void validationRejectsMissingTitleAndAuthor() throws Exception {
        mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"year\":2000}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists())
                .andExpect(jsonPath("$.errors.author").exists());
    }

    @Test
    void listReturnsAllBooksAndSupportsAuthorFilter() throws Exception {
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(bookJson("1984", "George Orwell", 1949, "a"))).andExpect(status().isCreated());
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(bookJson("Animal Farm", "George Orwell", 1945, "b"))).andExpect(status().isCreated());
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(bookJson("Dune", "Frank Herbert", 1965, "c"))).andExpect(status().isCreated());

        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));

        mvc.perform(get("/books").param("author", "George Orwell"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }

    @Test
    void getBookByIdReturnsBook() throws Exception {
        String created = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Dune", "Frank Herbert", 1965, "c")))
                .andReturn().getResponse().getContentAsString();
        long id = Long.parseLong(created.replaceAll(".*\"id\":(\\d+).*", "$1"));

        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune"));
    }

    @Test
    void getUnknownBookReturns404() throws Exception {
        mvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateBookChangesFields() throws Exception {
        String created = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Dune", "Frank Herbert", 1965, "c")))
                .andReturn().getResponse().getContentAsString();
        long id = Long.parseLong(created.replaceAll(".*\"id\":(\\d+).*", "$1"));

        mvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Dune Updated", "Frank Herbert", 1966, "c2")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune Updated"))
                .andExpect(jsonPath("$.year").value(1966));

        mvc.perform(get("/books/" + id))
                .andExpect(jsonPath("$.isbn").value("c2"));
    }

    @Test
    void deleteBookRemovesItAnd404sAfter() throws Exception {
        String created = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Dune", "Frank Herbert", 1965, "c")))
                .andReturn().getResponse().getContentAsString();
        long id = Long.parseLong(created.replaceAll(".*\"id\":(\\d+).*", "$1"));

        mvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteUnknownBookReturns404() throws Exception {
        mvc.perform(delete("/books/999999"))
                .andExpect(status().isNotFound());
    }
}
