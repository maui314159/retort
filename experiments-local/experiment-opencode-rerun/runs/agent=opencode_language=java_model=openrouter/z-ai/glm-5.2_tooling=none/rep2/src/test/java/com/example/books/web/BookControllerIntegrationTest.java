package com.example.books.web;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.AfterEach;
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
class BookControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private BookRepository bookRepository;

    @AfterEach
    void cleanup() {
        bookRepository.deleteAll();
    }

    @Test
    void healthCheckReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createBookReturnsCreatedAndCanBeFetched() throws Exception {
        String body = """
                {"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}
                """;
        String location = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("J.R.R. Tolkien"))
                .andReturn().getResponse().getContentAsString();

        // extract id from response
        String id = com.jayway.jsonpath.JsonPath.read(location, "$.id").toString();

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isbn").value("978-0261102217"));
    }

    @Test
    void createBookWithMissingTitleReturns400() throws Exception {
        String body = """
                {"author":"Some Author","year":2000}
                """;
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("title"));
    }

    @Test
    void listBooksSupportsAuthorFilter() throws Exception {
        bookRepository.save(new Book(null, "Book A", "Alice", 2001, "111"));
        bookRepository.save(new Book(null, "Book B", "Bob", 2002, "222"));

        mockMvc.perform(get("/books").param("author", "Alice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].author").value("Alice"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }

    @Test
    void updateAndDeleteBook() throws Exception {
        String body = """
                {"title":"Old","author":"Old Author","year":1990,"isbn":"old"}
                """;
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        String id = com.jayway.jsonpath.JsonPath.read(created, "$.id").toString();

        String update = """
                {"title":"New","author":"New Author","year":2020,"isbn":"new"}
                """;
        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(update))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New"))
                .andExpect(jsonPath("$.year").value(2020));

        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound());
    }
}
