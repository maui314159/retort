package com.example.books.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class BookControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void healthCheckReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createBookReturnsCreatedAndBookCanBeRetrieved() throws Exception {
        Map<String, Object> book = new LinkedHashMap<>();
        book.put("title", "The Pragmatic Programmer");
        book.put("author", "Andrew Hunt");
        book.put("year", 1999);
        book.put("isbn", "978-0201616224");

        String body = objectMapper.writeValueAsString(book);

        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("The Pragmatic Programmer"))
                .andExpect(jsonPath("$.author").value("Andrew Hunt"))
                .andExpect(jsonPath("$.id").exists())
                .andReturn().getResponse().getContentAsString();

        Long id = objectMapper.readTree(created).get("id").asLong();

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.isbn").value("978-0201616224"));
    }

    @Test
    void createBookWithMissingTitleReturns400() throws Exception {
        Map<String, Object> book = new LinkedHashMap<>();
        book.put("author", "Someone");
        book.put("year", 2020);

        String body = objectMapper.writeValueAsString(book);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists());
    }

    @Test
    void listBooksSupportsAuthorFilter() throws Exception {
        // Seed two books with different authors
        Map<String, Object> a = new LinkedHashMap<>();
        a.put("title", "Filtered A");
        a.put("author", "UniqueAuthor");
        a.put("year", 2010);
        a.put("isbn", "ua1");
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(a))).andExpect(status().isCreated());

        Map<String, Object> b = new LinkedHashMap<>();
        b.put("title", "Filtered B");
        b.put("author", "OtherAuthor");
        b.put("year", 2011);
        b.put("isbn", "ua2");
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(b))).andExpect(status().isCreated());

        mockMvc.perform(get("/books").param("author", "UniqueAuthor"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].author").value("UniqueAuthor"));
    }

    @Test
    void updateBookReturns200WithUpdatedFields() throws Exception {
        Map<String, Object> book = new LinkedHashMap<>();
        book.put("title", "Old Title");
        book.put("author", "Old Author");
        book.put("year", 2000);
        book.put("isbn", "old-isbn");

        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        Long id = objectMapper.readTree(created).get("id").asLong();

        Map<String, Object> update = new LinkedHashMap<>();
        update.put("title", "New Title");
        update.put("author", "New Author");
        update.put("year", 2022);
        update.put("isbn", "new-isbn");

        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2022));
    }

    @Test
    void deleteBookReturnsNoContentAndThen404() throws Exception {
        Map<String, Object> book = new LinkedHashMap<>();
        book.put("title", "Delete Me");
        book.put("author", "Author");
        book.put("year", 2020);
        book.put("isbn", "d1");

        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        Long id = objectMapper.readTree(created).get("id").asLong();

        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void getBookForUnknownIdReturns404WithEmptyBody() throws Exception {
        mockMvc.perform(get("/books/9999999"))
                .andExpect(status().isNotFound())
                .andExpect(content().string(""));
    }
}
