package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> "jdbc:sqlite:file:testdb?mode=memory&cache=shared");
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "create-drop");
    }

    private String createBook(String title, String author, Integer year, String isbn) throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("title", title);
        body.put("author", author);
        if (year != null) body.put("year", year);
        if (isbn != null) body.put("isbn", isbn);
        String json = objectMapper.writeValueAsString(body);
        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return objectMapper.readTree(response).get("id").asText();
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createListGetUpdateDeleteBook_flow() throws Exception {
        String id = createBook("The Hobbit", "J.R.R. Tolkien", 1937, "978-0261103283");

        // GET single
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("J.R.R. Tolkien"))
                .andExpect(jsonPath("$.year").value(1937))
                .andExpect(jsonPath("$.isbn").value("978-0261103283"));

        // LIST all
        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("The Hobbit"));

        // LIST filter by author
        mockMvc.perform(get("/books").param("author", "tolkien"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].author").value("J.R.R. Tolkien"));

        // UPDATE
        Map<String, Object> update = new LinkedHashMap<>();
        update.put("title", "The Hobbit: Revised");
        update.put("author", "J.R.R. Tolkien");
        update.put("year", 1937);
        update.put("isbn", "978-0261103283");
        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Hobbit: Revised"));

        // DELETE
        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        // GET after delete -> 404
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void validationFails_whenTitleAndAuthorMissing() throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("year", 2000);
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists())
                .andExpect(jsonPath("$.errors.author").exists());
    }

    @Test
    void getUnknownBookReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateNonexistentBookReturns404() throws Exception {
        Map<String, Object> update = new LinkedHashMap<>();
        update.put("title", "Ghost");
        update.put("author", "Nobody");
        mockMvc.perform(put("/books/999999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteNonexistentBookReturns404() throws Exception {
        mockMvc.perform(delete("/books/999999"))
                .andExpect(status().isNotFound());
    }
}
