package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:sqlite::memory:",
        "spring.datasource.driver-class-name=org.sqlite.JDBC",
        "spring.datasource.hikari.maximum-pool-size=1",
        "spring.sql.init.mode=always"
})
class BookApiIntegrationTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    JdbcTemplate jdbc;

    @BeforeEach
    void reset() {
        jdbc.update("DELETE FROM books");
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createGetListUpdateDeleteLifecycle() throws Exception {
        String body = """
                {"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
                """;
        String location = mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andReturn().getResponse().getHeader("Location");

        assertThat(location).startsWith("/books/");

        Long id = extractId(location);

        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.author").value("Frank Herbert"));

        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("Dune"));

        String updateBody = """
                {"title":"Dune Updated","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
                """;
        mvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(updateBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune Updated"));

        mvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void authorFilterReturnsMatchingBooks() throws Exception {
        createBook("Foundation", "Isaac Asimov", 1951);
        createBook("I, Robot", "Isaac Asimov", 1950);
        createBook("Dune", "Frank Herbert", 1965);

        mvc.perform(get("/books").param("author", "Isaac Asimov"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        String invalid = """
                {"title":"","author":"","year":1900}
                """;
        mvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(invalid))
                .andExpect(status().isBadRequest());
    }

    @Test
    void deleteUnknownReturns404() throws Exception {
        mvc.perform(delete("/books/999999"))
                .andExpect(status().isNotFound());
    }

    private void createBook(String title, String author, int year) throws Exception {
        mvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"" + title + "\",\"author\":\"" + author + "\",\"year\":" + year + "}"));
    }

    private static Long extractId(String location) {
        String s = location.substring(location.lastIndexOf('/') + 1);
        return Long.parseLong(s);
    }
}
