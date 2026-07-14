package com.example.books;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class BookApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createListGetUpdateDeleteBook() throws Exception {
        // Create
        String body = """
                {"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
                """;
        String location = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andReturn().getResponse().getContentAsString();

        Long id = JsonTestSupport.extractId(location);

        // List
        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("Dune"));

        // List with author filter
        mockMvc.perform(get("/books").param("author", "Frank Herbert"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].author").value("Frank Herbert"));

        mockMvc.perform(get("/books").param("author", "Nobody"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$[0]").doesNotExist());

        // Get by id
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isbn").value("9780441172719"));

        // Update
        String updateBody = """
                {"title":"Dune Updated","author":"Frank Herbert","year":1966,"isbn":"ISBN-X"}
                """;
        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(updateBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune Updated"))
                .andExpect(jsonPath("$.year").value(1966));

        // Delete
        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        // Get after delete -> 404
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void validationRejectsMissingTitleAndAuthor() throws Exception {
        String bad = """
                {"year":1999}
                """;
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bad))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getUnknownBookReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").exists());
    }
}
