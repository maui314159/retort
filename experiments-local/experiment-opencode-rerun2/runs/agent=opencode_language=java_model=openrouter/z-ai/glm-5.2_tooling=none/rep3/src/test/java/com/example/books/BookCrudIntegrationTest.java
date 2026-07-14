package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class BookCrudIntegrationTest extends BaseIntegrationTest {

    private static final ObjectMapper OM = new ObjectMapper();

    private Long seedBook(String title, String author, int year, String isbn) throws Exception {
        String body = OM.writeValueAsString(Map.of(
                "title", title,
                "author", author,
                "year", year,
                "isbn", isbn
        ));
        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return OM.readTree(response).get("id").asLong();
    }

    @Test
    void createGetUpdateDeleteFlow() throws Exception {
        Long id = seedBook("Refactoring", "Martin Fowler", 1999, "9780201485677");

        // GET single
        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Refactoring"))
                .andExpect(jsonPath("$.author").value("Martin Fowler"))
                .andExpect(jsonPath("$.year").value(1999))
                .andExpect(jsonPath("$.isbn").value("9780201485677"));

        // Update
        String update = OM.writeValueAsString(Map.of(
                "title", "Refactoring (2nd)",
                "author", "Martin Fowler",
                "year", 2018,
                "isbn", "9780134757599"
        ));
        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(update))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Refactoring (2nd)"))
                .andExpect(jsonPath("$.year").value(2018));

        // Delete
        mockMvc.perform(delete("/books/{id}", id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isNotFound());
    }

    @Test
    void listSupportsAuthorFilter() throws Exception {
        seedBook("Book A", "Alice", 2020, "a");
        seedBook("Book B", "Bob", 2021, "b");
        seedBook("Book C", "Alice", 2022, "c");

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));

        mockMvc.perform(get("/books").param("author", "Alice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].author").value("Alice"));
    }

    @Test
    void updateNonExistentReturns404() throws Exception {
        String body = OM.writeValueAsString(Map.of(
                "title", "X", "author", "Y", "year", 2000, "isbn", "z"
        ));
        mockMvc.perform(put("/books/{id}", 999999L)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isNotFound());
    }
}
