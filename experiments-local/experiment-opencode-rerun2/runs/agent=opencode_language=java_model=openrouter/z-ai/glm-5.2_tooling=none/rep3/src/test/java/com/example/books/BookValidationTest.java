package com.example.books;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class BookValidationTest extends BaseIntegrationTest {

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        String payload = "{\"year\": 2020, \"isbn\": \"123\"}";
        mockMvc.perform(post("/books")
                        .contentType("application/json")
                        .content(payload))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists())
                .andExpect(jsonPath("$.errors.author").exists());
    }
}
